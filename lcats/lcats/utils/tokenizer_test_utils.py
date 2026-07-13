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

    def decode_tokens_bytes(self, tokens):
        return [chr(token).encode("utf-8") for token in tokens]


def fake_encoding_for_model(_model):
    """Return a fake encoder for model lookup patches."""
    return FakeCharacterEncoding()


def patch_chunking_encoding_for_model():
    """Patch chunking's tiktoken model lookup at the LCATS boundary."""
    return unittest.mock.patch(
        "lcats.chunking.tiktoken.encoding_for_model",
        side_effect=fake_encoding_for_model,
    )


def patch_story_analysis_get_encoder(encoder=None):
    """Patch story_analysis encoder lookup at the LCATS boundary."""
    resolved_encoder = encoder or FakeCharacterEncoding()
    return unittest.mock.patch(
        "lcats.analysis.story_analysis.get_encoder",
        return_value=resolved_encoder,
    )
