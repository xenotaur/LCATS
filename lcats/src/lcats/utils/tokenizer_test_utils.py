"""Shared fake tokenizer helpers for deterministic unit tests.

The fake encoder uses one token per character (Unicode code point).
That makes token counts deterministic and decode/encode round-trips lossless
for tests that need chunking behavior.
"""

import unittest.mock


class FakeCharacterEncoding:
    """Character-level fake encoder compatible with the tiktoken API subset."""

    def encode(self, text, **_kwargs):
        return [ord(character) for character in text]

    def decode(self, tokens):
        return "".join(chr(token) for token in tokens)

    def decode_bytes(self, tokens):
        return self.decode(tokens).encode("utf-8")


class FakeByteEncoding:
    """Byte-level fake encoder: one token per UTF-8 byte.

    Unlike `FakeCharacterEncoding`, a multi-byte character's bytes can span
    more than one token, so chunk boundaries can fall mid-character — this
    is what real BPE tokenizers do and what `FakeCharacterEncoding` cannot
    exercise.
    """

    def encode(self, text, **_kwargs):
        return list(text.encode("utf-8"))

    def decode(self, tokens):
        return bytes(tokens).decode("utf-8", errors="replace")

    def decode_bytes(self, tokens):
        return bytes(tokens)


def fake_encoding_for_model(_model):
    """Return a fake encoder for model lookup patches."""
    return FakeCharacterEncoding()


def patch_chunking_encoding_for_model():
    """Patch chunking's tiktoken model lookup at the LCATS boundary."""
    return unittest.mock.patch(
        "lcats.chunking.tiktoken.encoding_for_model",
        side_effect=fake_encoding_for_model,
    )


def patch_chunking_encoding_for_model_with(encoder):
    """Patch chunking's tiktoken model lookup to return a specific encoder."""
    return unittest.mock.patch(
        "lcats.chunking.tiktoken.encoding_for_model",
        return_value=encoder,
    )


def patch_story_analysis_get_encoder(encoder=None):
    """Patch story_analysis encoder lookup at the LCATS boundary."""
    resolved_encoder = encoder or FakeCharacterEncoding()
    return unittest.mock.patch(
        "lcats.analysis.story_analysis.get_encoder",
        return_value=resolved_encoder,
    )
