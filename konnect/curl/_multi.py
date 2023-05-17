# Copyright 2023  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

from collections.abc import Iterator
from typing import Final
from typing import Literal
from typing import TypeAlias

import anyio
import pycurl
from anyio.abc import ObjectStream as Channel

from ._enums import SocketEvt
from ._exceptions import CurlError

Event: TypeAlias = tuple[Literal[SocketEvt.IN, SocketEvt.OUT], int]

MILLISECONDS: Final = 1
SECONDS: Final = 1000


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
		self._events = dict[int, SocketEvt]()
		self._delay = -1
		self._perform_cond = anyio.Condition()
		self._governor_delegated = False
		self._completed = dict[pycurl.Curl, int]()

	def _add_socket_evt(self, what: int, socket: int, *_: object) -> None:
		# Callback registered with CURLMOPT_SOCKETFUNCTION, registers socket events the
		# transfer manager wants to be activated in response to.
		what = SocketEvt(what)
		if what == SocketEvt.REMOVE:
			assert socket in self._events, f"file descriptor {socket} not in events"
			del self._events[socket]
		else:
			self._events[socket] = what

	def _add_timer_evt(self, delay: int) -> None:
		# Callback registered with CURLMOPT_TIMERFUNCTION, registers when the transfer
		# manager next wants to be activated if no prior events occur, in milliseconds.
		delay = delay * MILLISECONDS
		if self._delay < 0 or delay < self._delay:
			self._delay = delay

	async def _wait_readable(self, fd: int, channel: Channel[Event]) -> None:
		await anyio.wait_socket_readable(fd)  # type: ignore[arg-type]
		await channel.send((SocketEvt.IN, fd))

	async def _wait_writable(self, fd: int, channel: Channel[Event]) -> None:
		await anyio.wait_socket_writable(fd)  # type: ignore[arg-type]
		await channel.send((SocketEvt.OUT, fd))

	async def _wait_until(self, time: float, channel: Channel[None]) -> None:
		await anyio.sleep_until(time)
		await channel.send(None)

	async def _single_event(self) -> int:
		# Await a single event and call pycurl.CurlMulti.socket_action to inform the handler
		# of it, then return the number of active transfers

		# Shortcut if no events are registered, or the only event is an immediate timeout
		if not self._events and self._delay <= 0:
			_, running = self._handler.socket_action(pycurl.SOCKET_TIMEOUT, 0)
			return running

		# Start concurrent tasks awaiting each of the registered events, await a response
		# from the first task to wake and send one.
		async with anyio.create_task_group() as tasks, _make_evt_channel() as chan:
			for fd, evt in self._events.items():
				if SocketEvt.IN in evt:
					tasks.start_soon(self._wait_readable, fd, chan)
				if SocketEvt.OUT in evt:
					tasks.start_soon(self._wait_writable, fd, chan)
			if self._delay >= 0:
				delay = anyio.current_time() + self._delay / SECONDS
				tasks.start_soon(self._wait_until, delay, chan)
			resp = await chan.receive()
			tasks.cancel_scope.cancel()

		# Call pycurl.CurlMulti.socket_action() with details of the received event, and
		# return how many active handles remain.
		match resp:
			case None:
				_, running = self._handler.socket_action(pycurl.SOCKET_TIMEOUT, 0)
			case SocketEvt.IN, int(fd):
				_, running = self._handler.socket_action(fd, pycurl.CSELECT_IN)
			case SocketEvt.OUT, int(fd):
				_, running = self._handler.socket_action(fd, pycurl.CSELECT_OUT)  # type: ignore[unreachable]
		return running

	def _yield_complete(self) -> Iterator[tuple[pycurl.Curl, int]]:
		# Convert pycurl.CurlMulti.info_read() output into tuples of (handle, code) and
		# iteratively yield them
		n_msgs = -1
		while n_msgs:
			n_msgs, complete, failed = self._handler.info_read(10)
			yield from ((handle, pycurl.E_OK) for handle in complete)
			yield from ((handle, res) for (handle, res, _) in failed)

	async def _govern_transfer(self, handle: pycurl.Curl) -> int:
		# Await _single_event() repeatedly until the wanted handle is completed.
		# Store all intermediate completed handles and notify interested tasks.
		remaining = -1
		while remaining:
			remaining = await self._single_event()
			self._completed.update(self._yield_complete())
			if not self._completed:
				continue
			async with self._perform_cond:
				self._perform_cond.notify_all()
				# This check needs to be atomic with the notification
				# (more specifically, the _governor_delegated flag needs to be unset
				# atomically)
				if (res := self._completed.pop(handle, None)) is not None:
					self._governor_delegated = False
					return res
		# SHOULD NOT fall off the end of the loop, but don't want it to run infinitely if
		# something goes wrong, so ensure it has a completion condition and raise
		# RuntimeError if it does complete
		raise RuntimeError("no response detected after all handles processed")

	async def _await_notification(self, handle: pycurl.Curl) -> int|None:
		# Await notifications of completed transfers from _govern_transfer().
		# Return whether the wanted handle was completed.
		async with self._perform_cond:
			await self._perform_cond.wait()
			return self._completed.pop(handle, None)

	async def process(self, handle: pycurl.Curl) -> None:
		"""
		Perform a request as described by a Curl instance
		"""
		res: int|None = None
		self._handler.add_handle(handle)
		while res is None:
			# If no task is governing the transfer manager, self-delegate the role to
			# ourselves and govern transfers until `handle` completes.
			if not self._governor_delegated:
				self._governor_delegated = True
				try:
					res = await self._govern_transfer(handle)
				finally:
					self._governor_delegated = False
			# Otherwise await a notification of completed handles; break out if `handle` has
			# completed and returned a response, otherwise repeat the loop.
			else:
				res = await self._await_notification(handle)
		self._handler.remove_handle(handle)
		if res != pycurl.E_OK:
			raise CurlError(res, handle.errstr())


def _make_evt_channel() -> Channel[Event|None]:
	return anyio.streams.stapled.StapledObjectStream[Event|None](
		*anyio.create_memory_object_stream(1),
	)
