"""Provider API Key Validation and Model Discovery Service.

This module provides a unified framework for:
- Validating API keys for various LLM providers
- Fetching available models dynamically from provider APIs
- Caching validation results with configurable TTL (6-12 hours)
- Orchestrating validation across multiple providers

Architecture:
    ProviderValidator (ABC) - Base interface for provider-specific validators
    ValidationCache - In-memory TTL cache for validation results
    ProviderValidatorService - Main service orchestrating all validators
"""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Literal, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of API key validation and model discovery.

    Attributes:
        status: Validation status ('valid', 'invalid', 'error')
        models: List of available models if validation succeeded
        error: Error message if validation failed
        timestamp: Unix timestamp when validation was performed
    """
    status: Literal["valid", "invalid", "error"]
    models: Optional[List[Dict]] = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        """Check if validation succeeded."""
        return self.status == "valid"

    @property
    def age_seconds(self) -> float:
        """Get age of this result in seconds."""
        return time.time() - self.timestamp


class ProviderValidator(ABC):
    """Abstract base class for provider-specific validators.

    Each provider (OpenRouter, Google, Mistral, etc.) implements this interface
    to provide API key validation and model discovery logic.
    """

    def __init__(self, provider_name: str):
        """Initialize validator for a specific provider.

        Args:
            provider_name: Human-readable provider name (e.g., "OpenRouter")
        """
        self.provider_name = provider_name

    @abstractmethod
    async def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key by making a lightweight API call.

        Args:
            api_key: The API key to validate

        Returns:
            True if API key is valid, False otherwise

        Raises:
            Exception: If validation request fails unexpectedly
        """
        pass

    @abstractmethod
    async def fetch_available_models(self, api_key: str) -> List[Dict]:
        """Fetch list of available models from provider API.

        Args:
            api_key: Valid API key for the provider

        Returns:
            List of model dictionaries with 'id' and 'name' keys
            Example: [{'id': 'gpt-4', 'name': 'GPT-4'}, ...]

        Raises:
            Exception: If fetching models fails
        """
        pass

    async def validate_and_fetch(self, api_key: str) -> ValidationResult:
        """Validate API key and fetch models in one operation.

        This is the main entry point for validation. It:
        1. Validates the API key
        2. If valid, fetches available models
        3. Returns a ValidationResult with status and data

        Args:
            api_key: The API key to validate

        Returns:
            ValidationResult with status, models, and any errors
        """
        try:
            logger.info(f"Validating API key for {self.provider_name}")

            # Validate API key
            is_valid = await self.validate_api_key(api_key)
            if not is_valid:
                return ValidationResult(
                    status="invalid",
                    error=f"Invalid API key for {self.provider_name}"
                )

            # Fetch available models
            logger.info(f"Fetching available models for {self.provider_name}")
            models = await self.fetch_available_models(api_key)

            if not models:
                return ValidationResult(
                    status="error",
                    error=f"No models available for {self.provider_name}"
                )

            logger.info(f"Successfully validated {self.provider_name} - {len(models)} models available")
            return ValidationResult(
                status="valid",
                models=models
            )

        except Exception as e:
            logger.error(f"Validation failed for {self.provider_name}: {str(e)}")
            return ValidationResult(
                status="error",
                error=f"Validation error: {str(e)}"
            )


