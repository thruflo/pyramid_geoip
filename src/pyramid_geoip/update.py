# -*- coding: utf-8 -*-

"""Call this module as a script (with the ``PASTE_CONFIG`` environment
  variable set to the path to your PasteDeploy configuration file)
  to update the GeoIP data stored in the database.
"""

import os

from pyramid.paster import bootstrap as bootstrap_app
from pyramid.paster import setup_logging as setup_log

from .lookup import GeoIPLookupUtility

def main(bootstrap=None, setup_logging=None, lookup_cls=None):
    """Run to instantiate a configured GeoIPLookupUtility and use it
      to update the stored GeoIP data.
      
      Setup::
      
          >>> from mock import Mock
          >>> PASTE_CONFIG = os.environ.get('PASTE_CONFIG')
          >>> mock_registry = Mock()
          >>> mock_bootstrap = Mock()
          >>> mock_bootstrap.return_value = {'registry': mock_registry}
          >>> mock_setup_logging = Mock()
          >>> mock_lookup_cls = Mock()
          >>> main(bootstrap=mock_bootstrap, setup_logging=mock_setup_logging,
          ...         lookup_cls=mock_lookup_cls)
      
      Sets up logging::
      
          >>> mock_setup_logging.assert_called_with(PASTE_CONFIG)
      
      Bootstraps a pyramid environment::
      
          >>> mock_bootstrap.assert_called_with(PASTE_CONFIG)
      
      Instantiates a configured utility and calls force update::
      
          >>> mock_lookup_cls.assert_called_with(mock_registry.settings,
          ...         should_save=True)
          >>> assert mock_lookup_cls.return_value.force_update.called
      
    """
    
    # Compose.
    if bootstrap is None: #pragma: no cover
        bootstrap = bootstrap_app
    if setup_logging is None: #pragma: no cover
        setup_logging = setup_log
    if lookup_cls is None: #pragma: no cover
        lookup_cls = GeoIPLookupUtility
    
    paste_config = os.environ.get('PASTE_CONFIG')
    setup_logging(paste_config)
    
    pyramid_environment = bootstrap(paste_config)
    settings = pyramid_environment['registry'].settings
    
    lookup = lookup_cls(settings, should_save=True)
    lookup.force_update()


if __name__ == '__main__': #pragma: no cover
    main()

