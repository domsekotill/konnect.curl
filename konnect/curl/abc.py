# Copyright 2023-2024, 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Abstract protocols which may be implemented by users

`konnect.curl` provides simple implementations of these protocols which may be used directly
or subclassed by users.
"""

from __future__ import annotations

from typing import Protocol
from warnings import deprecated


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

	@deprecated(
		"use Multi.get_send_stream() and Multi.get_receive_stream() to control I/O flow"
	)
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


class UpdateHandler[UpdateT = object](Protocol):
	"""
	Implementations of this protocol control when and what is returned from `Multi.process()`

	Update handlers form a part of the `RequestHandler` protocol and are used internally for
	controlling when program flow exits from the «I/O ↔ libcurl ↔ callbacks» flow that forms
	the core of the `Multi.process()` awaitable.
	"""

	def has_update(self) -> bool:
		"""
		Return whether calling `get_update()` will return a value or raise `LookupError`
		"""
		...

	def get_update(self) -> UpdateT:
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


class RequestProtocol[UpdateT = object, ResultT = object](UpdateHandler[UpdateT], Protocol):
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

	def completed(self, handle: GetInfoHandle, /) -> ResultT:
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