class ValidationCache:
    """In-memory cache for validation results with TTL support.

    Caches validation results to avoid excessive API calls to provider services.
    Each cached entry has a configurable TTL (default 8 hours).

    Cache keys are generated from provider name and API key hash.
    """

    def __init__(self, default_ttl: int = 28800):
        """Initialize validation cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 8 hours)
        """
        self._cache: Dict[str, ValidationResult] = {}
        self._default_ttl = default_ttl
        logger.info(f"ValidationCache initialized with TTL={default_ttl}s ({default_ttl/3600:.1f}h)")

    def _make_cache_key(self, provider: str, api_key: str) -> str:
        """Generate cache key from provider and API key.

        Args:
            provider: Provider identifier (e.g., "openrouter")
            api_key: API key to hash

        Returns:
            Cache key in format: provider_hash
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12]
        return f"{provider}_{key_hash}"

    def get(self, provider: str, api_key: str) -> Optional[ValidationResult]:
        """Get cached validation result if not expired.

        Args:
            provider: Provider identifier
            api_key: API key to look up

        Returns:
            Cached ValidationResult if found and not expired, None otherwise
        """
        cache_key = self._make_cache_key(provider, api_key)
        result = self._cache.get(cache_key)

        if result is None:
            logger.debug(f"Cache miss for {provider}")
            return None

        # Check if result is expired
        if result.age_seconds > self._default_ttl:
            logger.debug(f"Cache expired for {provider} (age: {result.age_seconds:.0f}s)")
            self._cache.pop(cache_key, None)
            return None

        logger.debug(f"Cache hit for {provider} (age: {result.age_seconds:.0f}s)")
        return result

    def set(self, provider: str, api_key: str, result: ValidationResult, ttl: Optional[int] = None):
        """Store validation result in cache.

        Args:
            provider: Provider identifier
            api_key: API key used for validation
            result: ValidationResult to cache
            ttl: Optional custom TTL in seconds (uses default if not provided)
        """
        cache_key = self._make_cache_key(provider, api_key)
        self._cache[cache_key] = result

        ttl_used = ttl or self._default_ttl
        logger.info(
            f"Cached validation result for {provider} "
            f"(status={result.status}, ttl={ttl_used}s, models={len(result.models or [])})"
        )

    def invalidate(self, provider: str, api_key: Optional[str] = None):
        """Invalidate cache entries for a provider.

        Args:
            provider: Provider identifier
            api_key: Optional specific API key to invalidate.
                    If not provided, invalidates all entries for provider.
        """
        if api_key:
            cache_key = self._make_cache_key(provider, api_key)
            if self._cache.pop(cache_key, None):
                logger.info(f"Invalidated cache for {provider}")
        else:
            # Invalidate all entries for provider
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{provider}_")]
            for key in keys_to_remove:
                self._cache.pop(key)
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for {provider}")

    def clear(self):
        """Clear all cached validation results."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cache entries")

    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and entries by provider
        """
        stats = {
            "total_entries": len(self._cache),
            "by_provider": {}
        }

        for key, result in self._cache.items():
            provider = key.split("_")[0]
            if provider not in stats["by_provider"]:
                stats["by_provider"][provider] = {
                    "count": 0,
                    "valid": 0,
                    "invalid": 0,
                    "error": 0
                }
            stats["by_provider"][provider]["count"] += 1
            stats["by_provider"][provider][result.status] += 1

        return stats


class ProviderValidatorService:
    """Main service for orchestrating provider validation.

    This service:
    - Registers provider-specific validators
    - Manages validation cache
    - Coordinates validation and model refresh across providers
    """

    def __init__(self, cache_ttl: int = 28800):
        """Initialize validator service.

        Args:
            cache_ttl: Cache time-to-live in seconds (default: 8 hours)
        """
        self._validators: Dict[str, ProviderValidator] = {}
        self._cache = ValidationCache(default_ttl=cache_ttl)
        logger.info(f"ProviderValidatorService initialized with cache_ttl={cache_ttl}s")

    def register_validator(self, provider_id: str, validator: ProviderValidator):
        """Register a provider-specific validator.

        Args:
            provider_id: Provider identifier (e.g., "openrouter", "google")
            validator: ProviderValidator instance for this provider
        """
        self._validators[provider_id] = validator
        logger.info(f"Registered validator for provider: {provider_id}")

    def get_validator(self, provider_id: str) -> Optional[ProviderValidator]:
        """Get validator for a specific provider.

        Args:
            provider_id: Provider identifier

        Returns:
            ProviderValidator instance if registered, None otherwise
        """
        return self._validators.get(provider_id)

    async def validate_and_refresh(
        self,
        provider: str,
        api_key: str,
        force: bool = False
    ) -> ValidationResult:
        """Validate API key and refresh model list for a provider.

        This is the main entry point for validation. It:
        1. Checks cache if force=False
        2. If not cached or force=True, validates API key and fetches models
        3. Caches the result
        4. Returns ValidationResult

        Args:
            provider: Provider identifier (e.g., "openrouter")
            api_key: API key to validate
            force: If True, bypass cache and fetch fresh data

        Returns:
            ValidationResult with status, models, and any errors

        Raises:
            ValueError: If provider is not supported
        """
        # Check if provider is supported
        validator = self.get_validator(provider)
        if not validator:
            error_msg = f"Unsupported provider: {provider}. Available: {list(self._validators.keys())}"
            logger.error(error_msg)
            return ValidationResult(
                status="error",
                error=error_msg
            )

        # Check cache if not forcing refresh
        if not force:
            cached_result = self._cache.get(provider, api_key)
            if cached_result:
                logger.info(f"Using cached result for {provider}")
                return cached_result

        # Validate and fetch models
        logger.info(f"{'Force ' if force else ''}validating {provider}")
        result = await validator.validate_and_fetch(api_key)

        # Cache the result (even if invalid/error, to avoid repeated failed attempts)
        self._cache.set(provider, api_key, result)

        return result

    def invalidate_cache(self, provider: str, api_key: Optional[str] = None):
        """Invalidate cache for a provider.

        Args:
            provider: Provider identifier
            api_key: Optional specific API key to invalidate
        """
        self._cache.invalidate(provider, api_key)

    def clear_cache(self):
        """Clear all cached validation results."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return self._cache.get_stats()

    def list_providers(self) -> List[str]:
        """Get list of registered provider IDs.

        Returns:
            List of provider identifiers
        """
        return list(self._validators.keys())
