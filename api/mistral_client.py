"""Mistral AI ModelClient integration."""

from typing import Dict, Optional, Any, List
import logging
import json
import aiohttp
import requests
from requests.exceptions import RequestException, Timeout

from adalflow.core.model_client import ModelClient
from adalflow.core.types import (
    CompletionUsage,
    ModelType,
    GeneratorOutput,
)

log = logging.getLogger(__name__)


class MistralClient(ModelClient):
    __doc__ = r"""A component wrapper for the Mistral AI API client.

    Mistral AI provides state-of-the-art open and commercial LLM models.
    Their API is compatible with OpenAI's format for easy integration.

    Visit https://docs.mistral.ai/api for more details.

    Example:
        ```python
        from api.mistral_client import MistralClient
        import adalflow as adal

        client = MistralClient()
        generator = adal.Generator(
            model_client=client,
            model_kwargs={"model": "mistral-large-latest"}
        )
        ```

    Supported Models:
        - mistral-large-latest: Latest Mistral Large model
        - mistral-medium-latest: Mistral Medium model
        - mistral-small-latest: Mistral Small model
        - open-mistral-7b: Open source 7B model
        - open-mixtral-8x7b: Open source Mixtral 8x7B model
        - open-mixtral-8x22b: Open source Mixtral 8x22B model
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the Mistral AI client."""
        super().__init__(*args, **kwargs)
        self.sync_client = self.init_sync_client()
        self.async_client = None  # Initialize async client only when needed

    def init_sync_client(self):
        """Initialize the synchronous Mistral client."""
        import os
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            log.warning("MISTRAL_API_KEY not configured")

        return {
            "api_key": api_key,
            "base_url": "https://api.mistral.ai/v1"
        }

    def init_async_client(self):
        """Initialize the asynchronous Mistral client."""
        import os
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            log.warning("MISTRAL_API_KEY not configured")

        return {
            "api_key": api_key,
            "base_url": "https://api.mistral.ai/v1"
        }

    def convert_inputs_to_api_kwargs(
        self, input: Any, model_kwargs: Dict = None, model_type: ModelType = None
    ) -> Dict:
        """Convert AdalFlow inputs to Mistral API format."""
        model_kwargs = model_kwargs or {}

        if model_type == ModelType.LLM:
            # Handle LLM generation
            messages = []

            # Convert input to messages format if it's a string
            if isinstance(input, str):
                messages = [{"role": "user", "content": input}]
            elif isinstance(input, list) and all(isinstance(msg, dict) for msg in input):
                messages = input
            else:
                raise ValueError(
                    f"Unsupported input format for Mistral: {type(input)}")

            log.debug(f"Messages for Mistral: {messages}")

            api_kwargs = {
                "messages": messages,
                **model_kwargs
            }

            # Ensure model is specified
            if "model" not in api_kwargs:
                api_kwargs["model"] = "mistral-large-latest"

            return api_kwargs

        else:
            raise ValueError(f"model_type {model_type} is not supported")

    def parse_chat_completion(self, completion: Dict) -> GeneratorOutput:
        """Parse Mistral chat completion response to GeneratorOutput.

        Args:
            completion: Raw API response from Mistral

        Returns:
            GeneratorOutput with parsed data
        """
        try:
            usage = completion.get("usage", {})
            message = completion["choices"][0]["message"]

            return GeneratorOutput(
                data=message.get("content"),
                error=None,
                usage=CompletionUsage(
                    completion_tokens=usage.get("completion_tokens", 0),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0)
                ),
                raw_response=json.dumps(completion)
            )
        except (KeyError, IndexError) as e:
            log.error(f"Error parsing Mistral completion: {e}")
            return GeneratorOutput(
                data=None,
                error=f"Failed to parse completion: {str(e)}",
                raw_response=json.dumps(completion)
            )

    def call(self, api_kwargs: Dict, model_type: ModelType) -> GeneratorOutput:
        """Make synchronous call to Mistral API.

        Args:
            api_kwargs: API parameters
            model_type: Type of model (must be LLM)

        Returns:
            GeneratorOutput with response data
        """
        if model_type != ModelType.LLM:
            raise ValueError(f"model_type {model_type} is not supported")

        headers = {
            "Authorization": f"Bearer {self.sync_client['api_key']}",
            "Content-Type": "application/json"
        }

        url = f"{self.sync_client['base_url']}/chat/completions"

        try:
            log.debug(f"Calling Mistral API with model: {api_kwargs.get('model')}")
            response = requests.post(
                url,
                json=api_kwargs,
                headers=headers,
                timeout=120
            )
            response.raise_for_status()
            completion = response.json()
            return self.parse_chat_completion(completion)

        except Timeout:
            log.error("Mistral API request timed out")
            return GeneratorOutput(
                data=None,
                error="Request timed out"
            )
        except RequestException as e:
            log.error(f"Mistral API request failed: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"API request failed: {str(e)}"
            )
        except Exception as e:
            log.error(f"Unexpected error calling Mistral API: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"Unexpected error: {str(e)}"
            )

    async def acall(self, api_kwargs: Dict, model_type: ModelType) -> GeneratorOutput:
        """Make asynchronous call to Mistral API.

        Args:
            api_kwargs: API parameters
            model_type: Type of model (must be LLM)

        Returns:
            GeneratorOutput with response data
        """
        if model_type != ModelType.LLM:
            raise ValueError(f"model_type {model_type} is not supported")

        if self.async_client is None:
            self.async_client = self.init_async_client()

        headers = {
            "Authorization": f"Bearer {self.async_client['api_key']}",
            "Content-Type": "application/json"
        }

        url = f"{self.async_client['base_url']}/chat/completions"

        try:
            log.debug(f"Async calling Mistral API with model: {api_kwargs.get('model')}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=api_kwargs,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response.raise_for_status()
                    completion = await response.json()
                    return self.parse_chat_completion(completion)

        except aiohttp.ClientTimeout:
            log.error("Mistral API async request timed out")
            return GeneratorOutput(
                data=None,
                error="Request timed out"
            )
        except aiohttp.ClientError as e:
            log.error(f"Mistral API async request failed: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"API request failed: {str(e)}"
            )
        except Exception as e:
            log.error(f"Unexpected error in async Mistral API call: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"Unexpected error: {str(e)}"
            )
