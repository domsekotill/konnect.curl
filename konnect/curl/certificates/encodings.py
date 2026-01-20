# Copyright 2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Classes for various DER encoded objects, with ASCII armoring and file storage for them
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Final
from typing import Protocol
from typing import Self
from typing import overload

from .ascii_armor import ArmoredData

if TYPE_CHECKING:
	from typing import TypeVar

	PrivateKeyT = TypeVar("PrivateKeyT", bound=PrivateKey)

__all__ = [
	"AsciiArmored",
	"Certificate",
	"ECPrivateKey",
	"Pkcs8EncryptedPrivateKey",
	"Pkcs8PrivateKey",
	"Pkcs12",
	"PrivateKey",
	"RSAPrivateKey",
]

DEFAULT_MAX_READ: Final = 2**16  # 64kiB


class Encoding(Protocol):
	format: ClassVar[str]

	@classmethod
	def from_bytes(cls, source: bytes, /) -> Self: ...
	def to_bytes(self) -> bytes: ...

	def certificate(self) -> Certificate | None: ...
	def private_key(self) -> PrivateKey | None: ...


class Certificate(bytes):
	"""
	X.509 certificates
	"""

	format: ClassVar = "DER"
	label: ClassVar = "CERTIFICATE"

	@classmethod
	def from_bytes(cls, source: bytes, /) -> Self:
		"""
		Return a new instance from an in-memory bytes string
		"""
		return cls(source)

	def to_bytes(self) -> Self:
		"""
		Return a bytes string representation of an instance (itself, as it subclasses bytes)
		"""
		return self

	def fingerprint(self) -> str:
		"""
		Return the SHA1 hash of the certificate as a hexadecimal string
		"""
		# TODO(dom): Would like to return hashlib.HASH but not currently allowed by typeshed
		# https://code.kodo.org.uk/konnect/konnect.curl/-/issues/9
		return hashlib.sha1(self).hexdigest()

	def certificate(self) -> Self:
		"""
		Return the certificate, itself
		"""
		return self

	def private_key(self) -> None:
		"""
		Return None, this is a no-op for certificates
		"""
		return


class PrivateKey(bytes):
	"""
	Base class for private key containers
	"""

	format: ClassVar[str]
	label: ClassVar[str]

	def __new__(cls, source: bytes, /) -> Self:  # noqa: D102
		if cls is PrivateKey:
			msg = "cannot instantiate PrivateKey base class"
			raise TypeError(msg)
		return bytes.__new__(cls, source)

	def __init_subclass__(cls, label: str) -> None:
		cls.format = "DER"
		cls.label = label

	@classmethod
	def from_bytes(cls, source: bytes, /) -> Self:
		"""
		Return a new instance from an in-memory bytes string
		"""
		return cls(source)

	def to_bytes(self) -> Self:
		"""
		Return a bytes string representation of an instance (itself, as it subclasses bytes)
		"""
		return self

	def certificate(self) -> None:
		"""
		Return None, this is a no-op for private keys
		"""
		return

	def private_key(self) -> Self:
		"""
		Return the private key, itself
		"""
		return self


class RSAPrivateKey(PrivateKey, label="RSA PRIVATE KEY"):
	"""
	PKCS#1 private key
	"""


class Pkcs8PrivateKey(PrivateKey, label="PRIVATE KEY"):
	"""
	PKCS#8 unencrypted private key
	"""


class Pkcs8EncryptedPrivateKey(PrivateKey, label="ENCRYPTED PRIVATE KEY"):
	"""
	PKCS#8 encrypted private key
	"""


class ECPrivateKey(PrivateKey, label="EC PRIVATE KEY"):
	"""
	ECDSA private key
	"""


class AsciiArmored(bytes):
	"""
	Base 64 encoding with fences for binary cryptographic data, commonly known as PEM

	This class assumes that the encoded data contains at most one certificate and one
	private key, the first occurrence of each being returned by the `certificate()` and
	`private_key()` methods respectively.
	"""

	format: ClassVar = "PEM"

	@classmethod
	def new(
		cls, certificate: Certificate | None = None, private_key: PrivateKey | None = None
	) -> Self:
		"""
		Return an instance with the encoded form of the given certificate and/or private key
		"""
		parts = list[bytes]()

		if certificate:
			parts.extend(ArmoredData("CERTIFICATE", certificate).encode_lines())

		if private_key:
			parts.extend(ArmoredData(private_key.label, private_key).encode_lines())

		return cls(b"".join(parts))

	@classmethod
	def from_bytes(cls, source: bytes, /) -> Self:
		"""
		Return a new instance from an in-memory bytes string
		"""
		return cls(source)

	def to_bytes(self) -> Self:
		"""
		Return a bytes string representation of an instance (itself, as it subclasses bytes)
		"""
		return self

	def certificate(self) -> Certificate | None:
		"""
		Return the first certificate found in the encoded data, or None
		"""
		try:
			return self.find_first(Certificate)
		except NameError:
			return None

	def private_key(self) -> PrivateKey | None:
		"""
		Return the first private key found in the encoded data
		"""
		try:
			return self.find_first(PrivateKey)
		except NameError:
			return None

	@overload
	def find_first(self, kind: type[Certificate], /) -> Certificate: ...

	@overload
	def find_first(self, kind: type[PrivateKeyT], /) -> PrivateKeyT: ...

	def find_first(
		self, kind: type[Certificate] | type[PrivateKey]
	) -> Certificate | PrivateKey:
		"""
		Return the first item with a label matching one of the provided types
		"""
		labels = {t.label: t for t in _recurse_subclasses(kind) if t is not PrivateKey}
		for data in ArmoredData.extract(self):
			try:
				cls = labels[data.label]
			except KeyError:
				continue
			assert issubclass(cls, kind)
			return cls(data)
		msg = f"no matching labels found: {str.join(', ', labels)}"
		raise NameError(msg)


class Pkcs12(bytes):
	"""
	An ASN.1 container format for cryptographic data
	"""

	format: ClassVar = "P12"

	@classmethod
	def new(
		cls, certificate: Certificate | None = None, private_key: PrivateKey | None = None
	) -> Self:
		"""
		Return an instance with the encoded form of the given certificate and/or private key
		"""
		raise NotImplementedError

	@classmethod
	def from_bytes(cls, source: bytes, /) -> Self:
		"""
		Return a new instance from an in-memory bytes string
		"""
		return cls(source)

	def to_bytes(self) -> Self:
		"""
		Return a bytes string representation of an instance (itself, as it subclasses bytes)
		"""
		return self

	def certificate(self) -> Certificate | None:
		"""
		Return the first certificate found in the encoded data
		"""
		raise NotImplementedError

	def private_key(self) -> PrivateKey | None:
		"""
		Return the first private key found in the encoded data
		"""
		raise NotImplementedError


def _recurse_subclasses(
	cls: type[Certificate | PrivateKey],
) -> Iterator[type[Certificate | PrivateKey]]:
	yield cls
	for subcls in cls.__subclasses__():
		yield from _recurse_subclasses(subcls)
