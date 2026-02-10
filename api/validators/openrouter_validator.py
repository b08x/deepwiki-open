"""OpenRouter API validator for API key validation and model discovery."""

import asyncio
from typing import Dict, List

import logging

import httpx

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)


class OpenRouterValidator(ProviderValidator):
    """Validator for OpenRouter API.

    OpenRouter provides access to multiple LLM providers through a unified API.
    API Documentation: https://openrouter.ai/docs
    """

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self):
        """Initialize OpenRouter validator."""
        super().__init__("OpenRouter")

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate OpenRouter API key by fetching models.

        Args:
            api_key: OpenRouter API key (format: sk-or-v1-...)

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/deepwiki-open",
                "X-Title": "DeepWiki-Open"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=headers
                )

                if response.status_code == 401:
                    logger.warning("OpenRouter API key is invalid (401)")
                    return False
                elif response.status_code == 403:
                    logger.warning("OpenRouter API key is forbidden (403)")
                    return False
                elif response.status_code != 200:
                    logger.error(f"OpenRouter API returned status {response.status_code}")
                    return False

                return True

        except httpx.TimeoutException:
            logger.error("OpenRouter API request timed out")
            return False
        except Exception as e:
            logger.error(f"OpenRouter validation error: {str(e)}")
            return False

    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch available models from OpenRouter API.

        Args:
            api_key: Valid OpenRouter API key

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            Exception: If fetching models fails
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/deepwiki-open",
            "X-Title": "DeepWiki-Open"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/models",
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            models_data = data.get("data", [])

            # Transform OpenRouter model format to our format
            models = []
            for model in models_data:
                model_id = model.get("id", "")
                model_name = model.get("name", model_id)

                # Include context length and pricing info for display
                context_length = model.get("context_length", 0)
                pricing = model.get("pricing", {})

                models.append({
                    "id": model_id,
                    "name": f"{model_name} ({context_length:,} tokens)" if context_length else model_name,
                    "context_length": context_length,
                    "pricing": pricing
                })

            logger.info(f"Fetched {len(models)} models from OpenRouter")
            return models


# Synchronous wrapper for backwards compatibility
def validate_openrouter_key(api_key: str) -> bool:
    """Synchronous wrapper for OpenRouter validation.

    Args:
        api_key: OpenRouter API key

    Returns:
        True if valid, False otherwise
    """
    validator = OpenRouterValidator()
    return asyncio.run(validator.validate_api_key(api_key))
