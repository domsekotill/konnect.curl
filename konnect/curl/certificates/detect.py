# Copyright 2025-2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Functions for detecting encodings of files or in-memory byte strings
"""

from pathlib import Path
from typing import Final

from pyasn1.codec.der import decoder
from pyasn1.error import PyAsn1Error
from pyasn1_modules import rfc5208  # type: ignore
from pyasn1_modules import rfc5280  # type: ignore
from pyasn1_modules import rfc5915  # type: ignore
from pyasn1_modules import rfc7292  # type: ignore
from pyasn1_modules import rfc8017  # type: ignore

from .encodings import AsciiArmored
from .encodings import Certificate
from .encodings import ECPrivateKey
from .encodings import Pkcs8EncryptedPrivateKey
from .encodings import Pkcs8PrivateKey
from .encodings import Pkcs12
from .encodings import PrivateKey
from .encodings import RSAPrivateKey
from .files import EncodedFile

__all__ = [
	"identify_blob",
	"identify_certificate_file",
	"identify_file",
]

MAX_READ_SIZE: Final = 2**14  # 16kiB


def identify_file(
	path: Path,
) -> (
	EncodedFile[AsciiArmored]
	| EncodedFile[Certificate]
	| EncodedFile[Pkcs12]
	| EncodedFile[PrivateKey]
):
	"""
	Return the encoding of a file in the form of an `EncodedFile` instance
	"""
	with path.open("br") as file:
		match identify_blob(file.read(MAX_READ_SIZE)):
			case AsciiArmored() as contents:
				return EncodedFile(contents, path)
			case Certificate() as contents:
				return EncodedFile(contents, path)
			case Pkcs12() as contents:
				return EncodedFile(contents, path)
			case PrivateKey() as contents:
				return EncodedFile(contents, path)


def identify_certificate_file(
	path: Path,
) -> EncodedFile[AsciiArmored] | EncodedFile[Certificate] | EncodedFile[Pkcs12]:
	"""
	Return the encoding of a certificate file in the form of an `EncodedFile` instance
	"""
	with path.open("br") as file:
		match identify_blob(file.read(MAX_READ_SIZE)):
			case AsciiArmored() as contents:
				return EncodedFile(contents, path)
			case Certificate() as contents:
				return EncodedFile(contents, path)
			case Pkcs12() as contents:
				return EncodedFile(contents, path)
			case encoding:
				msg = f"file of type {encoding}, expected a certificate encoding: {path}"
				raise TypeError(msg)


def identify_key_file(
	path: Path,
) -> EncodedFile[AsciiArmored] | EncodedFile[Pkcs12] | EncodedFile[PrivateKey]:
	"""
	Return the encoding of a private key file in the form of an `EncodedFile` instance
	"""
	with path.open("br") as file:
		match identify_blob(file.read(MAX_READ_SIZE)):
			case AsciiArmored() as contents:
				return EncodedFile(contents, path)
			case Pkcs12() as contents:
				return EncodedFile(contents, path)
			case PrivateKey() as contents:
				return EncodedFile(contents, path)
			case encoding:
				msg = f"file of type {encoding}, expected a private key encoding: {path}"
				raise TypeError(msg)


def identify_blob(blob: bytes) -> AsciiArmored | Certificate | Pkcs12 | PrivateKey:
	"""
	Identify the encoding of a blob of octets and return the encoding class

	Raises `ValueError` if the encoding is not one of the supported types.

	Note that ASCII armored data is assumed if the first few octets can be interpreted as an
	ASCII or UTF-8 string.
	"""
	specs = [
		(rfc7292.PFX, Pkcs12),  # PKCS#12
		(rfc5280.Certificate, Certificate),  # X.509
		(rfc8017.RSAPrivateKey, RSAPrivateKey),  # PKCS#1
		(rfc5208.PrivateKeyInfo, Pkcs8PrivateKey),  # PKCS#8
		(rfc5208.EncryptedPrivateKeyInfo, Pkcs8EncryptedPrivateKey),  # PKCS#8
		# (rfc5958.AsymmetricKeyPackage, Pkcs8PrivateKey),  # PKCS#8 v2
		(rfc5915.ECPrivateKey, ECPrivateKey),  # ECDSA
	]
	try:
		blob[:20].decode("utf-8")
	except UnicodeError:
		pass
	else:
		return AsciiArmored(blob)
	for spec, encoding in specs:
		try:
			decoder.decode(blob, asn1Spec=spec())
		except PyAsn1Error:
			continue
		return encoding.from_bytes(blob)
	raise ValueError(f"unable to identify encoding")
