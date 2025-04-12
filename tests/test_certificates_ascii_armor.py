# Copyright 2025  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Tests for the konnect.curl.certificates.ascii_armor module
"""

import unittest
from hashlib import sha256
from importlib import resources
from io import BytesIO
from textwrap import dedent
from typing import assert_never

from konnect.curl.certificates.ascii_armor import ArmoredData


class Tests(unittest.TestCase):
	"""
	Tests for the AsciiArmored class
	"""

	def test_encode_lines(self) -> None:
		"""
		Check encoding ArmoredData produces the expected output
		"""
		raw = """
		And the Lord spake, saying, "First shalt thou take out the Holy Pin. Then shalt thou
		count to three, no more, no less. Three shall be the number thou shalt count, and
		the number of the counting shall be three. Four shalt thou not count, neither count
		thou two, excepting that thou then proceed to three. Five is right out. Once the
		number three, being the third number, be reached, then lobbest thou thy Holy Hand
		Grenade of Antioch towards thy foe, who, being naughty in My sight, shall snuff it.
		"""
		data = ArmoredData(
			"TEST", dedent(raw).lstrip().encode("ascii"), [("Ref", "Arm 2:9-21"), ("Lang", "Latin")]
		)
		digest = "9700a89facf5ae58b6d2d599dd1fce2dcc167d493c17ce8d4b8ad7c218266ee3"

		assert sha256(b"".join(data.encode_lines())).hexdigest() == digest

	def test_extract(self) -> None:
		"""
		Check that data is extracted accurately from a sample
		"""
		sample = resources.files("tests") / "sample.pem"
		data = [*ArmoredData.extract(sample.read_bytes())]

		assert data[0].label == "SAMPLE"
		assert data[0].headers == [("Encoding", "base64"), ("Content-Type", "text/plain")]
		assert b"Strange women lying in ponds" in data[0]
		assert b"farcical aquatic ceremony" in data[0]

		assert data[1].label == "PRIVATE KEY"
		assert data[1].headers == []

		assert data[2].label == "CERTIFICATE"
		assert data[2].headers == []

	def test_non_normative_extract(self) -> None:
		"""
		Check that the parser accepts a checksum and is a forgiving of common misformats
		"""
		sample = resources.files("tests") / "non-normative-sample.pem"
		data = [*ArmoredData.extract(sample.read_bytes())]

		assert data[0].label == "SAMPLE"
		assert data[0].headers == [("Encoding", "base64"), ("Content-Type", "text/plain")]
		assert b"Strange women lying in ponds" in data[0]
		assert b"farcical aquatic ceremony" in data[0]

	def test_extract_with_unarmored(self) -> None:
		"""
		Check that unarmored text is extracted verbatim as Unicode strings when asked
		"""
		sample = resources.files("tests") / "sample.pem"
		buff = BytesIO()

		for data in ArmoredData.extract((raw := sample.read_bytes()), with_unarmored=True):
			match data:
				case ArmoredData():
					buff.writelines(data.encode_lines())
				case str():
					buff.write(data.encode("utf-8"))
				case _ as never:
					assert_never(never)

		buff.seek(0)
		assert buff.read() == raw

	def test_extract_incomplete(self) -> None:
		"""
		Check that incomplete or unexpected input raises ValueError
		"""
		lines = [
			b"-----BEGIN SAMPLE-----\n",
			b"Header: Value\n",
			b"\n",
			b"aaa=\n",
			b"---",
			b"--END TEST-----\n",
		]
		sample = bytearray()

		for line in lines:
			sample.extend(line)

			with self.assertRaises(ValueError):
				_ = [*ArmoredData.extract(sample)]
