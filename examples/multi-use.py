#!/usr/bin/env python3
# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
An example script for demonstrating concurrent Curl transfers with konnect.curl.Multi
"""

import os
from pathlib import Path
from typing import IO

import anyio
import pycurl

from konnect.curl import CurlError
from konnect.curl import Multi

DEVNULL = Path("/dev/null")


async def get_url(multi: Multi, url: str, destination: IO[bytes]) -> None:
	"""
	Get a resource from a URL

	The request is actioned concurrently with any other requests running in other tasks.
	All requests actioned with the same Multi instance will share connections if the
	protocol allows it.

	This works well with HTTP GET and *MAY* also work with other URL schemes.
	"""
	# Create and configure a Curl instance
	c = pycurl.Curl()
	c.setopt(pycurl.URL, url)
	c.setopt(pycurl.VERBOSE, 1)
	c.setopt(pycurl.WRITEDATA, destination)
	c.setopt(pycurl.CONNECTTIMEOUT_MS, 500)
	c.setopt(pycurl.TIMEOUT_MS, 3000)
	# c.setopt(pycurl.FOLLOWLOCATION, 1)
	# ...

	try:
		await multi.process(c)
	except CurlError as exc:
		print(f"FAILED with {exc}:", c.getinfo(pycurl.EFFECTIVE_URL))
	else:
		print("COMPLETED:", c.getinfo(pycurl.EFFECTIVE_URL))


async def _test() -> None:
	multi = Multi()
	with DEVNULL.open("wb") as destination:
		async with anyio.create_task_group() as tasks:
			tasks.start_soon(get_url, multi, "https://example.com/", destination)
			tasks.start_soon(get_url, multi, "https://code.kodo.org.uk/", destination)

			# Give time for the above transfers to get going, then start another.
			await anyio.sleep(0.1)
			tasks.start_soon(get_url, multi, "https://code.kodo.org.uk/konnect/konnect.curl/", destination)


if __name__ == "__main__":
	anyio.run(_test, backend=os.environ.get("BACKEND", "asyncio"))
