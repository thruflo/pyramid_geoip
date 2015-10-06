# -*- coding: utf-8 -*-

"""Provides a GeoIPLookup utility."""

__all__ = [
    'GeoIPLookupUtility'
]

import logging
logger = logging.getLogger(__name__)

import os
import pygeoip
import transaction

from zope.interface import implementer

from pyramid_basemodel import save as save_to_db
from pyramid_basemodel.blob import Blob

from .interfaces import IGeoIPLookupUtility

IP_TYPES = ['ip4', 'ip6']

stub = u'https://geolite.maxmind.com/download/geoip/database'
DEFAULTS = {
    u'geoip.cities_ip4_name': u'GeoLiteCity',
    u'geoip.cities_ip4_path': u'vendor/GeoLiteCity.dat',
    u'geoip.cities_ip4_url': u'{0}/GeoLiteCity.dat.gz'.format(stub),
    u'geoip.cities_ip6_name': u'GeoLiteCityv6',
    u'geoip.cities_ip6_path': u'vendor/GeoLiteCityv6.dat',
    u'geoip.cities_ip6_url': u'{0}/GeoLiteCityv6-beta/GeoLiteCityv6.dat.gz'.format(stub),
}

@implementer(IGeoIPLookupUtility)
class GeoIPLookupUtility(object):
    """A utility that can be used to fetch GeoIP data and lookup the
      data by ip4 or ip6 IP address.

      Setup::

          >>> from mock import Mock
          >>> mock_blob_cls = Mock()
          >>> mock_query = Mock()
          >>> mock_blob = Mock()
          >>> mock_blob_cls.query.filter_by.return_value = mock_query
          >>> mock_query.first.return_value = mock_blob
          >>> mock_geoip_cls = Mock()
          >>> mock_geoip_cls.return_value = '<client>'
          >>> mock_save = Mock()
          >>> mock_settings = {
          ...     'geoip.cities_ip4_name': u'GeoLiteCity',
          ...     'geoip.cities_ip4_url': u'...',
          ...     'geoip.cities_ip6_name': u'GeoLiteCityv6',
          ...     'geoip.cities_ip6_url': u'...',
          ... }
          >>> kwargs = dict(blob_cls=mock_blob_cls, geoip_cls=mock_geoip_cls,
          ...         save=mock_save)

      Instantiating the utility and then calling ``setup_clients`` automatically
      loads data into geoip clients::

          >>> geoip_lookup = GeoIPLookupUtility(mock_settings, **kwargs)
          >>> geoip_lookup.setup_clients()
          >>> mock_blob_cls.query.filter_by.assert_any_call(name=u'GeoLiteCity')
          >>> mock_blob_cls.query.filter_by.assert_any_call(name=u'GeoLiteCityv6')
          >>> assert geoip_lookup.clients == ['<client>', '<client>']

      If instantiated and ``force_update()`` is called, then will overwrite the
      stored data::

          >>> assert not mock_blob.update_from_url.called
          >>> geoip_lookup = GeoIPLookupUtility(mock_settings, **kwargs)
          >>> geoip_lookup.force_update()
          >>> assert mock_blob.update_from_url.called

      Note that you can't call force_update after setup_clients is called (and
      that calling it calls setup_clients)::

          >>> geoip_lookup.force_update() # doctest: +ELLIPSIS
          Traceback (most recent call last):
          ...
          Exception: Must not call `force_update` after `setup_clients`.

    """

    def lookup(self, ip_address):
        """Lookup geodata for an ip address::

          Setup::

              >>> from mock import Mock
              >>> mock_client1 = Mock()
              >>> def raise_exception(*args):
              ...     raise Exception
              ...
              >>> mock_client1.record_by_addr = raise_exception
              >>> mock_client2 = Mock()
              >>> mock_client2.record_by_addr.return_value = 'data'
              >>> geoip = GeoIPLookupUtility({})
              >>> geoip.clients = [mock_client1, mock_client2]

          Returns the return value of the first call to
          ``client.record_by_addr(ip_address)`` that doesn't error::

              >>> geoip.lookup('64.233.161.99')
              'data'

          Data is in the format::

              {
                  'city': 'Mountain View',
                  'region_name': 'CA',
                  'area_code': 650,
                  'longitude': -122.0574,
                  'country_code3': 'USA',
                  'latitude': 37.419199999999989,
                  'postal_code': '94043',
                  'dma_code': 807,
                  'country_code': 'US',
                  'country_name': 'United States',
                  'continent': 'NA'
              }

        """

        if ip_address and hasattr(ip_address, 'split'):
           ip_address = ip_address.split(',')[0].strip()

        for client in self.clients:
            try:
                return client.record_by_addr(ip_address)
            except Exception:
                continue
        return {}

    def get_blob(self, name, url):
        """Store and return a blob called ``name`` containing the data
          downloaded from ``url``.

          If the blob alreadfy exists, returns it::

              >>> from mock import Mock
              >>> mock_blob_cls = Mock()
              >>> query = mock_blob_cls.query.filter_by.return_value
              >>> existing = query.first.return_value
              >>> geoip_lookup = GeoIPLookupUtility({}, blob_cls=mock_blob_cls)
              >>> blob = geoip_lookup.get_blob('name', 'url')
              >>> assert blob == existing
              >>> assert not blob.update_from_url.called

          If the blob doesn't exist, creates one::

              >>> query.first.return_value = None
              >>> geoip_lookup = GeoIPLookupUtility({}, blob_cls=mock_blob_cls)
              >>> geoip_lookup.should_save = False
              >>> blob = geoip_lookup.get_blob('name', 'url')
              >>> new_ = mock_blob_cls.factory.return_value
              >>> assert blob == new_
              >>> assert blob.update_from_url.called

          If created, or if ``self.should_force_update`` then will update from
          the url::

              >>> geoip_lookup.should_force_update = True
              >>> blob = geoip_lookup.get_blob('name', 'url')
              >>> assert blob.update_from_url.called

        """

        blob = self.blob_cls.query.filter_by(name=name).first()
        is_new = blob is None
        if is_new:
            blob = self.blob_cls.factory(name)

        if is_new or self.should_force_update:
            blob.update_from_url(url, should_unzip=url.endswith('.gz'))
            if self.should_save:
                self.save(blob)

        return blob

    def make_geoip(self, name, path, url):
        """Instantiate and return a ``pygeoip.GeoIP`` instance."""

        # Try the local filesystem.
        if self.exists(path):
            filename = path
            should_delete = False
        else: # Fallback on getting the data from the database as a named file.
            with self.tx_manager:
                blob = self.get_blob(name, url)
                named_file = blob.get_as_named_tempfile(should_close=True)
            filename = named_file.name
            should_delete = True

        # Instantiate the client.
        geoip = self.geoip_cls(filename, self.access_flag)

        # Delete the temp file.
        if should_delete:
            named_file.unlink(filename)

        # Return the client.
        return geoip

    def setup_clients(self, ip_types=IP_TYPES, defaults=DEFAULTS):
        """For each IP type, instantiate and store a geoip client and store the
          database config in case we want to update.
        """

        self.clients = []
        self.databases = []
        for item in ip_types:
            # Unpack / store the config.
            key = 'geoip.cities_{0}_name'.format(item)
            name = unicode(self.settings.get(key, defaults[key]))
            key = 'geoip.cities_{0}_path'.format(item)
            path = unicode(self.settings.get(key, defaults[key]))
            key = 'geoip.cities_{0}_url'.format(item)
            url = unicode(self.settings.get(key, defaults[key]))
            self.databases.append({'name': name, 'path': path, 'url': url})
            # Instantiate the client.
            client = self.make_geoip(name, path, url)
            self.clients.append(client)

    def force_update(self):
        if getattr(self, 'clients'):
            raise Exception('Must not call `force_update` after `setup_clients`.')
        self.should_force_update = True
        self.setup_clients()

    def __init__(self, settings, should_save=True, **kwargs):
        """Instantiate, unpacking the ``settings`` into structured config
          and using the config to instantiate clients.
        """

        # Compose.
        self.clients = []
        self.settings = settings
        self.should_save = should_save
        self.should_force_update = False
        self.access_flag = kwargs.get('access_flag', pygeoip.MEMORY_CACHE)
        self.blob_cls = kwargs.get('blob_cls', Blob)
        self.exists = kwargs.get('exists', os.path.exists)
        self.geoip_cls = kwargs.get('geoip_cls', pygeoip.GeoIP)
        self.save = kwargs.get('save', save_to_db)
        self.tx_manager = kwargs.get('tx_manager', transaction.manager)



