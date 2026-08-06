# Copyright (C) 2023-2024 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""End-to-end tests against a live Ollama server.

Every other test in this suite mocks the provider, which proves the request
is well-formed but never that a model actually answers it. These run the real
pipeline - config, transcript, generation, and all three output formats -
against a local server.

They skip when no server is reachable, so CI and contributors without Ollama
are unaffected. Run them with a server up:

    ollama serve &
    ollama pull <model>
    pytest -m integration

The model is whatever the server already has, so the test never depends on a
particular one being pulled.
"""

import json
import sqlite3

import pytest

from audioanalyser.modules import azure_recommendation as rec
from audioanalyser.modules import llm_providers as lp

pytestmark = pytest.mark.integration


@pytest.fixture
def live_ollama():
    """Skip unless a reachable server has at least one model."""
    provider = lp.OllamaProvider("unused")
    try:
        models = provider.available_models()
    except lp.ProviderError as exc:
        pytest.skip(f"no Ollama server: {exc}")
    if not models:
        pytest.skip("Ollama is running but has no models pulled")
    return models[0]


class TestLiveGeneration:
    def test_the_provider_returns_real_generated_text(self, live_ollama):
        provider = lp.OllamaProvider(live_ollama)

        result = provider.generate(
            system=(
                "You are a terse assistant. Reply with exactly one short "
                "sentence and no preamble."
            ),
            user_text="Say that the audio pipeline works.",
            max_tokens=64,
            temperature=0.0,
        )

        assert result, "the model returned no text"
        assert len(result.split()) >= 2

    def test_an_unpulled_model_names_what_is_available(self, live_ollama):
        """The failure should be actionable, not a bare 404."""
        provider = lp.OllamaProvider("definitely-not-pulled-xyz")

        with pytest.raises(lp.ProviderError) as excinfo:
            provider.generate("system", "user")

        message = str(excinfo.value)
        assert "ollama pull" in message
        assert live_ollama in message


class TestLivePipeline:
    def test_generates_and_saves_a_recommendation_end_to_end(
        self, live_ollama, full_env, clean_env, folders
    ):
        """Drives the real feature: transcript in, three artefacts out."""
        clean_env.setenv("LLM_PROVIDER", "ollama")
        clean_env.setenv("LLM_MODEL", live_ollama)
        clean_env.setenv("MAX_OUTPUT_LENGTH", "160")
        (folders["transcripts"] / "call.txt").write_text(
            "Customer reports the billing page times out on checkout. "
            "They were charged twice and want a refund."
        )

        rec.azure_recommendation()

        out = folders["recommendations"]
        text = (out / "azure_recommendation-call.txt").read_text()
        assert text.strip(), "the saved recommendation is empty"

        payload = json.loads(
            (out / "azure_recommendation-call.json").read_text()
        )
        assert payload["recommendation"].strip() == text.strip()

        with sqlite3.connect(out / "recommendations.db") as conn:
            rows = conn.execute(
                "SELECT filename, transcription FROM recommendations"
            ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "call.txt"
        assert rows[0][1].strip() == text.strip()
