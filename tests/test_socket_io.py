import asyncio
import json
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from overleaf_mcp.services.overleaf.socket_io import SocketIOClient, SocketIOError, _RawWebSocket


class MemoryWriter:
    def __init__(self): self.data = bytearray(); self.closed = False
    def write(self, data): self.data.extend(data)
    async def drain(self): pass
    def close(self): self.closed = True
    async def wait_closed(self): pass


class RawWebSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_sends_short_medium_and_large_masked_text_frames(self):
        for size in (5, 126, 65536):
            writer = MemoryWriter(); ws = _RawWebSocket(asyncio.StreamReader(), writer)
            with patch("overleaf_mcp.services.overleaf.socket_io.os.urandom", return_value=b"mask"):
                await ws.send_text("x" * size)
            self.assertEqual(writer.data[0], 0x81)
            self.assertTrue(writer.data[1] & 0x80)

    async def test_reads_masked_extended_and_fragmented_frames(self):
        reader = asyncio.StreamReader(); writer = MemoryWriter(); ws = _RawWebSocket(reader, writer)
        mask = b"abcd"; payload = b"hello"
        encoded = bytes(x ^ mask[i % 4] for i, x in enumerate(payload))
        reader.feed_data(bytes([0x81, 0x80 | len(payload)]) + mask + encoded); reader.feed_eof()
        self.assertEqual(await ws.recv(), "hello")

        reader = asyncio.StreamReader(); ws = _RawWebSocket(reader, writer)
        reader.feed_data(bytes([0x01, 3]) + b"hel" + bytes([0x80, 2]) + b"lo"); reader.feed_eof()
        self.assertEqual(await ws.recv(), "hello")

    async def test_handles_ping_pong_and_close_details(self):
        reader = asyncio.StreamReader(); writer = MemoryWriter(); ws = _RawWebSocket(reader, writer)
        reader.feed_data(bytes([0x89, 1]) + b"x" + bytes([0x8A, 0]) + bytes([0x88, 5]) + struct.pack("!H", 1000) + b"bye")
        reader.feed_eof()
        self.assertIsNone(await ws.recv())
        self.assertEqual(ws.close_detail, "code=1000, reason='bye'")
        await ws.close()
        self.assertTrue(writer.closed)

    async def test_incomplete_frame_returns_none(self):
        reader = asyncio.StreamReader(); reader.feed_eof()
        self.assertIsNone(await _RawWebSocket(reader, MemoryWriter())._read_frame())


class SocketIOClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_emit_ack_events_and_errors(self):
        client = SocketIOClient("https://example.test/", "sid=x")
        ws = SimpleNamespace(send_text=AsyncMock(), close=AsyncMock(), close_detail=None)
        client._ws = ws
        await client.emit("event", [1])
        self.assertIn('"name": "event"', ws.send_text.call_args.args[0])

        task = asyncio.create_task(client.emit_with_ack("save", [2]))
        await asyncio.sleep(0)
        client._handle_frame('6:::1+["ok"]')
        self.assertEqual(await task, ["ok"])

        client._handle_frame('5:::{"name":"update","args":[3]}')
        event = await client.wait_event()
        self.assertEqual((event.name, event.args), ("update", [3]))
        client._handle_frame("7:::failure")
        self.assertIsInstance(client._connection_error, SocketIOError)
        client._handle_frame("invalid")
        client._handle_frame("6:::bad+[]")

    async def test_send_requires_connection_and_disconnect_cleans_up(self):
        client = SocketIOClient("http://example.test", "sid=x")
        with self.assertRaisesRegex(SocketIOError, "Not connected"):
            await client.emit("event")
        ws = SimpleNamespace(send_text=AsyncMock(side_effect=SocketIOError("closed")), close=AsyncMock())
        client._ws = ws
        future = asyncio.get_running_loop().create_future(); client._pending_acks[1] = future
        await client.disconnect()
        self.assertTrue(future.cancelled())
        self.assertIsNone(client._ws)

    async def test_handle_empty_ack_and_disconnect_frames(self):
        client = SocketIOClient("http://example.test", "sid=x")
        future = asyncio.get_running_loop().create_future(); client._pending_acks[2] = future
        client._handle_frame("6:::2+")
        self.assertEqual(await future, [])
        client._handle_frame("2::")
        client._handle_frame("0::")

    async def test_receive_loop_records_server_close_reason(self):
        client = SocketIOClient("http://example.test", "sid=x")
        client._ws = SimpleNamespace(recv=AsyncMock(return_value=None), close_detail="code=1000")
        await client._receive_loop()
        self.assertIn("code=1000", str(client._connection_error))


if __name__ == "__main__":
    unittest.main()
