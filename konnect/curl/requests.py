# Copyright 2023-2024  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Provides `Request`, a simple implementation of `konnect.curl.abc.RequestProtocol`
"""

from typing import IO

import pycurl


class Request:
	"""
	A simple implementation of `konnect.curl.abc.RequestProtocol`
	"""

	url: str
	destination: IO[bytes]

	def __init__(self, url: str, destination: IO[bytes]):
		self.url = url
		self.destination = destination

	def configure_handle(self, handle: pycurl.Curl, /) -> None:
		"""
		Set options on a `pycurl.Curl` instance to be used for this request
		"""
		handle.setopt(pycurl.URL, self.url)
		handle.setopt(pycurl.WRITEDATA, self.destination)
		handle.setopt(pycurl.CONNECTTIMEOUT_MS, 500)
		handle.setopt(pycurl.TIMEOUT_MS, 3000)

	def has_response(self) -> bool:
		"""
		Return whether calling `response()` will return a value or raise LookupError
		"""
		return False

	def response(self) -> None:
		"""
		Return a waiting response or raise LookupError if there is none

		See `has_response()` for checking for waiting responses.
		"""
		raise LookupError

	def completed(self) -> None:
		"""
		Indicate that Curl has completed processing the handle and return a final response
		"""
