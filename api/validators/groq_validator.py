"""Groq API validator for API key validation and model discovery."""

import asyncio
import logging
from typing import Dict, List

import httpx

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)


class GroqValidator(ProviderValidator):
    """Validator for Groq API.

    Groq provides ultra-fast LLM inference using their LPU technology.
    API Documentation: https://console.groq.com/docs
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self):
        """Initialize Groq validator."""
        super().__init__("Groq")

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Groq API key by listing models.

        Args:
            api_key: Groq API key (format: gsk_...)

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
                    logger.warning("Groq API key is invalid (401)")
                    return False
                elif response.status_code == 403:
                    logger.warning("Groq API key is forbidden (403)")
                    return False
                elif response.status_code != 200:
                    logger.error(f"Groq API returned status {response.status_code}")
                    return False

                return True

        except httpx.TimeoutException:
            logger.error("Groq API request timed out")
            return False
        except Exception as e:
            logger.error(f"Groq validation error: {str(e)}")
            return False

    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch available models from Groq API.

        Args:
            api_key: Valid Groq API key

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

            # Transform Groq model format (OpenAI-compatible) to our format
            models = []
            for model in models_data:
                model_id = model.get("id", "")

                # Groq returns models in OpenAI format
                # Extract context window if available
                context_window = model.get("context_window", 0)

                display_name = model_id
                if context_window:
                    display_name = f"{model_id} ({context_window:,} tokens)"

                models.append({
                    "id": model_id,
                    "name": display_name,
                    "context_window": context_window,
                    "owned_by": model.get("owned_by", "")
                })

            logger.info(f"Fetched {len(models)} models from Groq")
            return models


# Synchronous wrapper for backwards compatibility
def validate_groq_key(api_key: str) -> bool:
    """Synchronous wrapper for Groq API key validation.

    Args:
        api_key: Groq API key

    Returns:
        True if valid, False otherwise
    """
    validator = GroqValidator()
    return asyncio.run(validator.validate_api_key(api_key))
