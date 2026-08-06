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
"""Tests for audioanalyser.modules.llm_providers.

Each provider's SDK is imported inside its generate() call, so these tests
inject a stub module into sys.modules rather than requiring the real package
to be installed. The call shapes asserted here were checked against the real
libraries (anthropic 0.120.2, google-genai 2.16.0, openai 1.109.1).
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
import requests

from audioanalyser.modules import llm_providers as lp


@pytest.fixture
def fake_openai():
    """Stub the openai module with a chat-completions client."""
    module = types.ModuleType("openai")
    client = MagicMock()
    client.chat.completions.create.return_value = types.SimpleNamespace(
        choices=[
            types.SimpleNamespace(
                message=types.SimpleNamespace(content="  A summary.  ")
            )
        ]
    )
    module.OpenAI = MagicMock(return_value=client)
    module.OpenAIError = type("OpenAIError", (Exception,), {})
    with patch.dict(sys.modules, {"openai": module}):
        yield module, client


@pytest.fixture
def fake_anthropic():
    """Stub the anthropic module with a Messages client."""
    module = types.ModuleType("anthropic")
    client = MagicMock()
    client.messages.create.return_value = types.SimpleNamespace(
        content=[
            types.SimpleNamespace(type="text", text="  A summary.  "),
        ]
    )
    module.Anthropic = MagicMock(return_value=client)
    with patch.dict(sys.modules, {"anthropic": module}):
        yield module, client


@pytest.fixture
def fake_genai():
    """Stub google.genai with a generate_content client."""
    google = types.ModuleType("google")
    genai = types.ModuleType("google.genai")
    gtypes = types.ModuleType("google.genai.types")

    client = MagicMock()
    client.models.generate_content.return_value = types.SimpleNamespace(
        text="  A summary.  "
    )
    genai.Client = MagicMock(return_value=client)
    gtypes.GenerateContentConfig = MagicMock(name="GenerateContentConfig")
    google.genai = genai

    with patch.dict(
        sys.modules,
        {
            "google": google,
            "google.genai": genai,
            "google.genai.types": gtypes,
        },
    ):
        yield gtypes, client


class TestModelResolution:
    def test_each_provider_has_a_default(self):
        assert set(lp.DEFAULT_MODELS) == set(lp.PROVIDERS)

    def test_llm_model_overrides_every_provider(self, clean_env):
        clean_env.setenv("LLM_MODEL", "custom-model")

        for name in lp.PROVIDERS:
            assert lp.resolve_model(name) == "custom-model"

    def test_openai_model_still_applies_to_openai(self, clean_env):
        """The variable introduced before the provider layer keeps working."""
        clean_env.delenv("LLM_MODEL", raising=False)
        clean_env.setenv("OPENAI_MODEL", "gpt-4.1-nano")

        assert lp.resolve_model("openai") == "gpt-4.1-nano"

    def test_openai_model_does_not_leak_to_other_providers(self, clean_env):
        clean_env.delenv("LLM_MODEL", raising=False)
        clean_env.setenv("OPENAI_MODEL", "gpt-4.1-nano")

        assert lp.resolve_model("anthropic") == "claude-opus-5"

    def test_llm_model_wins_over_openai_model(self, clean_env):
        clean_env.setenv("LLM_MODEL", "generic")
        clean_env.setenv("OPENAI_MODEL", "specific")

        assert lp.resolve_model("openai") == "generic"

    def test_falls_back_to_the_builtin_default(self, clean_env):
        clean_env.delenv("LLM_MODEL", raising=False)
        clean_env.delenv("OPENAI_MODEL", raising=False)

        assert lp.resolve_model("openai") == "gpt-4.1-mini"


class TestGetProvider:
    def test_defaults_to_openai(self, clean_env):
        clean_env.delenv("LLM_PROVIDER", raising=False)
        clean_env.setenv("GPT3_API_KEY", "key")

        provider = lp.get_provider()

        assert isinstance(provider, lp.OpenAIProvider)
        assert provider.model == "gpt-4.1-mini"

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("openai", lp.OpenAIProvider),
            ("anthropic", lp.AnthropicProvider),
            ("gemini", lp.GeminiProvider),
            ("ollama", lp.OllamaProvider),
        ],
    )
    def test_builds_the_named_provider(self, clean_env, name, expected):
        assert isinstance(lp.get_provider(name), expected)

    def test_reads_the_provider_from_the_environment(self, clean_env):
        clean_env.setenv("LLM_PROVIDER", "anthropic")

        assert isinstance(lp.get_provider(), lp.AnthropicProvider)

    def test_provider_name_is_case_insensitive(self, clean_env):
        assert isinstance(lp.get_provider("Anthropic"), lp.AnthropicProvider)

    def test_rejects_an_unknown_provider(self, clean_env):
        with pytest.raises(lp.ProviderError, match="Unknown provider"):
            lp.get_provider("telepathy")

    def test_passes_each_providers_own_key(self, clean_env):
        clean_env.setenv("ANTHROPIC_API_KEY", "sk-ant-xyz")

        assert lp.get_provider("anthropic").api_key == "sk-ant-xyz"

    def test_ollama_takes_a_host_not_a_key(self, clean_env):
        clean_env.setenv("OLLAMA_HOST", "http://gpu-box:11434")

        provider = lp.get_provider("ollama")

        assert provider.host == "http://gpu-box:11434"
        assert provider.api_key is None

    def test_ollama_host_defaults_to_localhost(self, clean_env):
        clean_env.delenv("OLLAMA_HOST", raising=False)

        assert lp.get_provider("ollama").host == lp.DEFAULT_OLLAMA_HOST


class TestCredentialResolution:
    """No key means "let the SDK resolve it", not "fail".

    Each SDK has its own chain - environment variables, a CLI login
    session, workload identity - and passing api_key=None would
    short-circuit it. Only a genuine SDK auth failure is an error here.
    """

    def test_openai_omits_the_key_so_the_sdk_can_resolve_one(
        self, fake_openai
    ):
        module, _ = fake_openai

        lp.OpenAIProvider("m", api_key=None).generate("sys", "text")

        assert module.OpenAI.call_args.kwargs == {}

    def test_anthropic_omits_the_key_so_a_cli_session_is_used(
        self, fake_anthropic
    ):
        """`ant auth login` stores a profile the SDK reads with no key set."""
        module, _ = fake_anthropic

        lp.AnthropicProvider("m", api_key=None).generate("sys", "text")

        assert module.Anthropic.call_args.kwargs == {}

    def test_an_explicit_key_is_still_passed_through(self, fake_anthropic):
        module, _ = fake_anthropic

        lp.AnthropicProvider("m", api_key="sk-ant-xyz").generate("s", "t")

        assert module.Anthropic.call_args.kwargs == {"api_key": "sk-ant-xyz"}

    def test_an_sdk_auth_failure_names_every_accepted_option(
        self, fake_anthropic
    ):
        module, _ = fake_anthropic
        module.AnthropicError = Exception
        module.Anthropic.side_effect = Exception("no credentials found")

        with pytest.raises(lp.ProviderError) as excinfo:
            lp.AnthropicProvider("m").generate("s", "t")

        message = str(excinfo.value)
        assert "ANTHROPIC_API_KEY" in message
        assert "ant auth login" in message

    def test_openai_auth_failure_says_there_is_no_session_login(
        self, fake_openai
    ):
        """OpenAI has no OAuth equivalent; the message should say so."""
        module, _ = fake_openai
        module.OpenAI.side_effect = module.OpenAIError("no api key")

        with pytest.raises(lp.ProviderError) as excinfo:
            lp.OpenAIProvider("m").generate("s", "t")

        message = str(excinfo.value)
        assert "OPENAI_API_KEY" in message
        assert "no session login" in message

    def test_gemini_uses_a_google_cloud_session_when_configured(
        self, fake_genai, clean_env
    ):
        """ADC via Vertex AI replaces the key entirely."""
        _, _ = fake_genai
        clean_env.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        clean_env.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
        from google import genai

        lp.GeminiProvider("m", api_key=None).generate("s", "t")

        assert genai.Client.call_args.kwargs == {
            "vertexai": True,
            "project": "my-project",
            "location": "europe-west1",
        }

    def test_gemini_location_defaults_to_global(self, fake_genai, clean_env):
        clean_env.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        clean_env.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
        from google import genai

        lp.GeminiProvider("m", api_key=None).generate("s", "t")

        assert genai.Client.call_args.kwargs["location"] == "global"

    def test_gemini_prefers_an_explicit_key_over_the_session(
        self, fake_genai, clean_env
    ):
        clean_env.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        from google import genai

        lp.GeminiProvider("m", api_key="k").generate("s", "t")

        assert genai.Client.call_args.kwargs == {"api_key": "k"}

    def test_gemini_auth_failure_mentions_the_gcloud_login(
        self, fake_genai, clean_env
    ):
        clean_env.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        from google import genai
        genai.Client.side_effect = Exception("no credentials")

        with pytest.raises(lp.ProviderError, match="gcloud auth"):
            lp.GeminiProvider("m").generate("s", "t")


class TestOpenAIProvider:
    def test_sends_system_and_user_and_returns_stripped_text(
        self, fake_openai
    ):
        module, client = fake_openai

        result = lp.OpenAIProvider("gpt-4.1-mini", api_key="k").generate(
            "instructions", "transcript", max_tokens=99, temperature=0.5
        )

        assert result == "A summary."
        module.OpenAI.assert_called_once_with(api_key="k")
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4.1-mini"
        assert kwargs["max_completion_tokens"] == 99
        assert kwargs["temperature"] == 0.5
        assert kwargs["messages"] == [
            {"role": "system", "content": "instructions"},
            {"role": "user", "content": "transcript"},
        ]

    def test_returns_empty_string_when_content_is_none(self, fake_openai):
        _, client = fake_openai
        client.chat.completions.create.return_value = types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content=None)
                )
            ]
        )

        assert lp.OpenAIProvider("m", api_key="k").generate("s", "t") == ""


class TestAnthropicProvider:
    def test_passes_the_instructions_as_the_system_parameter(
        self, fake_anthropic
    ):
        """Anthropic takes the system prompt top-level, not as a message."""
        module, client = fake_anthropic

        result = lp.AnthropicProvider("claude-opus-5", api_key="k").generate(
            "instructions", "transcript"
        )

        assert result == "A summary."
        module.Anthropic.assert_called_once_with(api_key="k")
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-opus-5"
        assert kwargs["system"] == "instructions"
        assert kwargs["messages"] == [
            {"role": "user", "content": "transcript"}
        ]

    def test_raises_the_max_tokens_floor(self, fake_anthropic):
        """Thinking shares the budget, so a summary-sized cap can starve it."""
        _, client = fake_anthropic

        lp.AnthropicProvider("m", api_key="k").generate(
            "s", "t", max_tokens=100
        )

        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == lp.ANTHROPIC_MIN_MAX_TOKENS

    def test_keeps_a_budget_larger_than_the_floor(self, fake_anthropic):
        _, client = fake_anthropic

        lp.AnthropicProvider("m", api_key="k").generate(
            "s", "t", max_tokens=50_000
        )

        assert client.messages.create.call_args.kwargs["max_tokens"] == 50_000

    def test_joins_text_blocks_and_ignores_other_block_types(
        self, fake_anthropic
    ):
        """Responses interleave thinking and text; only text is the reply."""
        _, client = fake_anthropic
        client.messages.create.return_value = types.SimpleNamespace(
            content=[
                types.SimpleNamespace(type="thinking", thinking="hmm"),
                types.SimpleNamespace(type="text", text="First."),
                types.SimpleNamespace(type="text", text="Second."),
            ]
        )

        result = lp.AnthropicProvider("m", api_key="k").generate("s", "t")

        assert result == "First.\nSecond."

    def test_returns_empty_string_when_there_is_no_text_block(
        self, fake_anthropic
    ):
        _, client = fake_anthropic
        client.messages.create.return_value = types.SimpleNamespace(content=[])

        assert lp.AnthropicProvider("m", api_key="k").generate("s", "t") == ""


class TestGeminiProvider:
    def test_sends_system_instruction_and_contents(self, fake_genai):
        gtypes, client = fake_genai

        result = lp.GeminiProvider("gemini-2.5-flash", api_key="k").generate(
            "instructions", "transcript", max_tokens=99, temperature=0.5
        )

        assert result == "A summary."
        kwargs = client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["contents"] == "transcript"
        config_kwargs = gtypes.GenerateContentConfig.call_args.kwargs
        assert config_kwargs["system_instruction"] == "instructions"
        assert config_kwargs["max_output_tokens"] == 99
        assert config_kwargs["temperature"] == 0.5

    def test_returns_empty_string_when_text_is_none(self, fake_genai):
        _, client = fake_genai
        client.models.generate_content.return_value = types.SimpleNamespace(
            text=None
        )

        assert lp.GeminiProvider("m", api_key="k").generate("s", "t") == ""


class TestOllamaProvider:
    def _response(self, payload):
        response = MagicMock()
        response.json.return_value = payload
        return response

    @pytest.fixture(autouse=True)
    def _model_is_available(self):
        """generate() checks the model exists before sending the prompt."""
        with patch.object(
            lp.OllamaProvider,
            "available_models",
            return_value=["llama3.1", "m"],
        ):
            yield

    def test_posts_to_the_chat_endpoint_and_returns_content(self):
        response = self._response({"message": {"content": "  A summary.  "}})

        with patch.object(requests, "post", return_value=response) as post:
            result = lp.OllamaProvider("llama3.1").generate(
                "instructions", "transcript", max_tokens=99, temperature=0.5
            )

        assert result == "A summary."
        (url,) = post.call_args.args
        assert url == f"{lp.DEFAULT_OLLAMA_HOST}/api/chat"
        body = post.call_args.kwargs["json"]
        assert body["model"] == "llama3.1"
        assert body["stream"] is False
        assert body["options"] == {"temperature": 0.5, "num_predict": 99}
        assert body["messages"] == [
            {"role": "system", "content": "instructions"},
            {"role": "user", "content": "transcript"},
        ]

    def test_needs_no_api_key(self):
        response = self._response({"message": {"content": "text"}})

        with patch.object(requests, "post", return_value=response):
            assert lp.OllamaProvider("m").generate("s", "t") == "text"

    def test_strips_a_trailing_slash_from_the_host(self):
        assert lp.OllamaProvider("m", host="http://box:1/").host == (
            "http://box:1"
        )

    def test_explains_how_to_start_the_server_when_unreachable(self):
        with patch.object(
            requests,
            "post",
            side_effect=requests.ConnectionError("refused"),
        ):
            with pytest.raises(lp.ProviderError, match="ollama serve"):
                lp.OllamaProvider("m").generate("s", "t")

    def test_reports_an_error_status(self):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("404")

        with patch.object(requests, "post", return_value=response):
            with pytest.raises(lp.ProviderError, match="Could not reach"):
                lp.OllamaProvider("m").generate("s", "t")

    def test_reports_a_non_json_body(self):
        response = MagicMock()
        response.json.side_effect = lp.json.JSONDecodeError("bad", "doc", 0)

        with patch.object(requests, "post", return_value=response):
            with pytest.raises(lp.ProviderError, match="non-JSON"):
                lp.OllamaProvider("m").generate("s", "t")

    def test_returns_empty_string_when_the_payload_has_no_content(self):
        with patch.object(requests, "post", return_value=self._response({})):
            assert lp.OllamaProvider("m").generate("s", "t") == ""


class TestOllamaModelDiscovery:
    """The right model is a property of the host, not of this package."""

    def test_lists_the_models_the_server_has(self):
        response = MagicMock()
        response.json.return_value = {
            "models": [{"name": "llama3.1:8b"}, {"name": "gemma3:4b"}]
        }

        with patch.object(requests, "get", return_value=response) as get:
            models = lp.OllamaProvider("m").available_models()

        assert models == ["llama3.1:8b", "gemma3:4b"]
        assert get.call_args.args[0].endswith("/api/tags")

    def test_a_bare_family_name_matches_a_tagged_model(self):
        """`llama3.1` should match a pulled `llama3.1:8b`."""
        with patch.object(
            lp.OllamaProvider, "available_models", return_value=["llama3.1:8b"]
        ):
            response = MagicMock()
            response.json.return_value = {"message": {"content": "ok"}}
            with patch.object(requests, "post", return_value=response):
                assert lp.OllamaProvider("llama3.1").generate("s", "t") == "ok"

    def test_an_absent_model_names_what_is_available(self):
        with patch.object(
            lp.OllamaProvider, "available_models", return_value=["gemma3:4b"]
        ):
            with pytest.raises(lp.ProviderError) as excinfo:
                lp.OllamaProvider("llama3.1").generate("s", "t")

        message = str(excinfo.value)
        assert "ollama pull llama3.1" in message
        assert "gemma3:4b" in message

    def test_says_none_when_the_server_has_no_models(self):
        with patch.object(
            lp.OllamaProvider, "available_models", return_value=[]
        ):
            with pytest.raises(lp.ProviderError, match="none"):
                lp.OllamaProvider("llama3.1").generate("s", "t")

    def test_unreachable_server_explains_how_to_start_it(self):
        with patch.object(
            requests, "get", side_effect=requests.ConnectionError("refused")
        ):
            with pytest.raises(lp.ProviderError, match="ollama serve"):
                lp.OllamaProvider("m").available_models()

    def test_reports_a_non_json_tags_response(self):
        response = MagicMock()
        response.json.side_effect = lp.json.JSONDecodeError("bad", "doc", 0)

        with patch.object(requests, "get", return_value=response):
            with pytest.raises(lp.ProviderError, match="Could not reach"):
                lp.OllamaProvider("m").available_models()


class TestMissingSdk:
    @pytest.mark.parametrize(
        ("cls", "module_name", "extra"),
        [
            (lp.AnthropicProvider, "anthropic", "audioanalyser[anthropic]"),
            (lp.GeminiProvider, "google.genai", "audioanalyser[gemini]"),
        ],
    )
    def test_names_the_install_command(self, cls, module_name, extra):
        """A missing optional SDK must say how to get it."""

        def deny(name, *args, **kwargs):
            if name == module_name or name.startswith("google"):
                raise ImportError(f"No module named {name!r}")
            return original(name, *args, **kwargs)

        original = (
            __builtins__["__import__"]
            if isinstance(__builtins__, dict)
            else __builtins__.__import__
        )

        with patch("builtins.__import__", side_effect=deny):
            with pytest.raises(lp.ProviderError, match=r"pip install"):
                cls("m", api_key="k").generate("s", "t")
