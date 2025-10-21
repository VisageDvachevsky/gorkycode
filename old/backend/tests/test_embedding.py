import pytest
from app.services.embedding import EmbeddingService


@pytest.fixture
def embedding_service():
    return EmbeddingService()


def test_generate_embedding(embedding_service):
    text = "street-art panoramas coffee history"
    embedding = embedding_service.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)


def test_cosine_similarity(embedding_service):
    vec1 = embedding_service.generate_embedding("museum history art")
    vec2 = embedding_service.generate_embedding("museum history culture")
    vec3 = embedding_service.generate_embedding("coffee street food")
    
    similarity_close = EmbeddingService.cosine_similarity(vec1, vec2)
    similarity_far = EmbeddingService.cosine_similarity(vec1, vec3)
    
    assert 0 <= similarity_close <= 1
    assert 0 <= similarity_far <= 1
    assert similarity_close > similarity_far


@pytest.mark.asyncio
async def test_caching(embedding_service):
    text = "test caching functionality"
    
    await embedding_service.connect_redis()
    
    embedding1, from_cache1 = await embedding_service.get_embedding(text)
    embedding2, from_cache2 = await embedding_service.get_embedding(text)
    
    assert not from_cache1
    assert from_cache2
    assert embedding1 == embedding2