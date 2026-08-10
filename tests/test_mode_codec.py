"""Unit tests for the Role A MODE codecs (Stream/Block/Compressed).

Covers RFC 959 §3.4 round-trips, wire-format layout, chunk splitting, bounded
streaming, and finite failure on malformed frames.
"""

from __future__ import annotations

import os
import unittest

from common.mode_codec import (
    MODE_BLOCK,
    MODE_COMPRESSED,
    MODE_STREAM,
    ModeCodecError,
    block_decode,
    block_encode,
    compressed_decode,
    compressed_encode,
    decode_chunks,
    encode_chunks,
    normalize_mode,
    normalize_transfer_type,
)

WIRE_CHUNK_SIZE = 1024


def join(iterable) -> bytes:
    return b"".join(iterable)


def round_trip(data: bytes, mode: str, slice_sizes=(7, 1024, 4096)) -> bytes:
    encoded = join(encode_chunks([data], mode))
    for size in slice_sizes:
        pieces = [
            encoded[i:i + size]
            for i in range(0, len(encoded), size)
        ] or [b""]
        if join(decode_chunks(pieces, mode)) != data:
            raise AssertionError(
                f"round-trip failed for mode={mode} slice={size} "
                f"len={len(data)} encoded_len={len(encoded)}"
            )
    return encoded


class TestRoundTrip(unittest.TestCase):
    CASES = [
        ("empty", b""),
        ("nul", b"\x00"),
        ("escape-nul", b"\x00\x40"),
        ("escape-half", b"\x40"),
        ("one-byte-max", b"\xff"),
        ("random-small", bytes(range(256))),
        ("random-mid", bytes((i * 7 + 3) % 256 for i in range(4000))),
        ("random-large", os.urandom(70000)),
        ("text", (b"the quick brown fox jumps over the lazy dog\r\n" * 500)),
        ("repeated-a", b"A" * 10000),
        ("repeated-nul", b"\x00" * 10000),
        ("alternating", (b"\x00\xff" * 5000)),
        ("pattern-127", bytes(range(127)) * 3),
    ]

    def test_stream_round_trip(self):
        for name, data in self.CASES:
            with self.subTest(name=name):
                round_trip(data, MODE_STREAM)

    def test_block_round_trip(self):
        for name, data in self.CASES:
            with self.subTest(name=name):
                round_trip(data, MODE_BLOCK)

    def test_compressed_round_trip(self):
        for name, data in self.CASES:
            with self.subTest(name=name):
                round_trip(data, MODE_COMPRESSED)

    def test_boundary_sizes(self):
        for size in (1, 2, 63, 64, 127, 128, 255, 256, 1023, 1024,
                     1025, 65535, 65536):
            for mode in (MODE_STREAM, MODE_BLOCK, MODE_COMPRESSED):
                with self.subTest(mode=mode, size=size):
                    round_trip(os.urandom(size), mode)

    def test_one_byte_at_a_time_decoding(self):
        for mode in (MODE_BLOCK, MODE_COMPRESSED):
            for name, data in [("nul", b"\x00"), ("mixed", os.urandom(3000))]:
                with self.subTest(mode=mode, name=name):
                    encoded = join(encode_chunks([data], mode))
                    pieces = [encoded[i:i + 1] for i in range(len(encoded))]
                    self.assertEqual(join(decode_chunks(pieces, mode)), data)

    def test_all_bytes_round_trip_compressed(self):
        for byte in range(256):
            with self.subTest(byte=byte):
                data = bytes([byte]) * 200
                self.assertEqual(
                    join(decode_chunks(encode_chunks([data], "C"), "C")), data
                )


