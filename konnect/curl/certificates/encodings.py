# Copyright 2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Classes for various DER encoded objects, with ASCII armoring and file storage for them
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Final
from typing import Generic
from typing import Never
from typing import Self
from typing import overload

from .ascii_armor import ArmoredData

if TYPE_CHECKING:
	from typing import TypeAlias
	from typing import TypeVar

	AnyEncoding: TypeAlias = "Certificate | PrivateKey | Pkcs12 | AsciiArmored"
	EncodedT = TypeVar("EncodedT", bound=AnyEncoding)
	PrivateKeyT = TypeVar("PrivateKeyT", bound="PrivateKey")

__all__ = [
	"AsciiArmored",
	"Certificate",
	"ECPrivateKey",
	"EncodedFile",
	"Pkcs8EncryptedPrivateKey",
	"Pkcs8PrivateKey",
	"Pkcs12",
	"PrivateKey",
	"RSAPrivateKey",
]

DEFAULT_MAX_READ: Final = 2**16  # 64kiB


class Certificate(bytes):
	"""
	X.509 certificates
	"""

	format: ClassVar = "DER"
	label: ClassVar = "CERTIFICATE"

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
	def find_first(self) -> Never: ...

	@overload
	def find_first(self, *types: type[Certificate]) -> Certificate: ...

	@overload
	def find_first(self, *types: type[PrivateKeyT]) -> PrivateKeyT: ...

	def find_first(self, *types: type[Certificate]|type[PrivateKey]) -> Certificate|PrivateKey:
		"""
		Return the first item with a label matching one of the provided types
		"""
		labels = {t.label: t for t in types}
		for data in ArmoredData.extract(self):
			try:
				cls = labels[data.label]
			except KeyError:
				continue
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


class EncodedFile(Generic["EncodedT"]):
	"""
	Combines a file path with encoding; and reading from and writing to that path
	"""

	def __init__(self, encoding: type[EncodedT], path: Path) -> None:
		self.encoding = encoding
		self.format = encoding.format
		self.path = path

	def read(self, maxsize: int = DEFAULT_MAX_READ) -> EncodedT:
		"""
		Read and return encoded data from the file path if it exists

		The value of 'maxsize' is a safety net to prevent arbitrarily large files being read
		into memory.  The default should be suitable for most certificate and key files but
		can be overridden to allow unusually large files to be read (probably ASCII armored
		files containing many items).

		Can raise the normal range of `OSError` exceptions that may occur when opening and
		reading a file.
		"""
		with self.path.open("rb") as handle:
			return self.encoding(handle.read(maxsize))

	def write(self, encoded_data: EncodedT, /, *, exists_ok: bool = False) -> None:
		"""
		Write encoded data to the file path

		If 'exists_ok' is false the file will be opened in create-only mode, raising
		`FileExistsError` if there is already a file at the path; otherwise the file is
		opened in normal write mode and truncated before writing the encoded data.  Either
		way the data is never appended to the file.

		Can raise the normal range of `OSError` exceptions that may occur when opening and
		writing to a file.
		"""
		mode = "wb" if exists_ok else "xb"
		with self.path.open(mode) as handle:
			handle.write(encoded_data)
