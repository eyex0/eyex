"""Tests for the AIGateway."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from packages.cognitive_kernel.ai_gateway.main import AIGateway
from packages.cognitive_kernel.ai_gateway.providers.base import GenerateRequest, GenerateResponse


class TestAIGateway:
    def test_register_provider(self):
        gateway = AIGateway()
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        gateway.register_provider("test", mock_provider)
        assert "test" in gateway.list_providers()

    def test_get_provider(self):
        gateway = AIGateway()
        mock_provider = MagicMock()
        gateway.register_provider("test", mock_provider)
        assert gateway.get_provider("test") == mock_provider

    def test_get_provider_not_found(self):
        gateway = AIGateway()
        with pytest.raises(ValueError):
            gateway.get_provider("nonexistent")

    def test_build_provider_chain(self):
        gateway = AIGateway()
        chain = gateway._build_provider_chain("openai", ["anthropic"])
        assert "openai" in chain
        assert "anthropic" in chain
        assert chain[0] == "openai"

    def test_build_provider_chain_no_primary(self):
        gateway = AIGateway()
        chain = gateway._build_provider_chain(None, None)
        assert len(chain) > 0

    def test_cache_key_consistency(self):
        gateway = AIGateway()
        req = GenerateRequest(prompt="test")
        key1 = gateway._cache_key(req)
        key2 = gateway._cache_key(req)
        assert key1 == key2

    def test_cache_key_different_prompts(self):
        gateway = AIGateway()
        req1 = GenerateRequest(prompt="test1")
        req2 = GenerateRequest(prompt="test2")
        assert gateway._cache_key(req1) != gateway._cache_key(req2)
