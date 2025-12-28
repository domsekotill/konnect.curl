# Copyright 2023-2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Provides `Request`, a simple implementation of `konnect.curl.abc.RequestProtocol`
"""

from typing import IO

import pycurl

from .abc import ConfigHandle
from .abc import GetInfoHandle


class Request:
	"""
	A simple implementation of `konnect.curl.abc.RequestProtocol`
	"""

	url: str
	destination: IO[bytes]

	def __init__(self, url: str, destination: IO[bytes]) -> None:
		self.url = url
		self.destination = destination

	def configure_handle(self, handle: ConfigHandle, /) -> None:
		"""
		Set options on a `pycurl.Curl` instance to be used for this request
		"""
		handle.setopt(pycurl.URL, self.url)
		handle.setopt(pycurl.WRITEDATA, self.destination)
		handle.setopt(pycurl.CONNECTTIMEOUT_MS, 500)
		handle.setopt(pycurl.TIMEOUT_MS, 3000)

	def has_update(self) -> bool:
		"""
		Return whether calling `get_update()` will return a value or raise LookupError
		"""
		return False

	def get_update(self) -> None:
		"""
		Return a waiting update or raise LookupError if there is none

		See `has_update()` for checking for waiting updates.
		"""
		raise LookupError

	def completed(self, handle: GetInfoHandle, /) -> None:
		"""
		Indicate that Curl has completed processing the handle and return a final response
		"""
