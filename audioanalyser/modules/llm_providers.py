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
"""Pluggable text-generation backends.

Each provider takes the same three inputs - a system instruction, the user
text, and generation settings - and returns plain text, so callers do not
branch on which service is configured.

Every SDK is imported inside its provider rather than at module scope, so
installing one backend never requires the others. Selecting a provider whose
SDK is absent raises ProviderError naming the install command.
"""

import json
import logging
import os
from abc import ABC, abstractmethod

import requests

logger = logging.getLogger("LLMProviders")

# Per-provider defaults, overridable with LLM_MODEL.
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-opus-5",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.1",
}

DEFAULT_OLLAMA_HOST = "http://localhost:11434"

# Anthropic bills thinking against the same max_tokens as the reply, and
# adaptive thinking is on by default, so a budget sized for the summary alone
# can be consumed before any text is produced.
ANTHROPIC_MIN_MAX_TOKENS = 4096


class ProviderError(RuntimeError):
    """Raised when a provider is unusable: missing SDK, key, or config."""


class Provider(ABC):
    """A text-generation backend."""

    #: Environment variable holding this provider's API key, if it needs one.
    api_key_env = ""

    #: How to authenticate, including any option that is not an API key.
    credential_help = ""

    def __init__(self, model, api_key=None):
        self.model = model
        self.api_key = api_key

    @abstractmethod
    def generate(
        self, system, user_text, max_tokens=2048, temperature=0.8
    ) -> str:
        """Return the model's reply as plain text."""

    def _credential_kwargs(self):
        """Return client kwargs for an explicit key, or nothing.

        An empty dict is deliberate rather than a failure: every SDK here
        resolves credentials itself - environment variables, a CLI login
        session, workload identity - and passing ``api_key=None`` would
        short-circuit that. Authentication is the SDK's job; ours is to
        explain the options when it finds nothing.
        """
        return {"api_key": self.api_key} if self.api_key else {}

    def _no_credentials(self, exc):
        """Wrap an SDK authentication failure with every accepted option."""
        return ProviderError(
            f"{type(self).__name__} could not authenticate: {exc}. "
            f"{self.credential_help}"
        )


class OpenAIProvider(Provider):
    """OpenAI chat completions."""

    api_key_env = "GPT3_API_KEY"
    credential_help = (
        "Set GPT3_API_KEY, or OPENAI_API_KEY which the SDK reads itself. "
        "OpenAI has no session login; the API accepts keys only."
    )

    def generate(self, system, user_text, max_tokens=2048, temperature=0.8):
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - openai is required
            raise ProviderError(
                "The openai package is not installed. "
                "Install it with: pip install openai"
            ) from exc

        try:
            client = openai.OpenAI(**self._credential_kwargs())
        except openai.OpenAIError as exc:
            raise self._no_credentials(exc) from exc
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            temperature=temperature,
            max_completion_tokens=max_tokens,
            n=1,
            stop=None,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""


class AnthropicProvider(Provider):
    """Anthropic Messages API."""

    api_key_env = "ANTHROPIC_API_KEY"
    credential_help = (
        "Set ANTHROPIC_API_KEY, or sign in once with `ant auth login` - the "
        "SDK reads that session from ~/.config/anthropic with no key set. "
        "ANTHROPIC_AUTH_TOKEN and workload identity federation also work; "
        "`ant auth status` shows which source is active."
    )

    def generate(self, system, user_text, max_tokens=2048, temperature=0.8):
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "The anthropic package is not installed. Install it with: "
                "pip install 'audioanalyser[anthropic]'"
            ) from exc

        # No explicit key means "let the SDK resolve it", not "fail": it
        # falls back to ANTHROPIC_AUTH_TOKEN, then an `ant auth login`
        # profile, then workload identity federation.
        try:
            client = anthropic.Anthropic(**self._credential_kwargs())
        except anthropic.AnthropicError as exc:
            raise self._no_credentials(exc) from exc
        response = client.messages.create(
            model=self.model,
            # The instruction block is a top-level parameter here, not a
            # message with a system role as in the OpenAI shape.
            system=system,
            messages=[{"role": "user", "content": user_text}],
            max_tokens=max(max_tokens, ANTHROPIC_MIN_MAX_TOKENS),
        )
        # Responses carry a list of blocks; only the text ones are the reply.
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(parts).strip()


