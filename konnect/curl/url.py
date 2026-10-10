# Copyright 2024, 2026 Dominik Sekotill <dom.sekotill@kodo.org.uk>

"""
Easy URL manipulation

The `Url` class subclasses `str` but adds a new operator for joining URL parts inspired by
`pathlib.Path`, and some URL manipulation methods:


With the division operator '/' simple concatenation is performed, joining the two parts with
a slash between them:

>>> Url("http://example.com/api/menu") / "spam"
'http://example.com/api/menu/spam'

>>> Url("http://example.com/api/menu/") / "spam"
'http://example.com/api/menu/spam'


Alternatively the `Url.urljoin()` method does a browser-style URL join, where the last
slash-separated component is replaced with the joined string; unless the string starts with
a slash in which case it replaces the entire path component; or with a schema in which case
it replaces the entire URL:

>>> Url("http://example.com/api/menu").urljoin("spam")
'http://example.com/api/spam'

>>> Url("http://example.com/api/menu/").urljoin("spam")
'http://example.com/api/menu/spam'

>>> Url("http://example.com/api/menu/").urljoin("/spam")
'http://example.com/spam'

>>> Url("http://example.com/api/menu/").urljoin("https://example.org/spam")
'https://example.org/spam'


The URL can be implicitly parsed with `urllib.parse.urlparse` and the fields of the result
accessed through attributes of the `Url` class:

>>> Url("http://example.com/api/menu").scheme
'http'

>>> Url("http://example.com/api/menu").hostname
'example.com'


The parsed fields can be replaced to create a new URL with `Url.urlreplace()`:

>>> url = Url("http://example.com/api/menu?choice=spam&number=2")
>>> url.urlreplace(hostname="example.org", query={"choice": "ham", "number": 1})
'http://example.org/api/menu?choice=ham&number=1'


Query parameters can be added or removed with `Url.queryadd()` and `Url.queryremove()`:

>>> Url("http://example.com?food=spam").queryadd(place="Camelot")
'http://example.com?food=spam&place=Camelot'

>>> Url("http://example.com?food=spam").queryadd({"food": ["ham", "eggs"]})
'http://example.com?food=spam&food=ham&food=eggs'

>>> Url("http://example.com?food=spam").queryadd("food=eggs&place=Camelot")
'http://example.com?food=spam&food=eggs&place=Camelot'

>>> Url("http://example.com?food=spam&place=Camelot").queryremove("place")
'http://example.com?food=spam'
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Self
from typing import assert_never
from urllib import parse

type ParamValue = str | int | Sequence[str | int]
type QuerySrc = Sequence[tuple[str, ParamValue]] | Mapping[str, ParamValue] | str


class Url(str):
	"""
	URL strings that can be examined and manipulated
	"""

	__slots__ = "_components"

	scheme: str
	hostname: str
	port: int | None
	path: str
	query: list[tuple[str, str]]
	fragment: str

	netloc: str
	username: str | None
	password: str | None

	@classmethod
	def from_parts(
		cls,
		scheme: str,
		hostname: str,
		port: int | str = "",
		path: str = "",
		query: QuerySrc = "",
		fragment: str = "",
	) -> Self:
		"""
		Create a new URL from component parts

		Note:
			There is no 'netloc', 'username' or 'password' arguments. Credentials should not
			be encoded in URLs.
		"""
		if not isinstance(query, str):
			query = parse.urlencode(query, doseq=True)
		netloc = f"{hostname}:{port}" if port else hostname
		components = parse.ParseResult(scheme, netloc, path, "", query, fragment)
		url = cls(parse.urlunparse(components))
		url._components = components
		return url

	def __init__(self, _src: str, /) -> None:
		self._components: parse.ParseResult | None = None

	def __getattr__(self, name: str, /) -> object:
		if not (comp := self._components):
			self._components = comp = parse.urlparse(self)
		if name == "query":
			return parse.parse_qsl(comp.query, keep_blank_values=True)
		try:
			return getattr(comp, name)
		except AttributeError:
			msg = f"{type(self).__name__!r} object has no attribute {name!r}"
			raise AttributeError(msg) from None

	def __truediv__(self, other: object, /) -> Url:
		if not isinstance(other, str):
			msg = "need a string type"
			raise TypeError(msg)
		if other.startswith("/"):
			msg = f"{other!r} starts with '/', did you mean to use join()?"
			raise ValueError(msg)
		return Url(f"{self}{other}") if self.endswith("/") else Url(f"{self}/{other}")

	def urljoin(self, other: str, /) -> Url:
		"""
		Join this URL as a base with a possibly relative URL to form an absolute URL
		"""
		return Url(parse.urljoin(self, other))

	def urlreplace(
		self,
		scheme: str = "",
		hostname: str = "",
		port: int | str = 0,
		path: str = "",
		query: QuerySrc = "",
		fragment: str = "",
	) -> Url:
		"""
		Replace parts of the URL and return the new URL

		Note:
			Username and password values cannot be replaced, and will be stripped from the
			new URL.  These should not be encoded in URLs.
		"""
		return Url.from_parts(
			scheme or self.scheme,
			hostname or self.hostname,
			port or self.port or 0,
			path or self.path,
			query or self.query,
			fragment or self.fragment,
		)

	def queryadd(self, src: QuerySrc = (), **extra: ParamValue) -> Url:
		"""
		Add query parameters to the URL and return the new URL
		"""
		query = list[tuple[str, ParamValue]](self.query)
		match src:
			case str():
				query.extend(parse.parse_qsl(src))
			case Mapping():
				query.extend(src.items())
			case Sequence():
				query.extend(src)
			case _ as never:
				assert_never(never)
		query.extend(extra.items())
		return self.urlreplace(query=query)

	def queryremove(self, *names: str) -> Url:
		"""
		Remove the named parameters (including repeats) from the URL and return the new URL
		"""
		query = [item for item in self.query if item[0] not in names]
		return self.urlreplace(query=query)
