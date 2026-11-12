"""Four relocated real-model checks, run explicitly via scripts/smoke.

Imports and model initialization are inside methods so discovering test names
does not load native libraries. No availability decorators: missing models are
errors when the user explicitly requests integration validation.
"""

import pathlib
import unittest

from lcats.analysis.event_role_world import nlp_backend
from lcats.analysis.linguistics import runner
from lcats.analysis.linguistics import sidecar


class SpacySmoke(unittest.TestCase):
    """Existing spaCy backend and sidecar assertions, with CPU enforcement."""

    backend_name = "spacy"

    def setUp(self):
        import spacy

        spacy.require_cpu()

    def test_spacy_backend_produces_normalized_tokens(self):
        backend = nlp_backend.SpacyBackend()
        sentences = backend.analyze("The old machine hummed.")
        self.assertEqual(len(sentences), 1)
        tokens = sentences[0].tokens
        self.assertTrue(any(t.upos == "VERB" for t in tokens))
        self.assertEqual(sum(1 for t in tokens if t.head_index == 0), 1)

    def test_spacy_smoke_backend_can_build_sidecar(self):
        backend = runner.make_backend("spacy")
        data, _ = sidecar.build_sidecar(
            story_data={
                "name": "Example",
                "body": "The old machine hummed.",
                "metadata": {"author": "A. Writer"},
            },
            story_path=pathlib.Path("c/s/story.json"),
            backend=backend,
            options=sidecar.LinguisticsOptions(backend_name="spacy"),
        )
        self.assertTrue(sidecar.validate_sidecar(data).valid)

    def test_repaired_spacy_profile_splits_problematic_surface_forms(self):
        backend = runner.make_backend(
            "spacy", tokenization_mode=sidecar.TOKENIZATION_MODE_REPAIRED
        )
        sentences = backend.analyze("and-- thirst'--_he body'd I'll d'ye")
        self.assertEqual(
            [
                "and",
                "--",
                "thirst",
                "'",
                "--",
                "_",
                "he",
                "body",
                "'d",
                "I",
                "'ll",
                "d'ye",
            ],
            [token.text for token in sentences[0].tokens],
        )


class StanzaSmoke(unittest.TestCase):
    """Existing Stanza normalized-token assertions; no native output suppression."""

    backend_name = "stanza"

    def test_stanza_backend_produces_normalized_tokens(self):
        import torch

        # CUDA_VISIBLE_DEVICES was set before this fresh interpreter started.
        self.assertFalse(torch.cuda.is_available())
        backend = nlp_backend.StanzaBackend()
        self.assertEqual(str(backend._pipeline.device), "cpu")
        sentences = backend.analyze("The old machine hummed.")
        self.assertEqual(len(sentences), 1)
        tokens = sentences[0].tokens
        self.assertTrue(any(t.upos == "VERB" for t in tokens))
        self.assertEqual(sum(1 for t in tokens if t.head_index == 0), 1)
