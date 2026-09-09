import unittest

from overleaf_mcp.services.overleaf.realtime import (
    OverleafRealtimeService,
    _decode_websocket_text,
)


class FakeSocketIOClient:
    async def emit_with_ack(self, name, args):
        self.name = name
        self.args = args
        return [
            None,
            ["A researcherâs question", "Î±-synuclein"],
            17,
            [],
            {},
            "sharejs-text-ot",
        ]


class RealtimeEncodingTests(unittest.IsolatedAsyncioTestCase):
    def test_decodes_overleaf_websocket_text(self):
        self.assertEqual(_decode_websocket_text("researcherâs"), "researcher’s")
        self.assertEqual(_decode_websocket_text("Î±-synuclein"), "α-synuclein")

    async def test_join_doc_decodes_lines_before_ot_positions_are_calculated(self):
        socket = FakeSocketIOClient()
        service = OverleafRealtimeService("https://overleaf.example")

        lines, version = await service._join_doc(socket, "0123456789abcdef01234567")

        self.assertEqual(lines, ["A researcher’s question", "α-synuclein"])
        self.assertEqual(version, 17)
        self.assertEqual(socket.name, "joinDoc")
        self.assertEqual(socket.args, ["0123456789abcdef01234567", -1, {}])


if __name__ == "__main__":
    unittest.main()
