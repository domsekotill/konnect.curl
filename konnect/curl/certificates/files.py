# Copyright 2025-2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
File storage helper class for encoded cryptographic formats
"""

from __future__ import annotations

from pathlib import Path
from typing import Final
from typing import Generic
from typing import TypeVar
from typing import final

from .encodings import Encoding

T = TypeVar("T", bound=Encoding, covariant=True)
C = TypeVar("C", bound=Encoding)

DEFAULT_MAX_READ: Final = 2**16  # 64kiB


@final
class EncodedFile(Generic[T]):
	"""
	Combines decoding data with file path information
	"""

	def __init__(self, contents: T, path: Path) -> None:
		self.contents = contents
		self.path = path

	@classmethod
	def read(
		cls: type[EncodedFile[C]],
		path: Path,
		encoding: type[C],
		/,
		maxsize: int = DEFAULT_MAX_READ,
	) -> EncodedFile[C]:
		"""
		Read encoded data from the file path if it exists and return an `EncodedFile`

		The value of 'maxsize' is a safety net to prevent arbitrarily large files being read
		into memory.  The default should be suitable for most certificate and key files but
		can be overridden to allow unusually large files to be read (probably ASCII armored
		files containing many items).

		Can raise the normal range of `OSError` exceptions that may occur when opening and
		reading a file.
		"""
		with path.open("rb") as handle:
			contents = encoding.from_bytes(handle.read(maxsize))
		return cls(contents, path)

	@staticmethod
	def write(path: Path, contents: C, /, *, exists_ok: bool = False) -> EncodedFile[C]:
		"""
		Write encoded data to the file path

		If 'exists_ok' is false the file will be opened in create-only mode, raising
		`FileExistsError` if there is already a file at the path; otherwise the file is
		opened in normal write mode and truncated before writing the encoded data.  Either
		way the data is never appended to the file.

		Can raise the normal range of `OSError` exceptions that may occur when opening and
		writing to a file.
		"""
		# Its a shame this cannot be a @classmethod to inject EncodedFile subclasses but it
		# cannot be done without subscripting the subclass with the contents type when
		# called.
		mode = "wb" if exists_ok else "xb"
		with path.open(mode) as handle:
			handle.write(contents.to_bytes())
		return EncodedFile(contents, path)
