# Copyright 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from typing import Any
from typing import Final
from typing import Protocol

import anyio.abc
import pycurl

from ._enums import COMPLETED

if TYPE_CHECKING:
	from collections.abc import Awaitable
	from collections.abc import Callable
	from collections.abc import Generator
	from types import CoroutineType

	from .abc import UpdateHandler

	type CoroutineCallable[**P, R] = Callable[P, CoroutineType[Any, Any, R]]

MAX_SIZE_DEFAULT: Final = 64 * 2**10


def check_not_empty[**P](func: CoroutineCallable[P, bytes]) -> CoroutineCallable[P, bytes]:
	if not __debug__:
		return func

	async def wrap(*args: P.args, **kwargs: P.kwargs) -> bytes:
		resp = await func(*args, **kwargs)
		assert len(resp) > 0, f"empty bytes response from {func}"
		return resp

	return wrap


class ProcessCallback(Protocol):
	def __call__[R](
		self, updates: UpdateHandler[R], handle: pycurl.Curl, /
	) -> Awaitable[R | COMPLETED]: ...


class ReadStream(anyio.abc.ByteReceiveStream):
	def __init__(self, callback: ProcessCallback, handle: pycurl.Curl) -> None:
		self._callback = callback
		self._handle = handle
		self._updates = ReadHandler()
		handle.setopt(pycurl.WRITEFUNCTION, self._updates.write)

	async def aclose(self) -> None:
		assert not self._updates.data
		self._updates.data = b""

	@check_not_empty
	async def receive(self, max_bytes: int = MAX_SIZE_DEFAULT) -> bytes:
		# Maintain this invariant: if self._updates.data is b"" on entry to the method, it
		# MUST remain so on return.  This is used to indicate a closed stream.
		if max_bytes < 1:
			msg = f"invalid maximum number of bytes: {max_bytes}"
			raise ValueError(msg)
		updates = self._updates
		if updates.data is None:
			self._handle.pause(pycurl.PAUSE_CONT)  # May call updates.write()
		if updates.data is None and await self._callback(updates, self._handle) is COMPLETED:
			assert updates.data is None
			raise anyio.EndOfStream
		assert updates.data is not None
		match updates.data:
			case b"":
				raise anyio.EndOfStream
			case data if len(data) <= max_bytes:
				updates.data = None
				return data
			case data:
				data, updates.data = data[:max_bytes], data[max_bytes:]
				return data


class ReadHandler:
	def __init__(self) -> None:
		self.data: bytes | None = None

	def has_update(self) -> bool:
		return self.data is not None

	def get_update(self) -> None:
		return None

	def write(self, data: bytes) -> int:
		if self.data is not None:
			return pycurl.WRITEFUNC_PAUSE
		self.data = data
		return len(data)


class WriteStream(anyio.abc.ByteSendStream):
	def __init__(self, callback: ProcessCallback, handle: pycurl.Curl) -> None:
		self._callback = callback
		self._handle = handle
		self._updates = WriteHandler()
		handle.setopt(pycurl.READFUNCTION, self._updates.read)

	async def aclose(self) -> None:
		self._updates.closed = True

	async def send(self, item: bytes | bytearray | memoryview) -> None:
		updates = self._updates
		if updates.closed:
			raise anyio.ClosedResourceError
		if self._handle.getinfo(pycurl.CONN_ID) >= 0:
			self._handle.pause(pycurl.PAUSE_CONT)
		with updates.use_contents(item):
			if await self._callback(updates, self._handle) is COMPLETED:
				updates.closed = True
				raise anyio.ClosedResourceError


class WriteHandler:
	def __init__(self) -> None:
		self._buffer: memoryview | None = None
		self.closed = False

	@contextmanager
	def use_contents(self, contents: bytes | bytearray | memoryview) -> Generator[None]:
		assert self._buffer is None, "use_contents() is not re-entrant"
		self._buffer = memoryview(contents)
		yield
		assert self._buffer is None

	def has_update(self) -> bool:
		return self._buffer is None

	def get_update(self) -> None:
		return None

	def read(self, size: int) -> bytes | int:
		if not self._buffer:
			return b"" if self.closed else pycurl.READFUNC_PAUSE
		if len(self._buffer) <= size:
			data = self._buffer.tobytes()
			self._buffer = None
			return data
		data, self._buffer = self._buffer[:size].tobytes(), self._buffer[size:]
		return data