class GeminiProvider(Provider):
    """Google Gemini (Agy)."""

    api_key_env = "GEMINI_API_KEY"
    credential_help = (
        "Set GEMINI_API_KEY, or use a Google Cloud session: run "
        "`gcloud auth application-default login`, then set "
        "GOOGLE_CLOUD_PROJECT (and optionally GOOGLE_CLOUD_LOCATION) to "
        "route through Vertex AI with no key."
    )

    def _client(self, genai):
        """Build a client from a key, or from a Google Cloud session.

        Vertex AI mode authenticates with application-default credentials,
        so a `gcloud auth application-default login` session works in place
        of a key. Selected by GOOGLE_CLOUD_PROJECT being set.
        """
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.api_key and project:
            return genai.Client(
                vertexai=True,
                project=project,
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
            )
        return genai.Client(**self._credential_kwargs())

    def generate(self, system, user_text, max_tokens=2048, temperature=0.8):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderError(
                "The google-genai package is not installed. Install it with: "
                "pip install 'audioanalyser[gemini]'"
            ) from exc

        try:
            client = self._client(genai)
        except Exception as exc:
            raise self._no_credentials(exc) from exc
        response = client.models.generate_content(
            model=self.model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return (response.text or "").strip()


class OllamaProvider(Provider):
    """A local Ollama server.

    Speaks the HTTP API directly: no SDK to install, no key, and transcripts
    never leave the machine.
    """

    api_key_env = ""

    def __init__(self, model, api_key=None, host=None):
        super().__init__(model, api_key)
        self.host = (host or DEFAULT_OLLAMA_HOST).rstrip("/")

    def available_models(self):
        """Return the models this server has pulled.

        Raises:
            ProviderError: If the server cannot be reached.
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"Could not reach Ollama at {self.host}: {exc}. "
                "Is `ollama serve` running?"
            ) from exc
        return [m.get("name", "") for m in payload.get("models", [])]

    def _check_model(self):
        """Fail with the actual model list rather than a generic 404.

        Which models exist is a property of the machine, not of this package,
        so the default here is a guess that a given host may not have pulled.
        """
        models = self.available_models()
        # Ollama names are "family:tag"; accept a bare family name too.
        families = {name.split(":", 1)[0] for name in models}
        if self.model in models or self.model in families:
            return
        raise ProviderError(
            f"Ollama at {self.host} has no model {self.model!r}. "
            f"Pull it with `ollama pull {self.model}`, set LLM_MODEL to one "
            f"it already has ({', '.join(sorted(models)) or 'none'}), or "
            "point OLLAMA_HOST at a different server."
        )

    def generate(self, system, user_text, max_tokens=2048, temperature=0.8):
        self._check_model()
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_text},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
                timeout=300,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderError(
                f"Could not reach Ollama at {self.host}: {exc}. "
                "Is `ollama serve` running?"
            ) from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Ollama returned a non-JSON response: {exc}"
            ) from exc

        return (payload.get("message", {}).get("content") or "").strip()


PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def resolve_model(provider_name):
    """Return the model for a provider.

    LLM_MODEL wins; OPENAI_MODEL still applies to the openai provider so
    existing configurations keep working; otherwise the built-in default.
    """
    model = os.getenv("LLM_MODEL")
    if model:
        return model
    if provider_name == "openai":
        legacy = os.getenv("OPENAI_MODEL")
        if legacy:
            return legacy
    return DEFAULT_MODELS[provider_name]


def get_provider(name=None):
    """Build the configured provider.

    Args:
        name: Provider name; defaults to LLM_PROVIDER, then "openai".

    Raises:
        ProviderError: If the name is not a known provider.
    """
    provider_name = (name or os.getenv("LLM_PROVIDER") or "openai").lower()
    provider_cls = PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise ProviderError(
            f"Unknown provider {provider_name!r}. "
            f"Choose one of: {', '.join(sorted(PROVIDERS))}."
        )

    model = resolve_model(provider_name)
    logger.info(f"Using {provider_name} provider with model {model}")

    if provider_name == "ollama":
        return provider_cls(model, host=os.getenv("OLLAMA_HOST"))

    api_key = os.getenv(provider_cls.api_key_env)
    return provider_cls(model, api_key=api_key)
