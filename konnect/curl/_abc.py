# Copyright 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

from collections.abc import Buffer
from typing import Protocol
from typing import Self


class Hash(Protocol):
	"""
	Protocol description of `hashlib` hash objects

	See https://docs.python.org/3/library/hashlib.html#hash-objects
	"""

	@property
	def digest_size(self) -> int:
		"""
		The size of the hash in bytes
		"""
		...

	@property
	def block_size(self) -> int:
		"""
		The internal block size of the hash algorithm in bytes
		"""
		...

	@property
	def name(self) -> str:
		"""
		The canonical name of this hash, always lowercase
		"""
		...

	def update(self, obj: Buffer, /) -> None:
		"""
		Update the hash object with the bytes-like object

		Repeated calls are equivalent to a single call with the concatenation of all the
		arguments: m.update(a); m.update(b) is equivalent to m.update(a+b).
		"""
		...

	def digest(self) -> bytes:
		"""
		Return the digest of the data passed to the update() method so far

		This is a bytes object of size digest_size which may contain bytes in the whole
		range from 0 to 255.
		"""
		...

	def hexdigest(self) -> str:
		"""
		Return the digest encoded as a hexadecimal digit string

		Like digest() except the digest is returned as a string object of double length,
		containing only hexadecimal digits. This may be used to exchange the value safely in
		email or other non-binary environments.
		"""
		...

	def copy(self) -> Self:
		"""
		Return a copy (“clone”) of the hash object

		This can be used to efficiently compute the digests of data sharing a common initial substring.
		"""
		...
