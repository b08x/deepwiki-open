"""Mistral AI API validator for API key validation and model discovery."""

import asyncio
import logging
from typing import Dict, List

import httpx

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)


class MistralValidator(ProviderValidator):
    """Validator for Mistral AI API.

    Mistral AI provides state-of-the-art open and commercial LLM models.
    API Documentation: https://docs.mistral.ai/api
    """

    BASE_URL = "https://api.mistral.ai/v1"

    def __init__(self):
        """Initialize Mistral AI validator."""
        super().__init__("Mistral AI")

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Mistral AI API key by listing models.

        Args:
            api_key: Mistral AI API key

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=headers
                )

                if response.status_code == 401:
                    logger.warning("Mistral AI API key is invalid (401)")
                    return False
                elif response.status_code == 403:
                    logger.warning("Mistral AI API key is forbidden (403)")
                    return False
                elif response.status_code != 200:
                    logger.error(f"Mistral AI API returned status {response.status_code}")
                    return False

                return True

        except httpx.TimeoutException:
            logger.error("Mistral AI API request timed out")
            return False
        except Exception as e:
            logger.error(f"Mistral AI validation error: {str(e)}")
            return False

    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch available models from Mistral AI API.

        Args:
            api_key: Valid Mistral AI API key

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            Exception: If fetching models fails
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/models",
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            models_data = data.get("data", [])

            # Transform Mistral model format to our format
            models = []
            for model in models_data:
                model_id = model.get("id", "")
                model_name = model.get("name", model_id)

                # Include capabilities and context window
                capabilities = model.get("capabilities", {})
                max_context_length = model.get("max_context_length", 0)

                display_name = model_name
                if max_context_length:
                    display_name = f"{model_name} ({max_context_length:,} tokens)"

                models.append({
                    "id": model_id,
                    "name": display_name,
                    "context_length": max_context_length,
                    "capabilities": capabilities
                })

            logger.info(f"Fetched {len(models)} models from Mistral AI")
            return models


# Synchronous wrapper for backwards compatibility
def validate_mistral_key(api_key: str) -> bool:
    """Synchronous wrapper for Mistral AI API key validation.

    Args:
        api_key: Mistral AI API key

    Returns:
        True if valid, False otherwise
    """
    validator = MistralValidator()
    return asyncio.run(validator.validate_api_key(api_key))
