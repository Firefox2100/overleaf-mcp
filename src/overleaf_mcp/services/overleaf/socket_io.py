"""
Minimal Socket.IO 0.9 client for Overleaf's real-time server.

Overleaf's real-time server is a fork of the pre-Engine.IO Socket.IO 0.9
protocol (github:overleaf/socket.io#0.9.19-overleaf-12); no maintained
Python library speaks it (python-socketio only supports v2+). It also
sends masked frames despite being the server side, which violates
RFC 6455 and is rejected by strict WebSocket clients (verified against
the `websockets` package) — so the WebSocket framing itself is
hand-rolled here too, tolerant of that.

Only the subset Overleaf's client actually exercises is implemented:
handshake, websocket upgrade, heartbeat, event emission, ack, and
disconnect. This is deliberately isolated from the rest of the Overleaf
services so the wire-level details can be fixed independently.
"""

import asyncio
import base64
import json
import os
import ssl
import struct
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

import httpx

_TEXT_OPCODE = 0x1
_CONTINUATION_OPCODE = 0x0
_CLOSE_OPCODE = 0x8
_PING_OPCODE = 0x9
_PONG_OPCODE = 0xA


class SocketIOError(Exception):
    """Raised on a Socket.IO handshake, protocol, or connection error."""


@dataclass(frozen=True)
class SocketIOEvent:
    name: str
    args: list[Any]


