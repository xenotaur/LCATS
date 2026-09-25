"""Tests for the experiment-09 Parquet bridge."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

from lcats.analysis.event_role_world import nlp_backend
from lcats.analysis.linguistics import lexicon, sidecar

_BRIDGE_PATH = pathlib.Path(__file__).resolve().parent / "parquet_bridge.py"
_SPEC = importlib.util.spec_from_file_location("parquet_bridge", _BRIDGE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
parquet_bridge = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = parquet_bridge
_SPEC.loader.exec_module(parquet_bridge)


@unittest.skipUnless(shutil.which("python") is not None, "python unavailable")
class ParquetBridgeTest(unittest.TestCase):
    def setUp(self):
        try:
            __import__("pyarrow")
        except ImportError as error:
            self.skipTest(f"pyarrow unavailable: {error}")

    def test_exports_and_restores_v2_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = root / "source" / "alpha" / "one"
            source.mkdir(parents=True)
            body = "Alice saw the machine."
            story_path = pathlib.Path("alpha/one/story.json")
            story_data = {"name": "Fixture", "body": body}
            story_record_path = source / "story.json"
            story_record_path.write_text(json.dumps(story_data), encoding="utf-8")
            backend = nlp_backend.FakeNLPBackend(
                sentences=[
                    nlp_backend.SentenceRecord(
                        tokens=[
                            _token(body, "Alice", "PROPN", 2, 0),
                            _token(body, "saw", "VERB", 0, 0),
                            _token(body, "machine", "NOUN", 2, 0),
                        ],
                        start_char=0,
                        end_char=len(body),
                    )
                ]
            )
            options = sidecar.LinguisticsOptions(
                backend_name="fake",
                include_token_detail=True,
                token_detail_version=sidecar.TOKEN_DETAIL_VERSION_V2,
            )
            compact, detail = sidecar.build_sidecar(
                story_data=story_data,
                story_path=story_path,
                backend=backend,
                options=options,
            )
            sidecar.write_json_atomic(source / sidecar.SIDECAR_FILENAME, compact)
            sidecar.write_json_atomic(source / sidecar.TOKEN_DETAIL_FILENAME, detail)
            sidecar.write_json_atomic(
                source / lexicon.LEXICON_FILENAME, lexicon.build_lexicon(detail)
            )

            manifest = parquet_bridge.export_token_details(
                source_root=root / "source", output_dir=root / "parquet"
            )
            restore = parquet_bridge.restore_token_details(
                parquet_dir=root / "parquet", output_root=root / "restored"
            )

            restored_detail = root / "restored" / "alpha" / "one" / "linguistics.tokens.json"
            restored_compact = root / "restored" / "alpha" / "one" / "linguistics.json"
            restored_lexicon = root / "restored" / "alpha" / "one" / "linguistics.lexicon.json"
            self.assertEqual(1, manifest["story_count"])
            self.assertEqual(3, manifest["token_count"])
            self.assertEqual(1, restore["restored_token_details"])
            self.assertEqual(
                (source / sidecar.TOKEN_DETAIL_FILENAME).read_text(encoding="utf-8"),
                restored_detail.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (source / sidecar.SIDECAR_FILENAME).read_text(encoding="utf-8"),
                restored_compact.read_text(encoding="utf-8"),
            )
            self.assertTrue(restored_lexicon.exists())

    def test_non_string_compact_json_cell_is_treated_as_missing(self):
        self.assertEqual("", parquet_bridge._optional_json_cell(None))
        self.assertEqual("", parquet_bridge._optional_json_cell(float("nan")))
        self.assertEqual("{}", parquet_bridge._optional_json_cell("{}"))


def _token(
    body: str, text: str, upos: str, head_index: int, cursor: int
) -> nlp_backend.TokenRecord:
    start = body.find(text, cursor)
    return nlp_backend.TokenRecord(
        text=text,
        lemma=text.casefold(),
        upos=upos,
        xpos=upos,
        feats="",
        head_index=head_index,
        deprel="dep" if head_index else "root",
        start_char=start,
        end_char=start + len(text),
    )


if __name__ == "__main__":
    unittest.main()
