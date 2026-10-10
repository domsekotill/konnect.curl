# Copyright 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Tests for the konnect.curl.url.Url class
"""

from __future__ import annotations

import pytest

from konnect.curl.url import Url


def test_divide_operator(subtests: pytest.Subtests) -> None:
	with subtests.test("append after slash"):
		url = Url("http://example.com/api/menu/") / "spam"
		assert url == "http://example.com/api/menu/spam"

	with subtests.test("append without slash"):
		url = Url("http://example.com/api/menu") / "spam"
		assert url == "http://example.com/api/menu/spam"

	with subtests.test("append empty value"):
		url = Url("http://example.com/api/menu") / "" / "spam"
		assert url == "http://example.com/api/menu/spam"

	with subtests.test("disallow rooted"), pytest.raises(ValueError):
		_ = Url("http://example.com/api/menu") / "/spam"

	with subtests.test("non-string argument"), pytest.raises(TypeError):
		_ = Url("http://example.com/api/menu") / 1


def test_urljoin(subtests: pytest.Subtests) -> None:
	with subtests.test("join without slash"):
		url = Url("http://example.com/api/menu").urljoin("spam")
		assert url == "http://example.com/api/spam"

	with subtests.test("join with slash"):
		url = Url("http://example.com/api/menu/").urljoin("spam")
		assert url == "http://example.com/api/menu/spam"

	with subtests.test("join rooted path"):
		url = Url("http://example.com/api/menu/").urljoin("/spam")
		assert url == "http://example.com/spam"

	with subtests.test("join absolute"):
		url = Url("http://example.com/api/menu/").urljoin("https://example.org/spam")
		assert url == "https://example.org/spam"


def test_urlreplace(subtests: pytest.Subtests) -> None:
	with subtests.test():
		url = Url("http://example.com/api/menu?choice=spam&number=2")
		result = url.urlreplace(hostname="example.org", query={"choice": "ham", "number": 1})
		assert result == "http://example.org/api/menu?choice=ham&number=1"

	with subtests.test():
		url = Url("http://example.com/api/menu?choice=spam&number=2")
		result = url.urlreplace(hostname="example.org", query="choice=ham&number=1")
		assert result == "http://example.org/api/menu?choice=ham&number=1"


def test_queryadd(subtests: pytest.Subtests) -> None:
	with subtests.test("add kwargs"):
		url = Url("http://example.com?food=spam").queryadd(place="Camelot")
		assert url == "http://example.com?food=spam&place=Camelot"

	with subtests.test("add string"):
		url = Url("http://example.com?food=spam").queryadd("food=eggs&place=Camelot")
		assert url == "http://example.com?food=spam&food=eggs&place=Camelot"

	with subtests.test("add mapping"):
		url = Url("http://example.com?food=spam").queryadd({"food": ["ham", "eggs"]})
		assert url == "http://example.com?food=spam&food=ham&food=eggs"

	with subtests.test("add sequence"):
		url = Url("http://example.com?food=spam").queryadd([("food", ["ham", "eggs"])])
		assert url == "http://example.com?food=spam&food=ham&food=eggs"


def test_queryremove(subtests: pytest.Subtests) -> None:
	with subtests.test("remove one"):
		url = Url("http://example.com?food=spam&place=Camelot").queryremove("place")
		assert url == "http://example.com?food=spam"

	with subtests.test("remove many"):
		url = Url("http://example.com?food=spam&number=1&food=ham&place=Camelot").queryremove(
			"food", "number"
		)
		assert url == "http://example.com?place=Camelot"


def test_access(subtests: pytest.Subtests) -> None:
	url = Url("http://example.com")

	with subtests.test("access parsed components"):
		assert url.scheme == "http"
		assert url.hostname == "example.com"
		assert url.path == ""

	with (
		subtests.test("attempt to access non-existing component"),
		pytest.raises(AttributeError),
	):
		_ = url.foo
