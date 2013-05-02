# -*- coding: utf-8 -*-

"""Provides ``IGeoIPLookupUtility`` marker interface. This is used by the
  Pyramid framework machinery.
"""

from zope.interface import Attribute
from zope.interface import Interface

class IGeoIPLookupUtility(Interface):
    """Marker interface provided by ``GeoIPLookupUtility``s."""

