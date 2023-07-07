# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Enum classes for other modules
"""

import enum

import pycurl

from .scalars import QuantityUnit


class SocketEvt(enum.Flag):
	"""
	Provides the `CURL_POLL_*` values from libcurl as a Python enum

	Member names have the 'CURL_POLL_' portion of the name removed.
	"""

	IN = pycurl.POLL_IN
	OUT = pycurl.POLL_OUT
	INOUT = pycurl.POLL_INOUT
	REMOVE = pycurl.POLL_REMOVE


class Time(QuantityUnit):
	"""
	Units for time intervals
	"""

	# Base times on milliseconds as thats the greatest precision used by curl.
	# This can be transparently changed at any time to a greater precision base.

	MILLISECONDS = 1
	SECONDS = 1000
