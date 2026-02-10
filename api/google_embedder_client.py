"""Google AI Embeddings ModelClient integration."""

import os
import logging
import backoff
from typing import Dict, Any, Optional, List, Sequence

from adalflow.core.model_client import ModelClient
from adalflow.core.types import ModelType, EmbedderOutput

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError("google-genai is required. Install it with 'pip install google-genai'")

log = logging.getLogger(__name__)


class GoogleEmbedderClient(ModelClient):
    __doc__ = r"""A component wrapper for Google AI Embeddings API client.

    This client provides access to Google's embedding models through the new
    google.genai SDK. It supports text embeddings for various tasks including
    semantic similarity, retrieval, and classification.

    Note: This uses the new google-genai package (not google-generativeai).
    The old google.generativeai package is deprecated and no longer maintained.

    Args:
        api_key (Optional[str]): Google AI API key. Defaults to None.
            If not provided, will use the GOOGLE_API_KEY environment variable.
        env_api_key_name (str): Environment variable name for the API key.
            Defaults to "GOOGLE_API_KEY".

    Example:
        ```python
        from api.google_embedder_client import GoogleEmbedderClient
        import adalflow as adal

        # Initialize client
        client = GoogleEmbedderClient()

        # Use with adalflow Embedder
        embedder = adal.Embedder(
            model_client=client,
            model_kwargs={
                "model": "gemini-embedding-001",
                "task_type": "SEMANTIC_SIMILARITY",
                "output_dimensionality": 768  # Optional: reduce dimensions
            }
        )
        ```

    References:
        - New SDK: https://github.com/googleapis/python-genai
        - Google AI Embeddings: https://ai.google.dev/gemini-api/docs/embeddings
        - Available models: gemini-embedding-001 (recommended)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        env_api_key_name: str = "GOOGLE_API_KEY",
    ):
        """Initialize Google AI Embeddings client.

        Args:
            api_key: Google AI API key. If not provided, uses environment variable.
            env_api_key_name: Name of environment variable containing API key.
        """
        super().__init__()
        self._api_key = api_key
        self._env_api_key_name = env_api_key_name
        self.client: Optional[genai.Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Google AI client with API key."""
        api_key = self._api_key or os.getenv(self._env_api_key_name)
        if not api_key:
            raise ValueError(
                f"Environment variable {self._env_api_key_name} must be set"
            )
        self.client = genai.Client(api_key=api_key)

    def parse_embedding_response(self, response) -> EmbedderOutput:
        """Parse Google AI embedding response to EmbedderOutput format.

        Args:
            response: Google AI embedding response from the new google.genai SDK

        Returns:
            EmbedderOutput with parsed embeddings
        """
        try:
            from adalflow.core.types import Embedding

            embedding_data = []

            # New API returns response with .embeddings attribute
            if hasattr(response, 'embeddings'):
                # Response structure: response.embeddings[i].values
                for i, emb_obj in enumerate(response.embeddings):
                    if hasattr(emb_obj, 'values'):
                        embedding_data.append(
                            Embedding(embedding=emb_obj.values, index=i)
                        )
                    else:
                        log.warning(f"Embedding object at index {i} missing 'values' attribute")
            # Fallback: handle dict format for backwards compatibility during transition
            elif isinstance(response, dict):
                if 'embedding' in response:
                    embedding_value = response['embedding']
                    if isinstance(embedding_value, list) and len(embedding_value) > 0:
                        if isinstance(embedding_value[0], (int, float)):
                            # Single embedding
                            embedding_data = [Embedding(embedding=embedding_value, index=0)]
                        else:
                            # Batch embeddings
                            embedding_data = [
                                Embedding(embedding=emb_list, index=i)
                                for i, emb_list in enumerate(embedding_value)
                            ]
                elif 'embeddings' in response:
                    # Batch format
                    embedding_data = [
                        Embedding(embedding=item.get('embedding', item.get('values', [])), index=i)
                        for i, item in enumerate(response['embeddings'])
                    ]
            else:
                log.warning(f"Unexpected response type: {type(response)}")
                embedding_data = []

            if not embedding_data:
                log.warning("No embeddings found in response")

            return EmbedderOutput(
                data=embedding_data,
                error=None,
                raw_response=response
            )
        except Exception as e:
            log.error(f"Error parsing Google AI embedding response: {e}")
            return EmbedderOutput(
                data=[],
                error=str(e),
                raw_response=response
            )

    def convert_inputs_to_api_kwargs(
        self,
        input: Optional[Any] = None,
        model_kwargs: Dict = {},
        model_type: ModelType = ModelType.UNDEFINED,
    ) -> Dict:
        """Convert inputs to Google AI API format.

        Args:
            input: Text input(s) to embed
            model_kwargs: Model parameters including model name and task_type
            model_type: Should be ModelType.EMBEDDER for this client

        Returns:
            Dict: API kwargs for Google AI embedding call
        """
        if model_type != ModelType.EMBEDDER:
            raise ValueError(f"GoogleEmbedderClient only supports EMBEDDER model type, got {model_type}")

        # Ensure input is a list
        if isinstance(input, str):
            contents = [input]
        elif isinstance(input, Sequence):
            contents = list(input)
        else:
            raise TypeError("input must be a string or sequence of strings")

        # Extract model and config parameters
        # Note: New SDK uses model names without 'models/' prefix
        # Default to gemini-embedding-001 (the current embedding model)
        model = model_kwargs.get("model", "gemini-embedding-001")

        # Build config object for embedding parameters
        config_params = {}
        if "task_type" in model_kwargs:
            config_params["task_type"] = model_kwargs["task_type"]
        else:
            config_params["task_type"] = "SEMANTIC_SIMILARITY"

        if "output_dimensionality" in model_kwargs:
            config_params["output_dimensionality"] = model_kwargs["output_dimensionality"]

        # Build final API kwargs
        final_model_kwargs = {
            "model": model,
            "contents": contents,
        }

        # Add config if we have parameters
        if config_params:
            final_model_kwargs["config"] = types.EmbedContentConfig(**config_params)

        return final_model_kwargs

    @backoff.on_exception(
        backoff.expo,
        (Exception,),  # Google AI may raise various exceptions
        max_time=5,
    )
    def call(self, api_kwargs: Dict = {}, model_type: ModelType = ModelType.UNDEFINED):
        """Call Google AI embedding API.

        Args:
            api_kwargs: API parameters
            model_type: Should be ModelType.EMBEDDER

        Returns:
            Google AI embedding response
        """
        if model_type != ModelType.EMBEDDER:
            raise ValueError(f"GoogleEmbedderClient only supports EMBEDDER model type")

        if not self.client:
            raise RuntimeError("Client not initialized. Call _initialize_client() first.")

        log.info(f"Google AI Embeddings API kwargs: {api_kwargs}")

        try:
            # Use the new client-based API
            response = self.client.models.embed_content(**api_kwargs)
            return response

        except Exception as e:
            log.error(f"Error calling Google AI Embeddings API: {e}")
            raise

    async def acall(self, api_kwargs: Dict = {}, model_type: ModelType = ModelType.UNDEFINED):
        """Async call to Google AI embedding API.
        
        Note: Google AI Python client doesn't have async support yet,
        so this falls back to synchronous call.
        """
        # Google AI client doesn't have async support yet
        return self.call(api_kwargs, model_type)