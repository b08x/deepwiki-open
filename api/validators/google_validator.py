"""Google GenAI API validator for API key validation and model discovery.

Uses the new google-genai SDK (NOT the deprecated google.generativeai).
"""

import asyncio
import logging
from typing import Dict, List

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError("google-genai is required. Install it with 'pip install google-genai'")


class GoogleValidator(ProviderValidator):
    """Validator for Google GenAI API.

    Uses the new google-genai package to validate API keys and fetch available models.
    API Documentation: https://ai.google.dev/gemini-api/docs

    Note: This uses the NEW google-genai package, NOT the deprecated google.generativeai.
    """

    def __init__(self):
        """Initialize Google GenAI validator."""
        super().__init__("Google GenAI")

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate Google GenAI API key by listing models.

        Args:
            api_key: Google AI API key

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            client = genai.Client(api_key=api_key)

            # Try to list models - this will fail if API key is invalid
            # Use asyncio.to_thread since genai SDK is synchronous
            models = await asyncio.to_thread(self._list_models_sync, client)

            if not models:
                logger.warning("Google API key valid but no models available")
                return False

            logger.info(f"Google API key validated - {len(models)} models available")
            return True

        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "unauthorized" in error_msg or "forbidden" in error_msg:
                logger.warning(f"Google API key is invalid: {str(e)}")
                return False
            else:
                logger.error(f"Google validation error: {str(e)}")
                raise

    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch available models from Google GenAI API.

        Args:
            api_key: Valid Google AI API key

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            Exception: If fetching models fails
        """
        client = genai.Client(api_key=api_key)

        # Use asyncio.to_thread since genai SDK is synchronous
        all_models = await asyncio.to_thread(self._list_models_sync, client)

        # Filter models that support content generation
        # (embedding-only models are filtered out)
        models = []
        for model in all_models:
            model_id = model.name
            display_name = getattr(model, 'display_name', None) or model_id

            # Skip embedding-only models (they have "embedding" in the name)
            if 'embedding' in model_id.lower():
                logger.debug(f"Skipping embedding model: {model_id}")
                continue

            # Check if model supports generation methods
            supported_methods = getattr(model, 'supported_generation_methods', None)

            # Include model if:
            # 1. It has generateContent in supported methods, OR
            # 2. It doesn't have supported_methods attribute (assume it's a generation model), OR
            # 3. It's a known generation model (gemini, gemma, etc.)
            is_generation_model = (
                (supported_methods and 'generateContent' in supported_methods) or
                (supported_methods is None) or
                any(prefix in model_id.lower() for prefix in ['gemini', 'gemma', 'palm'])
            )

            if is_generation_model:
                models.append({
                    "id": model_id,
                    "name": display_name,
                    "description": getattr(model, 'description', ''),
                    "input_token_limit": getattr(model, 'input_token_limit', 0),
                    "output_token_limit": getattr(model, 'output_token_limit', 0)
                })

        logger.info(f"Fetched {len(models)} content generation models from Google GenAI (total: {len(all_models)})")
        return models

    def _list_models_sync(self, client: genai.Client) -> List:
        """Synchronous helper to list models.

        Args:
            client: Initialized Google GenAI client

        Returns:
            List of model objects
        """
        try:
            # List all models
            models_list = list(client.models.list())
            logger.info(f"Google API returned {len(models_list)} total models")

            # Debug: log first model attributes to understand structure
            if models_list:
                first_model = models_list[0]
                logger.debug(f"Sample model structure: name={first_model.name}, "
                           f"attributes={dir(first_model)}")

            return models_list
        except Exception as e:
            logger.error(f"Failed to list Google models: {str(e)}")
            raise


# Synchronous wrapper for backwards compatibility
def validate_google_key(api_key: str) -> bool:
    """Synchronous wrapper for Google API key validation.

    Args:
        api_key: Google AI API key

    Returns:
        True if valid, False otherwise
    """
    validator = GoogleValidator()
    return asyncio.run(validator.validate_api_key(api_key))
