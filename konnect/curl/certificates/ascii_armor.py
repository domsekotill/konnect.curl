# Copyright 2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
ASCII armor is a 7-bit safe encoding method for various types of data to be embedded in text
"""

import re
from binascii import a2b_base64
from binascii import b2a_base64
from collections.abc import Iterator
from collections.abc import Sequence
from typing import Literal
from typing import Self
from typing import SupportsIndex
from typing import TypeAlias
from typing import overload

BytesType: TypeAlias = Sequence[SupportsIndex]
Header: TypeAlias = tuple[str, str]

CHR_EQL = ord("=")
CHR_DASH = ord("-")


class ArmoredData(bytes):
	"""
	Armored data is a labeled binary data object with optional headers

	Common examples of armored data are X.509 certificates and private keys labeled as
	CERTIFICATE or PRIVATE KEY respectively.
	"""

	def __new__(  # noqa: D102
		cls, label: str, source: BytesType, headers: Sequence[Header] | None = None
	) -> Self:
		return super().__new__(cls, source)

	def __init__(
		self, label: str, source: BytesType, headers: Sequence[Header] | None = None
	) -> None:
		self.label = label
		self.headers: Sequence[Header] = [] if headers is None else list(headers)

	def encode_lines(self) -> Iterator[bytes]:
		"""
		Encode an `ArmoredData` instance and return a line iterator

		The returned iterator yields the encoded field as LF terminated lines and is
		suitable for passing to `typing.IO[bytes].writelines()` or `bytes.join()`.
		"""
		yield f"-----BEGIN {self.label}-----\n".encode("ascii")

		for header, value in self.headers:
			yield f"{header}: {value}\n".encode("ascii")
		if self.headers:
			yield b"\n"

		view = memoryview(self)
		for offset in range(0, len(self), 48):
			yield b2a_base64(view[offset : offset + 48])

		yield f"-----END {self.label}-----\n".encode("ascii")

	@overload
	@classmethod
	def extract(
		cls, data: bytes | bytearray, *, with_unarmored: Literal[True]
	) -> Iterator[Self | str]: ...

	@overload
	@classmethod
	def extract(
		cls, data: bytes | bytearray, *, with_unarmored: Literal[False] = False
	) -> Iterator[Self]: ...

	@classmethod
	def extract(  # noqa: C901
		cls, data: bytes | bytearray, *, with_unarmored: bool = False
	) -> Iterator[Self | str]:
		"""
		Scan input and return an iterator that yields `ArmoredData` and unarmored lines

		An unarmored line is anything outside of any field's start and end lines and is
		yielded as Unicode strings if 'with_unarmored' is `True`.  Note that unarmored lines
		are assumed to be ASCII or UTF-8 encoded.
		"""
		begin_pattern = re.compile(rb"^-----[ ]?BEGIN ([^-]+)-----$")
		end_pattern = re.compile(rb"^-----[ ]?END ([^-]+)-----$")

		headers = list[tuple[str, str]]()

		lines = enumerate(data.splitlines(keepends=True))
		while 1:
			del headers[:]

			for _, line in lines:
				if match := begin_pattern.match(line):
					break
				if with_unarmored:
					yield line.decode("utf-8")
			else:
				return
			label = match.group(1).rstrip()

			for _, line in lines:
				name, is_hdr, val = line.decode("ascii").partition(":")
				if not is_hdr:
					break
				headers.append((name, val.strip()))
			else:
				raise ValueError("missing contents: expecting encoded data")

			buff = bytearray(a2b_base64(line))
			for number, line in lines:
				match line[0]:
					case 0x3D:  # "="
						# skip checksums
						continue
					case 0x2D:  # "-"
						# break on hitting what is most likely the END line
						line_no = number
						break
					case _:
						buff.extend(a2b_base64(line))
			else:
				raise ValueError("missing contents: expecting an END line")

			if not (match := end_pattern.match(line)):
				raise ValueError(f"malformed line encountered ({line_no})")
			if match.group(1).rstrip() != label:
				raise ValueError(f"unmatched END line encountered ({line_no})")

			yield cls(label.decode("ascii"), buff, headers)
