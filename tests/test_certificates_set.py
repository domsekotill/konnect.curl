# Copyright 2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Tests for the konnect.curl.certificates.configure.set_client_certificate function
"""

from __future__ import annotations

from collections.abc import Iterator
from importlib import import_module
from importlib import resources
from os import fspath
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Final
from typing import NamedTuple

import pycurl
import pytest

from konnect.curl.certificates import AsciiArmored
from konnect.curl.certificates import Certificate
from konnect.curl.certificates import EncodedFile
from konnect.curl.certificates import Pkcs12
from konnect.curl.certificates import RSAPrivateKey
from konnect.curl.certificates import add_client_certificate

if TYPE_CHECKING:
	from konnect.curl.certificates.configure import CertificateSource
	from konnect.curl.certificates.configure import CommonEncodedSource
	from konnect.curl.certificates.configure import PrivateKeySource

STATIC_SHA1: Final = "da39a3ee5e6b4b0d3255bfef95601890afd80709"


class MockConfigHandle:
	def __init__(self) -> None:
		self.setopt_calls = list[tuple[int, object]]()

	def setopt(self, option: int, value: object) -> None:
		self.setopt_calls.append((option, value))

	def unsetopt(self, option: int) -> None:
		raise NotImplementedError

	def pause(self, state: int) -> None:
		raise NotImplementedError


class MockSHA1:
	def __init__(self) -> None: ...
	def update(self, value: bytes) -> None: ...
	def hexdigest(self) -> str:
		return STATIC_SHA1


class SubtestParamsCombined(NamedTuple):
	msg: str
	version: str
	source: CommonEncodedSource
	opts: list[tuple[int, object]]


class SubtestParamsSeparate(NamedTuple):
	msg: str
	version: str
	cert: CertificateSource
	key: PrivateKeySource
	opts: list[tuple[int, object]]


def test_add_client_certificate(
	subtests: pytest.Subtests, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
	monkeypatch.setattr(import_module("hashlib"), "sha1", MockSHA1)
	monkeypatch.setattr(
		import_module("konnect.curl.certificates.configure"), "mkdtemp", lambda: tmp_path
	)

	for params in parameter_generator(tmp_path):
		monkeypatch.setattr(
			pycurl, "version_info", lambda version=params.version: [...] * 5 + [version]
		)
		with subtests.test(f"{params.msg} [{params.version}]"):
			if isinstance(params, SubtestParamsCombined):
				try:
					add_client_certificate(handle := MockConfigHandle(), params.source)
				except NotImplementedError:
					if isinstance(params.source, Pkcs12) or (
						isinstance(params.source, EncodedFile) and isinstance(params.source.contents, Pkcs12)
					):
						pytest.xfail("PKCS12 support not fully implemented yet")
					raise
			else:
				try:
					add_client_certificate(handle := MockConfigHandle(), params.cert, params.key)
				except NotImplementedError:
					if (
						isinstance(params.cert, Pkcs12)
						or isinstance(params.key, Pkcs12)
						or (isinstance(params.cert, EncodedFile) and isinstance(params.cert.contents, Pkcs12))
						or (isinstance(params.key, EncodedFile) and isinstance(params.key.contents, Pkcs12))
					):
						pytest.xfail("PKCS12 support not fully implemented yet")
					raise

			assert handle.setopt_calls == params.opts


def parameter_generator(
	tmp_path: Path,
) -> Iterator[SubtestParamsCombined | SubtestParamsSeparate]:
	sample_blob_pem = AsciiArmored(
		resources.files(__name__).joinpath("sample.pem").read_bytes()
	)
	sample_blob_p12 = Pkcs12(resources.files(__name__).joinpath("sample.p12").read_bytes())
	sample_file_x509 = EncodedFile.write(
		tmp_path / "sample.crt", cert := Certificate(b"xxx"), exists_ok=True
	)
	sample_file_rsa = EncodedFile.write(
		tmp_path / "sample.key", key := RSAPrivateKey(b"xxx"), exists_ok=True
	)
	sample_file_pem = EncodedFile.write(
		tmp_path / "sample.pem",
		AsciiArmored.new(certificate=cert, private_key=key),
		exists_ok=True,
	)
	sample_file_p12 = EncodedFile.write(
		tmp_path / "sample.p12",
		Pkcs12(b"xxx"),
		exists_ok=True,
	)

	yield SubtestParamsCombined(
		"combined cert and key (PEM)",
		"OpenSSL/1.1.0",
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_pem.to_bytes()),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (PKCS12)",
		"OpenSSL/1.1.0",
		sample_blob_p12,
		[
			(pycurl.SSLCERTTYPE, "P12"),
			(pycurl.SSLCERT_BLOB, sample_blob_p12.to_bytes()),
		],
	)
	yield SubtestParamsSeparate(
		"separate cert (PEM) and key (PEM)",
		"OpenSSL/1.1.0",
		sample_blob_pem,
		key := AsciiArmored.new(private_key=RSAPrivateKey(b"xxx")),
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_pem.to_bytes()),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY_BLOB, key.to_bytes()),
		],
	)
	yield SubtestParamsSeparate(
		"separate cert (PEM) and key (RSA)",
		"OpenSSL/1.1.0",
		sample_blob_pem,
		key := RSAPrivateKey(b"xxx"),
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_pem.to_bytes()),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY_BLOB, AsciiArmored.new(private_key=key).to_bytes()),
		],
	)
	yield SubtestParamsSeparate(
		"separate cert (x509) and key (PEM)",
		"OpenSSL/1.1.0",
		cert := Certificate(b"xxx"),
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, AsciiArmored.new(certificate=cert).to_bytes()),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY_BLOB, sample_blob_pem.to_bytes()),
		],
	)
	yield SubtestParamsSeparate(
		"PKCS12 cert and RSA key",
		"OpenSSL/0.9.0",
		sample_blob_p12,
		key := RSAPrivateKey(b"xxx"),
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_p12.to_bytes()),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY_BLOB, AsciiArmored.new(private_key=key).to_bytes()),
		],
	)
	yield SubtestParamsCombined(
		"combined PEM formatted file",
		"OpenSSL/1.1.0",
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(sample_file_pem.path)),
		],
	)
	yield SubtestParamsSeparate(
		"separate cert and key files",
		"OpenSSL/1.1.0",
		sample_file_x509,
		sample_file_rsa,
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT, fspath(sample_file_x509.path)),
			(pycurl.SSLKEYTYPE, "DER"),
			(pycurl.SSLKEY, fspath(sample_file_rsa.path)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (PEM)",
		"GnuTLS/8.10.0",
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (P12)",
		"GnuTLS/8.10.0",
		sample_blob_p12,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (PEM)",
		"GnuTLS/8.11.0",
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (P12)",
		"GnuTLS/8.11.0",
		sample_blob_p12,
		[
			(pycurl.SSLCERTTYPE, "P12"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key (P12)",
		"GnuTLS/8.10.0",
		sample_blob_p12,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsSeparate(
		"separate cert (PEM) and key (RSA)",
		"GnuTLS/8.11.0",
		sample_blob_p12,
		sample_file_rsa,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key file (P12)",
		"GnuTLS/8.10.0",
		sample_file_p12,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key file (PEM)",
		"GnuTLS/8.11.0",
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(sample_file_pem.path)),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key file (P12)",
		"GnuTLS/8.11.0",
		sample_file_p12,
		[
			(pycurl.SSLCERTTYPE, "P12"),
			(pycurl.SSLCERT, fspath(sample_file_p12.path)),
		],
	)

	### MbedTLS tests
	yield SubtestParamsCombined(
		"combined cert and key (PEM)",
		"MbedTLS/0.0.0",
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_pem.to_bytes()),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key file (PEM)",
		"MbedTLS/0.0.0",
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(sample_file_pem.path)),
		],
	)
	# yield SubtestParamsCombined(
	# 	"combined cert and key (PKCS12)",
	# 	"MbedTLS/0.0.0",
	# 	sample_blob_p12,
	# 	[
	# 		(pycurl.SSLCERTTYPE, "PEM"),
	# 		(
	# 			pycurl.SSLCERT_BLOB,
	# 			AsciiArmored.new(
	# 				certificate=sample_blob_p12.certificate(),
	# 				private_key=sample_blob_p12.private_key(),
	# 			),
	# 		),
	# 	],
	# )
	# yield SubtestParamsCombined(
	# 	"combined cert and key file (PKCS12)",
	# 	"MbedTLS/0.0.0",
	# 	sample_file_p12,
	# 	[
	# 		(pycurl.SSLCERTTYPE, "PEM"),
	# 		(
	# 			pycurl.SSLCERT_BLOB,
	# 			AsciiArmored.new(
	# 				certificate=sample_file_p12.contents.certificate(),
	# 				private_key=sample_file_p12.contents.private_key(),
	# 			),
	# 		),
	# 	],
	# )
	yield SubtestParamsSeparate(
		"separated cert blob (x509) and key blob (RSA)",
		"MbedTLS/0.0.0",
		cert := Certificate(b"xxx"),
		key := RSAPrivateKey(b"xxx"),
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT_BLOB, cert.to_bytes()),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsSeparate(
		"separated cert file (x509) and key file (RSA)",
		"MbedTLS/0.0.0",
		sample_file_x509,
		sample_file_rsa,
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT, fspath(sample_file_x509.path)),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY, fspath(tmp_path / STATIC_SHA1)),
		],
	)
	yield SubtestParamsSeparate(
		"separated cert file (x509) and key file (PEM)",
		"MbedTLS/0.0.0",
		sample_file_x509,
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT, fspath(sample_file_x509.path)),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY, fspath(sample_file_pem.path)),
		],
	)

	### WolfSSL tests
	yield SubtestParamsCombined(
		"combined cert and key (PEM)",
		"WolfSSL/0.0.0",
		sample_blob_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT_BLOB, sample_blob_pem.to_bytes()),
		],
	)
	yield SubtestParamsCombined(
		"combined cert and key file (PEM)",
		"WolfSSL/0.0.0",
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "PEM"),
			(pycurl.SSLCERT, fspath(sample_file_pem.path)),
		],
	)
	# yield SubtestParamsCombined(
	# 	"combined cert and key (PKCS12)",
	# 	"WolfSSL/0.0.0",
	# 	sample_blob_p12,
	# 	[
	# 		(pycurl.SSLCERTTYPE, "PEM"),
	# 		(
	# 			pycurl.SSLCERT_BLOB,
	# 			AsciiArmored.new(
	# 				certificate=sample_blob_p12.certificate(),
	# 				private_key=sample_blob_p12.private_key(),
	# 			),
	# 		),
	# 	],
	# )
	# yield SubtestParamsCombined(
	# 	"combined cert and key file (PKCS12)",
	# 	"WolfSSL/0.0.0",
	# 	sample_file_p12,
	# 	[
	# 		(pycurl.SSLCERTTYPE, "PEM"),
	# 		(
	# 			pycurl.SSLCERT_BLOB,
	# 			AsciiArmored.new(
	# 				certificate=sample_file_p12.contents.certificate(),
	# 				private_key=sample_file_p12.contents.private_key(),
	# 			),
	# 		),
	# 	],
	# )
	# yield SubtestParamsSeparate(
	# 	"separated cert blob (DER) and key blob (PKCS12)",
	# 	"WolfSSL/0.0.0",
	# 	cert := Certificate(b"xxx"),
	# 	sample_blob_p12,
	# 	[
	# 		(pycurl.SSLCERTTYPE, "DER"),
	# 		(pycurl.SSLCERT_BLOB, cert.to_bytes()),
	# 		(pycurl.SSLKEYTYPE, "DER"),
	# 		(pycurl.SSLKEY_BLOB, sample_blob_p12.private_key().to_bytes()),
	# 	],
	# )
	yield SubtestParamsSeparate(
		"separated cert blob (x509) and key blob (RSA)",
		"WolfSSL/0.0.0",
		cert := Certificate(b"xxx"),
		key := RSAPrivateKey(b"xxx"),
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT_BLOB, cert.to_bytes()),
			(pycurl.SSLKEYTYPE, "DER"),
			(pycurl.SSLKEY_BLOB, key.to_bytes()),
		],
	)
	yield SubtestParamsSeparate(
		"separated cert file (x509) and key file (RSA)",
		"WolfSSL/0.0.0",
		sample_file_x509,
		sample_file_rsa,
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT, fspath(sample_file_x509.path)),
			(pycurl.SSLKEYTYPE, "DER"),
			(pycurl.SSLKEY_BLOB, sample_file_rsa.contents.private_key()),
		],
	)
	yield SubtestParamsSeparate(
		"separated cert file (x509) and key file (PEM)",
		"WolfSSL/0.0.0",
		sample_file_x509,
		sample_file_pem,
		[
			(pycurl.SSLCERTTYPE, "DER"),
			(pycurl.SSLCERT, fspath(sample_file_x509.path)),
			(pycurl.SSLKEYTYPE, "PEM"),
			(pycurl.SSLKEY, fspath(sample_file_pem.path)),
		],
	)