def get_geoip_lookup(request, ip_address=None, lookup_iface=None):
    """Lookup and return the geoip_lookup utility.

      Setup::

          >>> from mock import Mock
          >>> mock_geoip = Mock()
          >>> mock_geoip.lookup.return_value = {'some': u'data'}
          >>> mock_request = Mock()
          >>> mock_request.registry.getUtility.return_value = mock_geoip
          >>> mock_iface = 'IGeoIPLookupUtility'

      Returns a function that will get data for an ip address::

          >>> get_geoip_lookup(mock_request, 'ip address', lookup_iface=mock_iface)
          {'some': u'data'}
          >>> mock_request.registry.getUtility.assert_called_with(mock_iface)
          >>> mock_geoip.lookup.assert_called_with('ip address')

      If no ip address is provided, will use the ``REMOTE_ADDR``::

          >>> mock_request.headers = {}
          >>> mock_request.environ = {'REMOTE_ADDR': 'remote ip'}
          >>> get_geoip_lookup(mock_request, lookup_iface=mock_iface)
          {'some': u'data'}
          >>> mock_geoip.lookup.assert_called_with('remote ip')

      Or the ``X-Forwarded-For`` header if available::

          >>> mock_request.headers = {'X-Forwarded-For': 'proxied / load balanced ip'}
          >>> get_geoip_lookup(mock_request, lookup_iface=mock_iface)
          {'some': u'data'}
          >>> mock_geoip.lookup.assert_called_with('proxied / load balanced ip')

    """

    # Compose.
    if lookup_iface is None: #pragma: no cover
        lookup_iface = IGeoIPLookupUtility

    # Get the lookup_utility.
    geoip = request.registry.getUtility(lookup_iface)

    # Get the ip address -- either directly from the remote address in the
    # WSGI environment, or from the X-Forwarded-For header if provided,
    # e.g.: when running behind a load balancer or proxy.
    if ip_address is None:
        remote_address = request.environ.get('REMOTE_ADDR')
        ip_address = request.headers.get('X-Forwarded-For', remote_address)

    # Return its lookup method with the ip_address defaulted to the current request.
    data = geoip.lookup(ip_address)
    if data:
        for key in data:
            value = data.get(key, None)
            if value and isinstance(value, str):
                try:
                    value = value.decode('latin-1')
                except UnicodeDecodeError:
                    value = value.decode('utf-8')
                data[key] = value
    return data

