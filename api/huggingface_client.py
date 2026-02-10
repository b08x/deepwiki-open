"""HuggingFace Inference API ModelClient integration."""

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


class HuggingFaceClient(ModelClient):
    __doc__ = r"""A component wrapper for the HuggingFace Inference API client.

    HuggingFace provides access to thousands of open-source models through their Inference API.
    Supports both serverless (free tier) and dedicated endpoints.

    Visit https://huggingface.co/docs/api-inference for more details.

    Example:
        ```python
        from api.huggingface_client import HuggingFaceClient
        import adalflow as adal

        client = HuggingFaceClient()
        generator = adal.Generator(
            model_client=client,
            model_kwargs={"model": "meta-llama/Llama-3.3-70B-Instruct"}
        )
        ```

    Popular Models:
        - meta-llama/Llama-3.3-70B-Instruct: Latest Llama model
        - mistralai/Mistral-7B-Instruct-v0.3: Mistral 7B instruct
        - google/gemma-2-9b-it: Gemma 2 9B instruct
        - Qwen/Qwen2.5-72B-Instruct: Qwen 2.5 72B instruct
        - microsoft/Phi-3-mini-4k-instruct: Phi 3 mini

    Note: Some models may require Pro subscription or dedicated endpoints.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the HuggingFace client."""
        super().__init__(*args, **kwargs)
        self.sync_client = self.init_sync_client()
        self.async_client = None  # Initialize async client only when needed

    def init_sync_client(self):
        """Initialize the synchronous HuggingFace client."""
        import os
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            log.warning("HUGGINGFACE_API_KEY not configured")

        return {
            "api_key": api_key,
            "base_url": "https://api-inference.huggingface.co/models"
        }

    def init_async_client(self):
        """Initialize the asynchronous HuggingFace client."""
        import os
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            log.warning("HUGGINGFACE_API_KEY not configured")

        return {
            "api_key": api_key,
            "base_url": "https://api-inference.huggingface.co/models"
        }

    def convert_inputs_to_api_kwargs(
        self, input: Any, model_kwargs: Dict = None, model_type: ModelType = None
    ) -> Dict:
        """Convert AdalFlow inputs to HuggingFace Inference API format."""
        model_kwargs = model_kwargs or {}

        if model_type == ModelType.LLM:
            # Handle LLM generation
            # HuggingFace Inference API typically uses 'inputs' parameter
            if isinstance(input, str):
                api_kwargs = {
                    "inputs": input,
                    **model_kwargs
                }
            elif isinstance(input, list) and all(isinstance(msg, dict) for msg in input):
                # Convert messages to a single text input
                # HuggingFace models often expect formatted prompts
                formatted_input = self._format_messages(input)
                api_kwargs = {
                    "inputs": formatted_input,
                    **model_kwargs
                }
            else:
                raise ValueError(
                    f"Unsupported input format for HuggingFace: {type(input)}")

            log.debug(f"Input for HuggingFace: {api_kwargs['inputs'][:100]}...")

            # Ensure model is specified
            if "model" not in api_kwargs:
                api_kwargs["model"] = "meta-llama/Llama-3.3-70B-Instruct"

            return api_kwargs

        else:
            raise ValueError(f"model_type {model_type} is not supported")

    def _format_messages(self, messages: List[Dict]) -> str:
        """Format chat messages into a single string for HuggingFace models.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            Formatted string suitable for HuggingFace models
        """
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted += f"System: {content}\n\n"
            elif role == "user":
                formatted += f"User: {content}\n\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n\n"

        formatted += "Assistant:"  # Prompt for response
        return formatted.strip()

    def parse_text_generation(self, response: Any) -> GeneratorOutput:
        """Parse HuggingFace text generation response to GeneratorOutput.

        Args:
            response: Raw API response from HuggingFace

        Returns:
            GeneratorOutput with parsed data
        """
        try:
            # HuggingFace Inference API can return different formats
            if isinstance(response, list) and len(response) > 0:
                # Format: [{"generated_text": "..."}]
                generated_text = response[0].get("generated_text", "")
            elif isinstance(response, dict):
                # Format: {"generated_text": "..."}
                generated_text = response.get("generated_text", "")
            else:
                generated_text = str(response)

            return GeneratorOutput(
                data=generated_text,
                error=None,
                usage=None,  # HuggingFace Inference API doesn't provide usage by default
                raw_response=json.dumps(response)
            )
        except Exception as e:
            log.error(f"Error parsing HuggingFace response: {e}")
            return GeneratorOutput(
                data=None,
                error=f"Failed to parse response: {str(e)}",
                raw_response=json.dumps(response)
            )

    def call(self, api_kwargs: Dict, model_type: ModelType) -> GeneratorOutput:
        """Make synchronous call to HuggingFace Inference API.

        Args:
            api_kwargs: API parameters
            model_type: Type of model (must be LLM)

        Returns:
            GeneratorOutput with response data
        """
        if model_type != ModelType.LLM:
            raise ValueError(f"model_type {model_type} is not supported")

        model_id = api_kwargs.pop("model", "meta-llama/Llama-3.3-70B-Instruct")
        headers = {
            "Authorization": f"Bearer {self.sync_client['api_key']}",
            "Content-Type": "application/json"
        }

        url = f"{self.sync_client['base_url']}/{model_id}"

        # Prepare payload
        payload = {
            "inputs": api_kwargs["inputs"],
            "parameters": {
                "max_new_tokens": api_kwargs.get("max_tokens", 512),
                "temperature": api_kwargs.get("temperature", 0.7),
                "top_p": api_kwargs.get("top_p", 0.9),
                "do_sample": True,
                "return_full_text": False
            }
        }

        try:
            log.debug(f"Calling HuggingFace API with model: {model_id}")
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return self.parse_text_generation(result)

        except Timeout:
            log.error("HuggingFace API request timed out")
            return GeneratorOutput(
                data=None,
                error="Request timed out"
            )
        except RequestException as e:
            log.error(f"HuggingFace API request failed: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"API request failed: {str(e)}"
            )
        except Exception as e:
            log.error(f"Unexpected error calling HuggingFace API: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"Unexpected error: {str(e)}"
            )

    async def acall(self, api_kwargs: Dict, model_type: ModelType) -> GeneratorOutput:
        """Make asynchronous call to HuggingFace Inference API.

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

        model_id = api_kwargs.pop("model", "meta-llama/Llama-3.3-70B-Instruct")
        headers = {
            "Authorization": f"Bearer {self.async_client['api_key']}",
            "Content-Type": "application/json"
        }

        url = f"{self.async_client['base_url']}/{model_id}"

        # Prepare payload
        payload = {
            "inputs": api_kwargs["inputs"],
            "parameters": {
                "max_new_tokens": api_kwargs.get("max_tokens", 512),
                "temperature": api_kwargs.get("temperature", 0.7),
                "top_p": api_kwargs.get("top_p", 0.9),
                "do_sample": True,
                "return_full_text": False
            }
        }

        try:
            log.debug(f"Async calling HuggingFace API with model: {model_id}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return self.parse_text_generation(result)

        except aiohttp.ClientTimeout:
            log.error("HuggingFace API async request timed out")
            return GeneratorOutput(
                data=None,
                error="Request timed out"
            )
        except aiohttp.ClientError as e:
            log.error(f"HuggingFace API async request failed: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"API request failed: {str(e)}"
            )
        except Exception as e:
            log.error(f"Unexpected error in async HuggingFace API call: {str(e)}")
            return GeneratorOutput(
                data=None,
                error=f"Unexpected error: {str(e)}"
            )
