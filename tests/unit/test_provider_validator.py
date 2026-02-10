"""Unit tests for provider validation service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from api.provider_validator import (
    ValidationResult,
    ProviderValidator,
    ValidationCache,
    ProviderValidatorService
)


class MockValidator(ProviderValidator):
    """Mock validator for testing."""

    def __init__(self, should_succeed=True):
        super().__init__("MockProvider")
        self.should_succeed = should_succeed

    async def validate_api_key(self, api_key: str) -> bool:
        """Mock validation."""
        await asyncio.sleep(0.01)  # Simulate API call
        return self.should_succeed and api_key == "valid_key"

    async def fetch_available_models(self, api_key: str) -> list:
        """Mock model fetching."""
        await asyncio.sleep(0.01)  # Simulate API call
        if not self.should_succeed:
            raise Exception("API error")

        return [
            {"id": "model-1", "name": "Model 1"},
            {"id": "model-2", "name": "Model 2"}
        ]


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            status="valid",
            models=[{"id": "test", "name": "Test Model"}]
        )

        assert result.status == "valid"
        assert result.is_valid
        assert len(result.models) == 1
        assert result.error is None

    def test_validation_result_invalid(self):
        """Test invalid validation result."""
        result = ValidationResult(
            status="invalid",
            error="Invalid API key"
        )

        assert result.status == "invalid"
        assert not result.is_valid
        assert result.models is None
        assert result.error == "Invalid API key"

    def test_validation_result_age(self):
        """Test result age calculation."""
        import time
        result = ValidationResult(status="valid", models=[])
        time.sleep(0.1)

        assert result.age_seconds >= 0.1


class TestValidationCache:
    """Tests for ValidationCache."""

    def test_cache_set_and_get(self):
        """Test caching and retrieving results."""
        cache = ValidationCache(default_ttl=3600)
        result = ValidationResult(status="valid", models=[{"id": "test", "name": "Test"}])

        cache.set("test_provider", "test_key", result)
        cached = cache.get("test_provider", "test_key")

        assert cached is not None
        assert cached.status == "valid"
        assert len(cached.models) == 1

    def test_cache_expiration(self):
        """Test cache expiration."""
        import time
        cache = ValidationCache(default_ttl=0.1)  # 100ms TTL
        result = ValidationResult(status="valid", models=[])

        cache.set("test_provider", "test_key", result)

        # Should be cached immediately
        assert cache.get("test_provider", "test_key") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Should be expired
        assert cache.get("test_provider", "test_key") is None

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = ValidationCache()
        result = ValidationResult(status="valid", models=[])

        cache.set("provider1", "key1", result)
        cache.set("provider2", "key2", result)

        # Invalidate specific provider
        cache.invalidate("provider1", "key1")

        assert cache.get("provider1", "key1") is None
        assert cache.get("provider2", "key2") is not None

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = ValidationCache()

        result_valid = ValidationResult(status="valid", models=[])
        result_invalid = ValidationResult(status="invalid", error="Error")

        cache.set("provider1", "key1", result_valid)
        cache.set("provider1", "key2", result_invalid)
        cache.set("provider2", "key3", result_valid)

        stats = cache.get_stats()

        assert stats["total_entries"] == 3
        assert "provider1" in stats["by_provider"]
        assert stats["by_provider"]["provider1"]["count"] == 2
        assert stats["by_provider"]["provider1"]["valid"] == 1
        assert stats["by_provider"]["provider1"]["invalid"] == 1


class TestProviderValidatorService:
    """Tests for ProviderValidatorService."""

    @pytest.mark.asyncio
    async def test_register_and_list_validators(self):
        """Test registering validators."""
        service = ProviderValidatorService()
        validator = MockValidator()

        service.register_validator("mock", validator)

        assert "mock" in service.list_providers()
        assert service.get_validator("mock") is not None

    @pytest.mark.asyncio
    async def test_validate_and_refresh_success(self):
        """Test successful validation and model refresh."""
        service = ProviderValidatorService()
        validator = MockValidator(should_succeed=True)
        service.register_validator("mock", validator)

        result = await service.validate_and_refresh("mock", "valid_key")

        assert result.status == "valid"
        assert result.models is not None
        assert len(result.models) == 2
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_and_refresh_invalid_key(self):
        """Test validation with invalid API key."""
        service = ProviderValidatorService()
        validator = MockValidator(should_succeed=True)
        service.register_validator("mock", validator)

        result = await service.validate_and_refresh("mock", "invalid_key")

        assert result.status == "invalid"
        assert result.models is None
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validate_and_refresh_api_error(self):
        """Test validation with API error."""
        service = ProviderValidatorService()
        validator = MockValidator(should_succeed=False)
        service.register_validator("mock", validator)

        result = await service.validate_and_refresh("mock", "valid_key")

        assert result.status == "error"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validate_and_refresh_unsupported_provider(self):
        """Test validation with unsupported provider."""
        service = ProviderValidatorService()

        result = await service.validate_and_refresh("nonexistent", "key")

        assert result.status == "error"
        assert "Unsupported provider" in result.error

    @pytest.mark.asyncio
    async def test_cache_bypass_with_force(self):
        """Test cache bypass with force=True."""
        service = ProviderValidatorService(cache_ttl=3600)
        validator = MockValidator(should_succeed=True)
        service.register_validator("mock", validator)

        # First call - should cache
        result1 = await service.validate_and_refresh("mock", "valid_key")
        assert result1.status == "valid"

        # Second call without force - should use cache
        result2 = await service.validate_and_refresh("mock", "valid_key", force=False)
        assert result2.timestamp == result1.timestamp  # Same cached result

        # Third call with force - should bypass cache
        result3 = await service.validate_and_refresh("mock", "valid_key", force=True)
        assert result3.timestamp > result1.timestamp  # New result

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test manual cache invalidation."""
        service = ProviderValidatorService()
        validator = MockValidator(should_succeed=True)
        service.register_validator("mock", validator)

        # Cache a result
        result1 = await service.validate_and_refresh("mock", "valid_key")
        assert result1.status == "valid"

        # Invalidate cache
        service.invalidate_cache("mock", "valid_key")

        # Next call should fetch fresh data
        result2 = await service.validate_and_refresh("mock", "valid_key")
        assert result2.timestamp > result1.timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