class _RawWebSocket:
    """
    Bare-bones RFC 6455 client, tolerant of a server that masks its
    frames (which real servers must not do, but Overleaf's does).
    """

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
        self._closed = False

    @classmethod
    async def connect(cls, url: str, headers: dict[str, str]) -> "_RawWebSocket":
        parts = urlsplit(url)
        is_tls = parts.scheme == "wss"
        port = parts.port or (443 if is_tls else 80)
        ssl_context = ssl.create_default_context() if is_tls else None

        reader, writer = await asyncio.open_connection(
            parts.hostname, port, ssl=ssl_context, server_hostname=parts.hostname if is_tls else None,
        )

        key = base64.b64encode(os.urandom(16)).decode()
        path = parts.path + (f"?{parts.query}" if parts.query else "")
        request_lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {parts.hostname}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
        ]
        request_lines += [f"{name}: {value}" for name, value in headers.items()]
        writer.write(("\r\n".join(request_lines) + "\r\n\r\n").encode())
        await writer.drain()

        status_line = await reader.readline()
        if b"101" not in status_line:
            writer.close()
            raise SocketIOError(f"WebSocket upgrade failed: {status_line.decode(errors='replace').strip()}")
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b""):
                break

        return cls(reader, writer)

    async def send_text(self, payload: str) -> None:
        data = payload.encode()
        header = bytearray([0x80 | _TEXT_OPCODE])
        mask_bit = 0x80
        length = len(data)
        if length < 126:
            header.append(mask_bit | length)
        elif length < 65536:
            header.append(mask_bit | 126)
            header += struct.pack("!H", length)
        else:
            header.append(mask_bit | 127)
            header += struct.pack("!Q", length)
        mask_key = os.urandom(4)
        header += mask_key
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
        self._writer.write(bytes(header) + masked)
        await self._writer.drain()

    async def recv(self) -> str | None:
        """
        Return the next text message, or None once the connection closes.
        Reassembles fragmented (continuation-frame) messages.
        """
        buffer = bytearray()
        while True:
            frame = await self._read_frame()
            if frame is None:
                return None
            opcode, fin, payload = frame
            if opcode == _CLOSE_OPCODE:
                await self._send_close()
                return None
            if opcode == _PING_OPCODE:
                await self._send_control(_PONG_OPCODE, payload)
                continue
            if opcode == _PONG_OPCODE:
                continue
            buffer += payload
            if fin:
                return buffer.decode()

    async def _read_frame(self) -> tuple[int, bool, bytes] | None:
        try:
            head = await self._reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionError):
            return None
        b0, b1 = head
        fin = bool(b0 & 0x80)
        opcode = b0 & 0x0F
        masked = bool(b1 & 0x80)
        length = b1 & 0x7F
        if length == 126:
            length = struct.unpack("!H", await self._reader.readexactly(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", await self._reader.readexactly(8))[0]
        mask_key = await self._reader.readexactly(4) if masked else None
        payload = await self._reader.readexactly(length) if length else b""
        if masked and mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, fin, payload

    async def _send_control(self, opcode: int, payload: bytes) -> None:
        mask_key = os.urandom(4)
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        header = bytes([0x80 | opcode, 0x80 | len(payload)])
        self._writer.write(header + mask_key + masked)
        await self._writer.drain()

    async def _send_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self._send_control(_CLOSE_OPCODE, b"")
        except (ConnectionError, OSError):
            pass

    async def close(self) -> None:
        await self._send_close()
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except (ConnectionError, OSError):
            pass


class SocketIOClient:
    """
    One Socket.IO 0.9 connection to Overleaf's real-time server.

    Usage: `async with SocketIOClient(...) as client:` — connects on
    enter, disconnects on exit. `call()` mirrors Overleaf's own
    convention of a plain `<name>Response` event as the reply rather
    than a true Socket.IO ack (verified live: `joinProject`'s reply
    ignores the requested ack id). `emit_with_ack()` is kept for
    completeness on the rare event that does use a real ack.
    """

    def __init__(self, base_url: str, cookie_header: str, query: dict[str, str] | None = None):
        self._base_url = base_url.rstrip("/")
        self._cookie_header = cookie_header
        self._query = query or {}
        self._ws: _RawWebSocket | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._next_ack_id = 1
        self._pending_acks: dict[int, asyncio.Future[list[Any]]] = {}
        self._events: asyncio.Queue[SocketIOEvent] = asyncio.Queue()
        self._heartbeat_interval = 20.0
        self._connection_error: SocketIOError | None = None

    async def connect(self) -> None:
        handshake_url = f"{self._base_url}/socket.io/1/"
        params = {**self._query, "t": str(uuid4().hex)}
        async with httpx.AsyncClient() as http:
            response = await http.get(handshake_url, headers={"Cookie": self._cookie_header}, params=params)
        if response.status_code != 200:
            raise SocketIOError(f"Socket.IO handshake failed with status {response.status_code}: {response.text}")

        try:
            sid, heartbeat_timeout, _close_timeout, transports = response.text.split(":")
        except ValueError as exc:
            raise SocketIOError(f"Unexpected handshake response: {response.text!r}") from exc
        if "websocket" not in transports.split(","):
            raise SocketIOError(f"Server does not offer the websocket transport: {transports!r}")
        self._heartbeat_interval = max(float(heartbeat_timeout) / 3, 1.0)

        ws_scheme = "wss" if self._base_url.startswith("https") else "ws"
        ws_host = self._base_url.split("://", 1)[1]
        query_string = urlencode(self._query)
        ws_url = f"{ws_scheme}://{ws_host}/socket.io/1/websocket/{sid}"
        if query_string:
            ws_url = f"{ws_url}?{query_string}"

        self._ws = await _RawWebSocket.connect(ws_url, headers={"Cookie": self._cookie_header})
        frame = await self._ws.recv()
        if frame != "1::":
            await self._ws.close()
            raise SocketIOError(f"Unexpected connect frame: {frame!r}")

        self._receive_task = asyncio.create_task(self._receive_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def emit(self, name: str, args: list[Any] | None = None) -> None:
        """
        Send an event with no reply expected.
        """
        await self._send(f"5:::{json.dumps({'name': name, 'args': args or []})}")

    async def call(self, name: str, args: list[Any] | None = None, timeout: float = 15.0) -> SocketIOEvent:
        """
        Send an event and wait for the next event Overleaf pushes back,
        Overleaf's own request/response convention (a plain event, not a
        true Socket.IO ack).
        """
        await self.emit(name, args)
        return await self.wait_event(timeout=timeout)

    async def emit_with_ack(self, name: str, args: list[Any] | None = None, timeout: float = 15.0) -> list[Any]:
        """
        Send an event using a real, numbered Socket.IO ack.
        """
        ack_id = self._next_ack_id
        self._next_ack_id += 1
        future: asyncio.Future[list[Any]] = asyncio.get_running_loop().create_future()
        self._pending_acks[ack_id] = future
        try:
            await self._send(f"5:{ack_id}+::{json.dumps({'name': name, 'args': args or []})}")
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_acks.pop(ack_id, None)

    async def wait_event(self, timeout: float = 15.0) -> SocketIOEvent:
        """
        Wait for the next event Overleaf pushes (not requested via call()).
        """
        try:
            return await asyncio.wait_for(self._events.get(), timeout=timeout)
        except asyncio.TimeoutError:
            if self._connection_error is not None:
                raise self._connection_error
            raise

    async def disconnect(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._ws is not None:
            try:
                await self._send("0::")
            except (SocketIOError, ConnectionError, OSError):
                pass
            await self._ws.close()
            self._ws = None
        if self._receive_task is not None:
            self._receive_task.cancel()
            self._receive_task = None
        for future in self._pending_acks.values():
            if not future.done():
                future.cancel()
        self._pending_acks.clear()

    async def __aenter__(self) -> "SocketIOClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.disconnect()

    async def _send(self, frame: str) -> None:
        if self._ws is None:
            raise SocketIOError("Not connected")
        await self._ws.send_text(frame)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            try:
                await self._send("2::")
            except SocketIOError:
                return

    async def _receive_loop(self) -> None:
        assert self._ws is not None
        try:
            while True:
                frame = await self._ws.recv()
                if frame is None:
                    self._connection_error = SocketIOError("Connection closed by server")
                    break
                self._handle_frame(frame)
        finally:
            for future in self._pending_acks.values():
                if not future.done():
                    future.set_exception(self._connection_error or SocketIOError("Connection closed"))

    def _handle_frame(self, raw: str) -> None:
        parts = raw.split(":", 3)
        if len(parts) < 3:
            return
        packet_type, _packet_id, _endpoint = parts[0], parts[1], parts[2]
        data = parts[3] if len(parts) > 3 else ""

        if packet_type == "2":
            return  # heartbeat, no payload to act on
        if packet_type == "0":
            return  # disconnect notice; the read loop's None return handles teardown
        if packet_type == "6":
            ack_id_str, _, payload = data.partition("+")
            try:
                ack_id = int(ack_id_str)
            except ValueError:
                return
            future = self._pending_acks.pop(ack_id, None)
            if future is not None and not future.done():
                future.set_result(json.loads(payload) if payload else [])
            return
        if packet_type == "5":
            payload = json.loads(data) if data else {}
            self._events.put_nowait(SocketIOEvent(name=payload.get("name", ""), args=payload.get("args", [])))
            return
        if packet_type == "7":
            self._connection_error = SocketIOError(f"Server sent an error frame: {raw}")
            return
        # Types 1, 3, 4, 8 aren't used by Overleaf's real-time protocol.
