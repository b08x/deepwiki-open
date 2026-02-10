"""HuggingFace API validator for API key validation and model discovery."""

import asyncio
import logging
from typing import Dict, List

import httpx

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)


class HuggingFaceValidator(ProviderValidator):
    """Validator for HuggingFace Inference API.

    HuggingFace provides access to thousands of open-source models.
    API Documentation: https://huggingface.co/docs/api-inference
    """

    BASE_URL = "https://api-inference.huggingface.co"
    MODELS_URL = "https://huggingface.co/api/models"

    def __init__(self):
        """Initialize HuggingFace validator."""
        super().__init__("HuggingFace")

    async def validate_api_key(self, api_key: str) -> bool:
        """Validate HuggingFace API key by making a test request.

        Args:
            api_key: HuggingFace API token (format: hf_...)

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}"
            }

            # Try to access user's model list or whoami endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://huggingface.co/api/whoami",
                    headers=headers
                )

                if response.status_code == 401:
                    logger.warning("HuggingFace API key is invalid (401)")
                    return False
                elif response.status_code == 403:
                    logger.warning("HuggingFace API key is forbidden (403)")
                    return False
                elif response.status_code != 200:
                    logger.error(f"HuggingFace API returned status {response.status_code}")
                    return False

                return True

        except httpx.TimeoutException:
            logger.error("HuggingFace API request timed out")
            return False
        except Exception as e:
            logger.error(f"HuggingFace validation error: {str(e)}")
            return False

    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch popular text-generation models from HuggingFace.

        Note: HuggingFace has thousands of models. This returns a curated list
        of popular text-generation models that work well with Inference API.

        Args:
            api_key: Valid HuggingFace API token

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            Exception: If fetching models fails
        """
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        # Query for popular text-generation models
        params = {
            "pipeline_tag": "text-generation",
            "sort": "downloads",
            "direction": -1,
            "limit": 50
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                self.MODELS_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()

            models_data = response.json()

            # Transform HuggingFace model format to our format
            models = []
            for model in models_data:
                model_id = model.get("id", "")
                model_name = model.get("modelId", model_id)

                # Get model card info
                downloads = model.get("downloads", 0)
                likes = model.get("likes", 0)

                # Include download and like counts for popular models
                display_name = f"{model_name} (↓{self._format_number(downloads)} ♥{likes})"

                models.append({
                    "id": model_id,
                    "name": display_name,
                    "downloads": downloads,
                    "likes": likes,
                    "tags": model.get("tags", [])
                })

            logger.info(f"Fetched {len(models)} models from HuggingFace")
            return models

    def _format_number(self, num: int) -> str:
        """Format large numbers in human-readable form.

        Args:
            num: Number to format

        Returns:
            Formatted string (e.g., "1.2M", "500K")
        """
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.0f}K"
        else:
            return str(num)


# Synchronous wrapper for backwards compatibility
def validate_huggingface_key(api_key: str) -> bool:
    """Synchronous wrapper for HuggingFace API key validation.

    Args:
        api_key: HuggingFace API token

    Returns:
        True if valid, False otherwise
    """
    validator = HuggingFaceValidator()
    return asyncio.run(validator.validate_api_key(api_key))
