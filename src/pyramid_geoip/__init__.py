#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Provides an ``includeme`` function that lets developers configure the
  package to be part of their Pyramid application with::
  
      config.include('pyramid_geoip')
  
"""

from pyramid.settings import asbool

from .interfaces import IGeoIPLookupUtility
from .lookup import GeoIPLookupUtility
from .lookup import get_geoip_lookup

def includeme(config, get_geoip=None, lookup_cls=None, lookup_iface=None):
    """Register an ``IGeoIPLookupUtility`` and provide access to it at
      ``request.geoip``.
      
      Setup::
      
          >>> from mock import Mock
          >>> mock_config = Mock()
          >>> mock_config.registry.settings = {}
          >>> mock_get_geoip = Mock()
          >>> mock_lookup_cls = Mock()
          >>> mock_lookup = mock_lookup_cls.return_value
          >>> mock_lookup_iface = Mock()
          >>> includeme(mock_config, get_geoip=mock_get_geoip,
          ...         lookup_cls=mock_lookup_cls, lookup_iface=mock_lookup_iface)
      
      Registers the utility::
      
          >>> registry = mock_config.registry
          >>> registry.registerUtility.assert_called_with(mock_lookup,
          ...         mock_lookup_iface)
          >>> assert mock_lookup.setup_clients.called
      
      Provides ``request.geoip`` method::
      
          >>> mock_config.add_request_method.assert_called_with(
          ...         mock_get_geoip, 'geoip')
      
    """
    
    # Compose.
    if get_geoip is None: #pragma: no cover
        get_geoip = get_geoip_lookup
    if lookup_cls is None: #pragma: no cover
        lookup_cls = GeoIPLookupUtility
    if lookup_iface is None: #pragma: no cover
        lookup_iface = IGeoIPLookupUtility
    
    # Unpack.
    registry = config.registry
    settings = registry.settings
    
    # Instantiate and setup the clients.
    geoip_lookup = lookup_cls(registry.settings)
    should_setup = asbool(settings.get('geoip.setup_clients', True))
    if should_setup:
        geoip_lookup.setup_clients()
    
    # Register the utililty.
    registry.registerUtility(geoip_lookup, lookup_iface)
    
    # Provide the utility as ``request.geoip``.
    config.add_request_method(get_geoip, 'geoip')

