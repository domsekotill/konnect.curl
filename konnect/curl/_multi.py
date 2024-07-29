# Copyright 2023-2024  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterator
from contextlib import asynccontextmanager
from os import dup
from socket import SO_PROTOCOL
from socket import SO_TYPE
from socket import SOL_SOCKET
from socket import socket as Socket
from typing import Literal
from typing import Self
from typing import TypeAlias
from typing import TypeVar

import anyio
import pycurl
from anyio.abc import ObjectReceiveStream
from anyio.abc import ObjectSendStream

from ._enums import MILLISECONDS
from ._enums import SECONDS
from ._enums import SocketEvt
from ._enums import Time
from ._exceptions import CurlError
from .abc import RequestProtocol
from .scalars import Quantity

T = TypeVar("T")
Event: TypeAlias = tuple[Literal[SocketEvt.IN, SocketEvt.OUT], Socket]


class Multi:
	"""
	A wrapper around `pycurl.CurlMulti` to bind it with Anyio-supported event frameworks

	Users should treat this class as a black-box.  Only the `process()` method is available.
	There are no other methods or attributes they should attempt to call or modify as doing
	so will have undefined results.
	"""

	def __init__(self) -> None:
		self._handler = pycurl.CurlMulti()
		self._handler.setopt(pycurl.M_SOCKETFUNCTION, self._add_socket_evt)
		self._handler.setopt(pycurl.M_TIMERFUNCTION, self._add_timer_evt)
		self._io_events = dict[int, tuple[Socket, SocketEvt]]()
		self._deadline: Quantity[Time]|None = None
		self._perform_cond = anyio.Condition()
		self._governor_delegated = False
		self._completed = dict[pycurl.Curl, int]()
		self._requests = dict[RequestProtocol[object], pycurl.Curl]()

	def _add_socket_evt(self, what: int, socket: int, *_: object) -> None:
		# Callback registered with CURLMOPT_SOCKETFUNCTION, registers socket events the
		# transfer manager wants to be activated in response to.
		what: SocketEvt = SocketEvt(what)
		if what == SocketEvt.REMOVE:
			assert socket in self._io_events, f"file descriptor {socket} not in events"
			del self._io_events[socket]
		elif socket in self._io_events:
			socket_, __ = self._io_events[socket]
			self._io_events[socket] = socket_, what
		else:
			self._io_events[socket] = _ExternalSocket.from_fd(socket), what

	def _add_timer_evt(self, delay: int) -> None:
		# Callback registered with CURLMOPT_TIMERFUNCTION, registers when the transfer
		# manager next wants to be activated if no prior events occur, in milliseconds.
		self._deadline = \
			None if delay < 0 else \
			anyio.current_time() @ SECONDS + delay @ MILLISECONDS

	async def _single_event(self) -> int:
		# Await a single event and call pycurl.CurlMulti.socket_action to inform the handler
		# of it, then return the number of active transfers

		# Shortcut if no events are registered, or the only event is an immediate timeout
		if not self._io_events and self._deadline is None:
			_, running = self._handler.socket_action(pycurl.SOCKET_TIMEOUT, 0)
			return running

		# Start concurrent tasks awaiting each of the registered events, await a response
		# from the first task to wake and send one.
		async with anyio.create_task_group() as tasks, _make_evt_channel() as (sendchan, recvchan):
			for socket, evt in self._io_events.values():
				if SocketEvt.IN in evt:
					tasks.start_soon(_wait_readable, socket, sendchan)
				if SocketEvt.OUT in evt:
					tasks.start_soon(_wait_writable, socket, sendchan)
			if self._deadline is not None:
				tasks.start_soon(_wait_until, self._deadline, sendchan)
			resp = await recvchan.receive()
			tasks.cancel_scope.cancel()

		# Call pycurl.CurlMulti.socket_action() with details of the received event, and
		# return how many active handles remain.
		match resp:
			case None:
				_, running = self._handler.socket_action(pycurl.SOCKET_TIMEOUT, 0)
			case SocketEvt.IN, Socket() as socket:
				_, running = self._handler.socket_action(socket.fileno(), pycurl.CSELECT_IN)
			case SocketEvt.OUT, Socket() as socket:
				_, running = self._handler.socket_action(socket.fileno(), pycurl.CSELECT_OUT)  # type: ignore[unreachable]
		return running

	def _get_handle(self, request: RequestProtocol[object]) -> pycurl.Curl:
		try:
			return self._requests[request]
		except KeyError:
			handle = self._requests[request] = pycurl.Curl()
			request.configure_handle(handle)
			self._handler.add_handle(handle)
			return handle

	def _del_handle(self, request: RequestProtocol[object]) -> None:
		handle = self._requests.pop(request)
		self._handler.remove_handle(handle)

	def _yield_complete(self) -> Iterator[tuple[pycurl.Curl, int]]:
		# Convert pycurl.CurlMulti.info_read() output into tuples of (handle, code) and
		# iteratively yield them
		n_msgs = -1
		while n_msgs:
			# There is a bug in PyCurl affecting info_read; to work around it the
			# 'max_objects' argument must be AT LEAST the number of waiting messages, which
			# can be up to the total number of active handles. This makes the loop
			# superfluous but if the bug is fixed 'max_objects' could be replaced with
			# a static value to constrain memory usage and make it more predictable, and
			# remove the need to track the number of active handles.
			n_msgs, complete, failed = self._handler.info_read(len(self._requests))
			yield from ((handle, pycurl.E_OK) for handle in complete)
			yield from ((handle, res) for (handle, res, _) in failed)

	async def _govern_transfer(self, request: RequestProtocol[T], handle: pycurl.Curl) -> None:
		# Await _single_event() repeatedly until the wanted handle is completed.
		# Store all intermediate completed handles and notify interested tasks.
		remaining = -1
		while remaining:
			remaining = await self._single_event()
			self._completed.update(self._yield_complete())
			has_resp = request.has_response()
			if not has_resp and not self._completed:
				continue
			async with self._perform_cond:
				self._perform_cond.notify_all()
				# This check needs to be atomic with the notification
				# (more specifically, the _governor_delegated flag needs to be unset
				# atomically)
				if has_resp or handle in self._completed:
					self._governor_delegated = False
					return

		# SHOULD NOT fall off the end of the loop, but don't want it to run infinitely if
		# something goes wrong, so ensure it has a completion condition and raise
		# RuntimeError if it does complete
		raise RuntimeError("no response detected after all handles processed")

	async def process(self, request: RequestProtocol[T]) -> T:
		"""
		Perform a request as described by a Curl instance
		"""
		if request.has_response():
			return request.response()
		handle = self._get_handle(request)
		while handle not in self._completed:
			# If no task is governing the transfer manager, self-delegate the role to
			# ourselves and govern transfers until `handle` completes.
			if not self._governor_delegated:
				self._governor_delegated = True
				try:
					await self._govern_transfer(request, handle)
				finally:
					self._governor_delegated = False
			# Otherwise await a notification of completed handles
			else:
				async with self._perform_cond:
					await self._perform_cond.wait()
			if request.has_response():
				return request.response()
		match self._completed.pop(handle):  # noqa: R503
			case pycurl.E_OK:
				self._del_handle(request)
				return request.completed()
			case err:
				assert isinstance(err, int)  # nudge mypy
				self._del_handle(request)
				raise CurlError(err, handle.errstr())


