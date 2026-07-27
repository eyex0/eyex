import pytest
from unittest.mock import AsyncMock, patch
from packages.cognitive_kernel.ai_gateway.providers.openai import OpenAIProvider

@pytest.mark.asyncio
async def test_openai_generate():
    with patch("openai.AsyncOpenAI") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="test"))]
        )
        provider = OpenAIProvider(api_key="test_key")
        response = await provider.generate(model="gpt-4", prompt="hello")
        assert response == "test"

@pytest.mark.asyncio
async def test_openai_stream():
    with patch("openai.AsyncOpenAI") as mock_client:
        async def mock_stream():
            yield AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="hello "))])
            yield AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="world"))])

        mock_client.return_value.chat.completions.create.return_value = mock_stream()
        provider = OpenAIProvider(api_key="test_key")
        response = ""
        async for chunk in provider.stream(model="gpt-4", prompt="hello"):
            response += chunk
        assert response == "hello world"

@pytest.mark.asyncio
async def test_openai_embed():
    with patch("openai.AsyncOpenAI") as mock_client:
        mock_client.return_value.embeddings.create.return_value = AsyncMock(
            data=[[1.0, 2.0, 3.0]]
        )
        provider = OpenAIProvider(api_key="test_key")
        response = await provider.embed(model="text-embedding-ada-002", texts=["hello"])
        assert response == [[1.0, 2.0, 3.0]]
