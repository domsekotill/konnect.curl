# Copyright 2023-2024  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Abstract protocols which may be implemented by users

`konnect.curl` provides simple implementations of these protocols which may be used directly
or subclassed by users.
"""

from typing import Protocol
from typing import TypeVar

from pycurl import Curl

U_co = TypeVar("U_co", covariant=True)
R_co = TypeVar("R_co", covariant=True)


class RequestProtocol(Protocol[U_co, R_co]):
	"""
	Request classes that are passed to `Multi.process()` must implement this protocol
	"""

	def configure_handle(self, handle: Curl, /) -> None:
		"""
		Configure a Curl handle for the request by calling its `Curl.setopt()` method

		Users may wish to re-implement or wrap this method to override `Curl.setopt()`
		options.  The handle is guaranteed to be in a clean state with all options set to
		their defaults.
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

		See `has_update()` for checking for waiting updates.
		"""
		...

	def completed(self) -> R_co:
		"""
		Indicate that Curl has completed processing the handle and return a final response
		"""
		...
