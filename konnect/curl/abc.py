# Copyright 2023-2024  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Abstract protocols which may be implemented by users

`konnect.curl` provides simple implementations of these protocols which may be used directly
or subclassed by users.
"""

from typing import Protocol
from typing import TypeVar

U_co = TypeVar("U_co", covariant=True)
R_co = TypeVar("R_co", covariant=True)


# TODO(dom): Make concrete proxies and convert Pycurl exceptions to package exceptions
# https://code.kodo.org.uk/konnect/konnect.curl/-/work_items/6


class ConfigHandle(Protocol):
	"""
	The interface provided by objects passed to `RequestProtocol.configure_handle()`
	"""

	def setopt(self, option: int, value: object, /) -> None:
		"""
		Set an option on a Curl handle

		See https://curl.se/libcurl/c/curl_easy_setopt.html for a list of options and what
		they do.
		"""
		...

	def unsetopt(self, option: int, /) -> None:
		"""
		Set options that have a default value back to that default
		"""
		...

	def pause(self, state: int, /) -> None:
		"""
		Set the paused state of a Curl handle

		This is provided for request implementations that need to await upload data, they
		may store the handle or method for later use. In a future release it will be
		deprecated in favour of a method that returns an asynchronously writable object.
		"""
		...


class GetInfoHandle(Protocol):
	"""
	The interface provided by objects passed to `RequestProtocol.completed()`
	"""

	def getinfo(self, option: int, /) -> object:
		"""
		Return information about a Curl handle

		Note that string values are returned as unicode strings.

		See https://curl.se/libcurl/c/curl_easy_getinfo.html for a list of options and what
		they return.
		"""
		...

	def getinfo_raw(self, option: int, /) -> object:
		"""
		Like `getinfo()` but string values are returned as byte strings
		"""
		...


class RequestProtocol(Protocol[U_co, R_co]):
	"""
	Request classes that are passed to `Multi.process()` must implement this protocol
	"""

	def configure_handle(self, handle: ConfigHandle, /) -> None:
		"""
		Configure a Curl handle for the request by calling `ConfigHandle` methods

		See https://curl.se/libcurl/c/curl_easy_setopt.html for a list of options and what
		they do.
		"""
		...

	def has_update(self) -> bool:
		"""
		Return whether calling `get_update()` will return a value or raise `LookupError`
		"""
		...

	def get_update(self) -> U_co:
		"""
		Return a waiting update or raise `LookupError` if there is none

		`Multi.process()` will only call this method when `has_update()` indicates an update
		is available.  The returned value will be returned by `Multi.process()`.

		Note that values returned by this method are interim updates, and `Multi.process()`
		will be called again with the current request.  It is up to the implementer how many
		times updates will be returned and what objects to return as updates: it may be
		different objects for different stages of a transfer; or there may never be interim
		updates.
		"""
		...

	def completed(self, handle: GetInfoHandle, /) -> R_co:
		"""
		Indicate that Curl has completed processing the handle and return a final response

		Like `get_update` this method's return value will be returned by `Multi.process()`.
		Unlike `get_update` this method will be called exactly once for a successful
		transfer.

		The `GetInfoHandle` passed as a positional argument may be used to get
		post-completion information about a transfer, see
		https://curl.se/libcurl/c/curl_easy_getinfo.html for a list of options and what they
		return.
		"""
		...
