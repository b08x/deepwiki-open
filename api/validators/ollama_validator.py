"""Ollama API validator for model discovery.

Ollama is a local LLM runner that doesn't require API keys.
This validator checks if Ollama is running and fetches available models.
"""

import logging
import os
from typing import Dict, List

import httpx

from api.provider_validator import ProviderValidator

logger = logging.getLogger(__name__)


class OllamaValidator(ProviderValidator):
    """Validator for Ollama local instance.

    Ollama runs locally and doesn't require API keys.
    This validator checks if Ollama is running and fetches installed models.

    API Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    def __init__(self, ollama_host: str = None):
        """Initialize Ollama validator.

        Args:
            ollama_host: Ollama host URL. Defaults to OLLAMA_HOST env var or http://localhost:11434
        """
        super().__init__("Ollama")
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Remove /api prefix if present (we'll add it back in API calls)
        if self.ollama_host.endswith('/api'):
            self.ollama_host = self.ollama_host[:-4]

    async def validate_api_key(self, api_key: str = "") -> bool:
        """Validate Ollama is running by checking /api/tags endpoint.

        Ollama doesn't use API keys, so this just checks if Ollama is accessible.

        Args:
            api_key: Ignored for Ollama (no API key needed)

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_host}/api/tags")

                if response.status_code == 200:
                    logger.info(f"Ollama is running at {self.ollama_host}")
                    return True
                else:
                    logger.warning(f"Ollama returned status {response.status_code}")
                    return False

        except httpx.ConnectError:
            logger.warning(f"Could not connect to Ollama at {self.ollama_host}")
            return False
        except httpx.TimeoutException:
            logger.warning(f"Ollama request timed out at {self.ollama_host}")
            return False
        except Exception as e:
            logger.error(f"Ollama validation error: {str(e)}")
            return False

    async def fetch_available_models(self, api_key: str = "") -> List[Dict]:
        """Fetch installed models from Ollama.

        Args:
            api_key: Ignored for Ollama (no API key needed)

        Returns:
            List of model dictionaries with 'id' and 'name' keys

        Raises:
            Exception: If fetching models fails
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.ollama_host}/api/tags")
            response.raise_for_status()

            data = response.json()
            models_data = data.get("models", [])

            # Transform Ollama model format to our format
            models = []
            for model in models_data:
                model_name = model.get("name", "")
                model_base_name = model_name.split(":")[0]  # Remove tag if present

                # Get model size and modified date
                size = model.get("size", 0)
                modified = model.get("modified_at", "")

                # Format size in human-readable form
                size_gb = size / (1024 ** 3) if size else 0

                display_name = f"{model_name} ({size_gb:.1f} GB)" if size_gb else model_name

                models.append({
                    "id": model_name,
                    "name": display_name,
                    "size_bytes": size,
                    "modified_at": modified,
                    "base_name": model_base_name
                })

            logger.info(f"Fetched {len(models)} models from Ollama")
            return models


# Synchronous wrapper for backwards compatibility
def check_ollama_available(ollama_host: str = None) -> bool:
    """Check if Ollama is running and accessible.

    Args:
        ollama_host: Ollama host URL

    Returns:
        True if Ollama is accessible, False otherwise
    """
    import asyncio
    validator = OllamaValidator(ollama_host)
    return asyncio.run(validator.validate_api_key(""))
