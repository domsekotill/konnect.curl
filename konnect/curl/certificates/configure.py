# Copyright 2025-2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Curl handle configuration supporting various TLS backends
"""

from __future__ import annotations

import hashlib
import re
from os import fspath
from pathlib import Path
from tempfile import mkdtemp
from typing import TypeAlias
from typing import TypeVar
from typing import assert_never
from typing import overload

import pycurl

from ..abc import ConfigHandle
from .detect import identify_certificate_file
from .encodings import AsciiArmored
from .encodings import Certificate
from .encodings import Encoding
from .encodings import Pkcs12
from .encodings import PrivateKey
from .files import EncodedFile

ContainerT = TypeVar("ContainerT", AsciiArmored, Pkcs12)
EncodedT = TypeVar("EncodedT", bound=Encoding)
RawT = TypeVar("RawT", Certificate, PrivateKey)

CommonEncodedSource: TypeAlias = (
	AsciiArmored | Pkcs12 | EncodedFile[AsciiArmored] | EncodedFile[Pkcs12]
)
EncodedSource: TypeAlias = CommonEncodedSource | RawT | EncodedFile[RawT]

CertificateSource: TypeAlias = EncodedSource[Certificate]
PrivateKeySource: TypeAlias = EncodedSource[PrivateKey]

__all__ = [
	"CertificateSource",
	"PrivateKeySource",
	"add_ca_certificate",
	"add_client_certificate",
]

_tempdir: Path | None = None


def temp_dir() -> Path:
	"""
	Idempotently create and return a temporary directory
	"""
	global _tempdir
	if _tempdir is None:
		_tempdir = Path(mkdtemp())
	return _tempdir


def add_ca_certificate(  # noqa: C901
	handle: ConfigHandle,
	cert_source: CertificateSource | Path,
) -> None:
	"""
	Configure a handle with Certificate Authority certificates
	"""
	if isinstance(cert_source, Path):
		if cert_source.is_dir():
			handle.setopt(pycurl.CAPATH, fspath(cert_source))
			return
		cert_source = identify_certificate_file(cert_source)

	match pycurl.version_info()[5].lower().split("/"):
		case ["gnutls", _]:
			use_blob = False
		case _:
			use_blob = True

	match cert_source:
		case EncodedFile() if isinstance(cert_source.contents, AsciiArmored):
			handle.setopt(pycurl.CAINFO, fspath(cert_source.path))
		case EncodedFile() if use_blob:
			if not (cert := cert_source.contents.certificate()):
				msg = f"no certificate found in {cert_source!r}"
				raise ValueError(msg)
			handle.setopt(pycurl.CAINFO_BLOB, AsciiArmored.new(cert))
		case EncodedFile():
			if not (cert := cert_source.contents.certificate()):
				msg = f"no certificate found in {cert_source!r}"
				raise ValueError(msg)
			cert_source = _container_file(AsciiArmored, cert, None)
			handle.setopt(pycurl.CAINFO, fspath(cert_source.path))
		case AsciiArmored() if use_blob:
			handle.setopt(pycurl.CAINFO_BLOB, cert_source.to_bytes())
		case AsciiArmored():
			cert_source = _as_file(cert_source)
			handle.setopt(pycurl.CAINFO, fspath(cert_source.path))
		case _:
			if not (cert := cert_source.certificate()):
				msg = f"no certificate found in {cert_source!r}"
				raise ValueError(msg)
			cert_source = _container_file(AsciiArmored, cert, None)
			handle.setopt(pycurl.CAINFO, fspath(cert_source.path))


@overload
def add_client_certificate(
	handle: ConfigHandle,
	cert: CertificateSource,
	key: PrivateKeySource,
) -> None: ...


@overload
def add_client_certificate(
	handle: ConfigHandle,
	cert: CommonEncodedSource,
	key: None = None,
) -> None: ...


def add_client_certificate(
	handle: ConfigHandle,
	cert: CertificateSource,
	key: PrivateKeySource | None = None,
) -> None:
	"""
	Configure a handle with a client certificate
	"""
	match pycurl.version_info()[5].lower().split("/"):
		case ["openssl", str(version)]:
			_configure_openssl_handle(handle, version, cert, key)
		case ["gnutls", str(version)]:
			_configure_gnutls_handle(handle, version, cert, key)
		case ["mbedtls", _]:
			_configure_mbedtls_handle(handle, cert, key)
		case ["wolfssl", _]:
			_configure_wolfssl_handle(handle, cert, key)
		case ["schannel" | "secure transport", _]:
			_configure_pkcs12_handle(handle, cert, key)
		case _:
			# TODO(dom): Get samples of other backends' version strings
			# https://code.kodo.org.uk/konnect/konnect.curl/-/issues/10
			raise NameError("unknown TLS backend")


def _configure_openssl_handle(
	handle: ConfigHandle,
	version_str: str,
	cert: CertificateSource,
	key: PrivateKeySource | None,
) -> None:
	# OpenSSL >= 0.9.3 supports PKCS#12; all formats as files or PEM and PKCS#12 as blobs
	# Keys can be given as a separate blob with CURLOPT_SSLKEY_BLOB
	version = _split_version(version_str)
	match cert:
		case Certificate():
			handle.setopt(pycurl.SSLCERTTYPE, AsciiArmored.format)
			handle.setopt(pycurl.SSLCERT_BLOB, AsciiArmored.new(certificate=cert))
		case Pkcs12() if version < [0, 9, 3]:
			cert = _container_blob(AsciiArmored, cert, None)
			handle.setopt(pycurl.SSLCERTTYPE, cert.format)
			handle.setopt(pycurl.SSLCERT_BLOB, cert)
		case AsciiArmored() | Pkcs12():
			handle.setopt(pycurl.SSLCERTTYPE, cert.format)
			handle.setopt(pycurl.SSLCERT_BLOB, cert)
		case EncodedFile():
			handle.setopt(pycurl.SSLCERTTYPE, cert.contents.format)
			handle.setopt(pycurl.SSLCERT, fspath(cert.path))
		case _ as never:
			assert_never(never)

	match key:
		case None:
			return
		case PrivateKey():
			handle.setopt(pycurl.SSLKEYTYPE, AsciiArmored.format)
			handle.setopt(pycurl.SSLKEY_BLOB, AsciiArmored.new(private_key=key))
		case Pkcs12() if version < [0, 9, 3]:
			cert = _container_blob(AsciiArmored, cert, key)
			handle.setopt(pycurl.SSLCERTTYPE, cert.format)
			handle.setopt(pycurl.SSLCERT_BLOB, cert)
		case AsciiArmored() | Pkcs12():
			handle.setopt(pycurl.SSLKEYTYPE, key.format)
			handle.setopt(pycurl.SSLKEY_BLOB, key)
		case EncodedFile():
			handle.setopt(pycurl.SSLKEYTYPE, key.contents.format)
			handle.setopt(pycurl.SSLKEY, fspath(key.path))
		case _ as never:
			assert_never(never)


def _configure_gnutls_handle(
	handle: ConfigHandle,
	version_str: str,
	cert: CertificateSource,
	key: PrivateKeySource | None,
) -> None:
	# From GnuTLS >= 8.11.0 PEM and P12 are allowed, just PEM before that.
	# Only CURLOPT_SSLCERT works with GnuTLS
	version = _split_version(version_str)

	match cert:
		case _ if key is not None:
			cert = _container_file(AsciiArmored, cert, key)
		case AsciiArmored():
			cert = _as_file(cert)
		case Pkcs12():
			cert = _as_file(cert)
		case EncodedFile() if isinstance(cert.contents, Pkcs12) and version < [8, 11, 0]:
			cert = _container_file(AsciiArmored, cert, None)
		case EncodedFile() if isinstance(cert.contents, AsciiArmored | Pkcs12):
			pass
		case _:
			cert = _container_file(AsciiArmored, cert, None)

	assert isinstance(cert, EncodedFile)
	handle.setopt(pycurl.SSLCERTTYPE, cert.contents.format)
	handle.setopt(pycurl.SSLCERT, fspath(cert.path))


def _configure_mbedtls_handle(
	handle: ConfigHandle,
	cert: CertificateSource,
	key: PrivateKeySource | None,
) -> None:
	# MbedTLS supports PEM and DER encodings with both CURLOPT_SSLCERT and
	# CURLOPT_SSLCERT_BLOB, and only PEM (?) with CURLOPT_SSLKEY. CURLOPT_SSLKEY_BLOB does
	# not appear to be supported.
	match cert:
		case Certificate() | AsciiArmored():
			handle.setopt(pycurl.SSLCERTTYPE, cert.format)
			handle.setopt(pycurl.SSLCERT_BLOB, cert)
		case EncodedFile() if not isinstance(cert.contents, Pkcs12):
			handle.setopt(pycurl.SSLCERTTYPE, cert.contents.format)
			handle.setopt(pycurl.SSLCERT, fspath(cert.path))
		case _:
			blob = _container_blob(AsciiArmored, cert, key)
			handle.setopt(pycurl.SSLCERTTYPE, blob.format)
			handle.setopt(pycurl.SSLCERT_BLOB, blob)
			return

	match key:
		case None:
			return
		case EncodedFile() if isinstance(key.contents, AsciiArmored):
			handle.setopt(pycurl.SSLKEYTYPE, "PEM")
			handle.setopt(pycurl.SSLKEY, fspath(key.path))
			return
		case EncodedFile():
			key = key.contents.private_key()
		case _:
			key = key.private_key()

	file = _as_file(AsciiArmored.new(private_key=key))
	handle.setopt(pycurl.SSLKEYTYPE, "PEM")
	handle.setopt(pycurl.SSLKEY, fspath(file.path))


def _configure_wolfssl_handle(
	handle: ConfigHandle,
	cert: CertificateSource,
	key: PrivateKeySource | None,
) -> None:
	# WolfSSL is similar to mbedtls, but supports CURLOPT_SSLKEY_BLOB
	match cert:
		case Certificate() | AsciiArmored():
			handle.setopt(pycurl.SSLCERTTYPE, cert.format)
			handle.setopt(pycurl.SSLCERT_BLOB, cert)
		case EncodedFile() if not isinstance(cert.contents, Pkcs12):
			handle.setopt(pycurl.SSLCERTTYPE, cert.contents.format)
			handle.setopt(pycurl.SSLCERT, fspath(cert.path))
		case _:
			blob = _container_blob(AsciiArmored, cert, key)
			handle.setopt(pycurl.SSLCERTTYPE, blob.format)
			handle.setopt(pycurl.SSLCERT_BLOB, blob)
			return

	match key:
		case None:
			return
		case PrivateKey() | AsciiArmored():
			pass
		case EncodedFile() if isinstance(key.contents, AsciiArmored):
			handle.setopt(pycurl.SSLKEYTYPE, key.contents.format)
			handle.setopt(pycurl.SSLKEY, fspath(key.path))
			return
		case EncodedFile():
			key = key.contents.private_key()
		case _:
			key = key.private_key()

	if key is None:
		msg = f"no private key found in {key}"
		raise ValueError(msg)

	handle.setopt(pycurl.SSLKEYTYPE, key.format)
	handle.setopt(pycurl.SSLKEY_BLOB, key)


def _configure_pkcs12_handle(
	handle: ConfigHandle,
	cert: CertificateSource,
	key: PrivateKeySource | None,
) -> None:
	# Both Schannel and Secure Transport supports only PKCS#12, for both file and blob types
	match cert:
		case EncodedFile() as file if isinstance(file.contents, Pkcs12) and key is None:
			handle.setopt(pycurl.SSLCERTTYPE, file.contents.format)
			handle.setopt(pycurl.SSLCERT, fspath(file.path))
			return
		case Pkcs12() as blob if key is None:
			handle.setopt(pycurl.SSLCERTTYPE, blob.format)
			handle.setopt(pycurl.SSLCERT_BLOB, blob)
			return
		case _:
			blob = _container_blob(Pkcs12, cert, key)
			handle.setopt(pycurl.SSLCERTTYPE, blob.format)
			handle.setopt(pycurl.SSLCERT_BLOB, blob)


def _container_blob(
	cls: type[ContainerT],
	cert_source: CertificateSource,
	key_source: PrivateKeySource | None,
) -> ContainerT:
	match cert_source:
		case AsciiArmored() | Pkcs12():
			cert = cert_source.certificate()
			key = cert_source.private_key()
		case EncodedFile():
			cert = cert_source.contents.certificate()
			key = cert_source.contents.private_key()
		case Certificate() as cert:
			key = None
		case _ as never:
			assert_never(never)

	match key_source:
		case None:
			pass
		case AsciiArmored() | Pkcs12():
			key = key_source.private_key()
		case EncodedFile():
			key = key_source.contents.private_key()
		case PrivateKey() as key:
			pass
		case _ as never:
			assert_never(never)

	if cert is None:
		msg = f"no certificate found in {cert_source!r}"
		raise ValueError(msg)
	if key is None:
		msg = f"no private key found in {key_source or cert_source!r}"
		raise ValueError(msg)

	return cls.new(certificate=cert, private_key=key)


def _container_file(
	cls: type[ContainerT],
	cert_source: CertificateSource,
	key_source: PrivateKeySource | None,
) -> EncodedFile[ContainerT]:
	blob = _container_blob(cls, cert_source, key_source)
	return _as_file(blob)


def _as_file(encoded_data: EncodedT) -> EncodedFile[EncodedT]:
	sha1 = hashlib.sha1()
	if cert := encoded_data.certificate():
		sha1.update(cert)
	if key := encoded_data.private_key():
		sha1.update(key)
	path = temp_dir() / sha1.hexdigest()

	try:
		return EncodedFile.write(path, encoded_data)
	except FileExistsError:
		# Assumes if the file exists this data has already been written to it
		return EncodedFile(encoded_data, path)


def _split_version(version: str) -> list[int]:
	return [int(part) for part in re.findall(r"(?:^|(?<=[._-]))[0-9]+", version)]
