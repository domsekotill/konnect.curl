# Copyright 2025-2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Cryptographic certificate management

The support for certificate and key storage formats is very naïve, it does no checks that
keys match certificates.  It exists only to allow users to use as many formats as possible
with as many of libcurl's TLS backends as possible.

The backends currently supported are:
 - OpenSSL
 - GnuTLS
 - MbedSSL
 - WolfSSL
 - Schannel
 - Secure Transport
"""

from .configure import CertificateSource
from .configure import CommonEncodedSource
from .configure import PrivateKeySource
from .configure import add_ca_certificate
from .configure import add_client_certificate
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
	"AsciiArmored",
	"Certificate",
	"CertificateSource",
	"CommonEncodedSource",
	"ECPrivateKey",
	"EncodedFile",
	"Pkcs8EncryptedPrivateKey",
	"Pkcs8PrivateKey",
	"Pkcs12",
	"PrivateKey",
	"PrivateKeySource",
	"RSAPrivateKey",
	"add_ca_certificate",
	"add_client_certificate",
]
