# Copyright 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from konnect.curl.certificates import AsciiArmored
from konnect.curl.certificates import Certificate
from konnect.curl.certificates import EncodedFile


def test_read() -> None:
	with resources.path(__name__, "sample.pem") as path:
		contents = AsciiArmored(path.read_bytes())

		file = EncodedFile.read(path, AsciiArmored)

	assert isinstance(file.contents, AsciiArmored)
	assert file.contents == contents


def test_write(tmp_path: Path) -> None:
	path = tmp_path / "write-test.crt"
	cert = Certificate(b"xxx")

	file = EncodedFile.write(path, cert)

	assert path.exists()
	assert file.path == path
	assert file.contents == cert


def test_rewrite(tmp_path: Path) -> None:
	path = tmp_path / "write-test.crt"
	cert = Certificate(b"xxx")

	EncodedFile.write(path, cert)
	EncodedFile.write(path, cert, exists_ok=True)

	with pytest.raises(FileExistsError):
		EncodedFile.write(path, cert)

	with pytest.raises(FileExistsError):
		EncodedFile.write(path, cert, exists_ok=False)