class _ExternalSocket(Socket):
	"""
	A non-closing socket.socket subclass

	When instances are garbage-collected they do not close the underlying file descriptor.
	Used for sockets managed in a third-party library (libcurl in this case) which are
	passed as file descriptors.  The file descriptor MUST match, so duplication is not
	a possibility
	"""

	def __del__(self) -> None:
		return

	@classmethod
	def from_fd(cls, fd: int, /) -> Self:
		"""
		Create an instance from the file descriptor of an open socket
		"""
		# Create a temporary socket instance to get socket type and protocol (no low level
		# getsockopt()). FD must be duplicated as it will be closed when destroyed.
		socket = Socket(fileno=dup(fd))
		stype = socket.getsockopt(SOL_SOCKET, SO_TYPE)
		proto = socket.getsockopt(SOL_SOCKET, SO_PROTOCOL)
		return cls(socket.family, stype, proto, fd)


@asynccontextmanager
async def _make_evt_channel() -> AsyncIterator[tuple[ObjectSendStream[Event|None], ObjectReceiveStream[Event|None]]]:
	send, recv = anyio.create_memory_object_stream[Event|None](1)
	async with send, recv:
		yield send, recv


async def _wait_readable(socket: Socket, channel: ObjectSendStream[Event]) -> None:
	await anyio.wait_socket_readable(socket)
	await channel.send((SocketEvt.IN, socket))


async def _wait_writable(socket: Socket, channel: ObjectSendStream[Event]) -> None:
	await anyio.wait_socket_writable(socket)
	await channel.send((SocketEvt.OUT, socket))


async def _wait_until(time: Quantity[Time], channel: ObjectSendStream[None]) -> None:
	await anyio.sleep_until(time >> SECONDS)
	await channel.send(None)