class TestWireFormat(unittest.TestCase):
    def test_block_header_layout(self):
        encoded = join(block_encode([b"abc"]))
        self.assertEqual(encoded, b"\x40\x00\x03abc")

    def test_block_mid_and_last_blocks(self):
        payload = b"x" * 2500
        encoded = list(block_encode([payload], block_size=1024))
        self.assertEqual(len(encoded), 3)
        self.assertEqual(encoded[0][0], 0x00)
        self.assertEqual(encoded[0][1:3], (1024).to_bytes(2, "big"))
        self.assertEqual(encoded[2][0], 0x40)
        self.assertEqual(join(decode_chunks(encoded, "B")), payload)

    def test_compressed_primitives(self):
        # literal run: a trailing singleton cannot be merged without lookahead,
        # so each byte may form its own one-byte literal run.
        self.assertEqual(join(compressed_encode([b"hi"])), b"\x01h\x01i\x00\x40")
        # repeated byte: 3 x 'a' -> 0x83 'a'
        self.assertEqual(join(compressed_encode([b"aaa"])), b"\x83a\x00\x40")
        # filler: 3 x NUL -> 0xc3
        self.assertEqual(join(compressed_encode([b"\x00\x00\x00"])), b"\xc3\x00\x40")
        # empty file -> bare EOF escape
        self.assertEqual(join(compressed_encode([b""])), b"\x00\x40")

    def test_compressed_filler_depends_on_transfer_type(self):
        ascii_wire = join(compressed_encode([b"   "], "A"))
        image_wire = join(compressed_encode([b"\x00\x00\x00"], "I"))
        self.assertEqual(ascii_wire, b"\xc3\x00\x40")
        self.assertEqual(image_wire, b"\xc3\x00\x40")
        self.assertEqual(join(compressed_decode([ascii_wire], "A")), b"   ")
        self.assertEqual(join(compressed_decode([image_wire], "I")), b"\x00" * 3)
        self.assertNotEqual(join(compressed_decode([ascii_wire], "I")), b"   ")

    def test_wire_chunks_never_exceed_budget(self):
        for mode in (MODE_STREAM, MODE_BLOCK, MODE_COMPRESSED):
            for payload in (os.urandom(100000), b"Z" * 100000, b"\x00" * 100000):
                pieces = [payload[i:i + 1024] for i in range(0, len(payload), 1024)]
                for chunk in encode_chunks(pieces, mode):
                    self.assertLessEqual(len(chunk), WIRE_CHUNK_SIZE)
                    self.assertGreater(len(chunk), 0)

    def test_encoded_output_is_not_stored_logical_bytes(self):
        payload = b"blocked-bytes-please"
        for mode in (MODE_BLOCK, MODE_COMPRESSED):
            encoded = join(encode_chunks([payload], mode))
            self.assertNotEqual(encoded, payload)


class TestMalformedFails(unittest.TestCase):
    def assertFails(self, chunks, decoder):
        with self.assertRaises(ModeCodecError):
            join(decoder(chunks))

    def test_block_truncated_header(self):
        self.assertFails([b"\x40\x00"], block_decode)

    def test_block_truncated_payload(self):
        self.assertFails([b"\x40\x00\x03ab"], block_decode)

    def test_block_missing_eof(self):
        self.assertFails([b"\x00\x00\x03abc"], block_decode)

    def test_block_data_after_eof(self):
        self.assertFails([b"\x40\x00\x00" + b"\x00\x00\x01z"], block_decode)

    def test_compressed_missing_eof(self):
        self.assertFails([b"\x01ab"], compressed_decode)

    def test_compressed_truncated_literal(self):
        self.assertFails([b"\x05ab"], compressed_decode)

    def test_compressed_truncated_replicate(self):
        self.assertFails([b"\x83"], compressed_decode)

    def test_compressed_invalid_control(self):
        self.assertFails([b"\x00\x0f\x00\x40"], compressed_decode)

    def test_compressed_data_after_eof(self):
        self.assertFails([b"\x00\x40\x01z"], compressed_decode)

    def test_compressed_zero_filler(self):
        self.assertFails([b"\xc0\x00\x40"], compressed_decode)

    def test_compressed_zero_replicate(self):
        self.assertFails([b"\x80\x00\x40"], compressed_decode)

    def test_compressed_duplicate_eof(self):
        self.assertFails([b"\x00\x40\x00\x40"], compressed_decode)

    def test_malformed_across_chunk_boundaries(self):
        encoded = b"\x00\x00\x05abc"  # block claiming 5 bytes but only 3
        pieces = [encoded[i:i + 2] for i in range(0, len(encoded), 2)]
        self.assertFails(pieces, block_decode)


class TestDispatcher(unittest.TestCase):
    def test_unknown_mode_encode_fails(self):
        with self.assertRaises(ModeCodecError):
            join(encode_chunks([b"x"], "X"))

    def test_unknown_mode_decode_fails(self):
        with self.assertRaises(ModeCodecError):
            join(decode_chunks([b"x"], "X"))

    def test_normalize_mode_lowercase_and_none(self):
        self.assertEqual(normalize_mode("b"), "B")
        self.assertEqual(normalize_mode(" c "), "C")
        self.assertEqual(normalize_mode(None), "S")
        self.assertEqual(normalize_transfer_type("a"), "A")
        self.assertEqual(normalize_transfer_type(None), "I")

    def test_mode_error_maps_to_426(self):
        try:
            join(decode_chunks([b"\x40\x00"], "B"))
        except ModeCodecError as error:
            self.assertEqual(error.reply_code, 426)
        else:
            self.fail("expected ModeCodecError")

    def test_stream_passthrough_identity(self):
        data = b"stream-bytes"
        self.assertEqual(list(encode_chunks([data], "S")), [data])
        self.assertEqual(list(decode_chunks([data], "S")), [data])


if __name__ == "__main__":
    unittest.main()
