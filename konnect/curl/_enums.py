# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Enum classes for other modules
"""

import enum

import pycurl


class SocketEvt(enum.Flag):
	"""
	Provides the `CURL_POLL_*` values from libcurl as a Python enum

	Member names have the 'CURL_POLL_' portion of the name removed.
	"""

	IN = pycurl.POLL_IN
	OUT = pycurl.POLL_OUT
	INOUT = pycurl.POLL_INOUT
	REMOVE = pycurl.POLL_REMOVE
