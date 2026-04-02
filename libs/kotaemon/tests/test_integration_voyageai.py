"""Integration tests for VoyageAI embeddings and rerankers using real API calls.

These tests require a valid VOYAGE_API_KEY environment variable.
Run with: pytest tests/test_integration_voyageai.py -v

To skip these tests (e.g., in CI without API key), use:
    pytest tests/test_integration_voyageai.py -v -k "not integration"
"""

import os

import pytest

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import VoyageAIEmbeddings
from kotaemon.rerankings import VoyageAIReranking

# Skip all tests in this module if VOYAGE_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("VOYAGE_API_KEY"),
    reason="VOYAGE_API_KEY environment variable not set",
)


def get_api_key():
    """Get the VoyageAI API key from environment."""
    return os.environ.get("VOYAGE_API_KEY")


class TestVoyage4Integration:
    """Integration tests for voyage-4 model family."""

    def test_voyage_4_embedding(self):
        """Test voyage-4 model generates valid embeddings."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")
        output = model("The quick brown fox jumps over the lazy dog.")

        assert isinstance(output, list)
        assert len(output) == 1
        assert isinstance(output[0], DocumentWithEmbedding)
        assert isinstance(output[0].embedding, list)
        assert len(output[0].embedding) == 1024  # Default dimensions
        assert all(isinstance(x, float) for x in output[0].embedding)

    def test_voyage_4_lite_embedding(self):
        """Test voyage-4-lite model generates valid embeddings."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4-lite")
        output = model("The quick brown fox jumps over the lazy dog.")

        assert isinstance(output, list)
        assert len(output) == 1
        assert isinstance(output[0], DocumentWithEmbedding)
        assert isinstance(output[0].embedding, list)
        assert len(output[0].embedding) == 1024  # Default dimensions
        assert all(isinstance(x, float) for x in output[0].embedding)

    def test_voyage_4_large_embedding(self):
        """Test voyage-4-large model generates valid embeddings."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4-large")
        output = model("The quick brown fox jumps over the lazy dog.")

        assert isinstance(output, list)
        assert len(output) == 1
        assert isinstance(output[0], DocumentWithEmbedding)
        assert isinstance(output[0].embedding, list)
        assert len(output[0].embedding) == 1024  # Default dimensions
        assert all(isinstance(x, float) for x in output[0].embedding)

    def test_voyage_4_batch_embedding(self):
        """Test voyage-4 model with batch input."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")
        texts = [
            "First document for embedding.",
            "Second document for embedding.",
            "Third document for embedding.",
        ]
        output = model(texts)

        assert isinstance(output, list)
        assert len(output) == 3
        for doc in output:
            assert isinstance(doc, DocumentWithEmbedding)
            assert len(doc.embedding) == 1024

    def test_voyage_4_lite_batch_embedding(self):
        """Test voyage-4-lite model with batch input."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4-lite")
        texts = [
            "First document for embedding.",
            "Second document for embedding.",
        ]
        output = model(texts)

        assert isinstance(output, list)
        assert len(output) == 2
        for doc in output:
            assert isinstance(doc, DocumentWithEmbedding)
            assert len(doc.embedding) == 1024

    def test_voyage_4_large_batch_embedding(self):
        """Test voyage-4-large model with batch input."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4-large")
        texts = [
            "First document for embedding.",
            "Second document for embedding.",
        ]
        output = model(texts)

        assert isinstance(output, list)
        assert len(output) == 2
        for doc in output:
            assert isinstance(doc, DocumentWithEmbedding)
            assert len(doc.embedding) == 1024

    def test_voyage_4_multilingual(self):
        """Test voyage-4 model with multilingual text."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")
        texts = [
            "Hello, world!",  # English
            "Bonjour le monde!",  # French
            "Hola mundo!",  # Spanish
            "Hallo Welt!",  # German
        ]
        output = model(texts)

        assert isinstance(output, list)
        assert len(output) == 4
        for doc in output:
            assert isinstance(doc, DocumentWithEmbedding)
            assert len(doc.embedding) == 1024

    def test_voyage_4_embedding_similarity(self):
        """Test that similar texts produce similar embeddings."""
        import math

        def cosine_similarity(v1, v2):
            dot_product = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            return dot_product / (norm1 * norm2)

        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")

        # Similar texts
        text1 = "The cat sat on the mat."
        text2 = "A cat was sitting on a mat."
        # Different text
        text3 = "Python is a programming language."

        output = model([text1, text2, text3])

        emb1, emb2, emb3 = (
            output[0].embedding,
            output[1].embedding,
            output[2].embedding,
        )

        sim_1_2 = cosine_similarity(emb1, emb2)
        sim_1_3 = cosine_similarity(emb1, emb3)

        # Similar texts should have higher similarity than different texts
        assert (
            sim_1_2 > sim_1_3
        ), f"Similar texts should have higher similarity: {sim_1_2} vs {sim_1_3}"


class TestVoyage4ModelComparison:
    """Test consistency across voyage-4 family models."""

    def test_all_models_same_dimensions(self):
        """Verify all voyage-4 models return same default dimensions."""
        api_key = get_api_key()
        text = "Test text for dimension comparison."

        models = ["voyage-4", "voyage-4-lite", "voyage-4-large"]
        dimensions = []

        for model_name in models:
            model = VoyageAIEmbeddings(api_key=api_key, model=model_name)
            output = model(text)
            dimensions.append(len(output[0].embedding))

        # All should have 1024 dimensions by default
        assert all(
            d == 1024 for d in dimensions
        ), f"All models should have 1024 dimensions, got: {dimensions}"

    def test_different_models_different_embeddings(self):
        """Verify different models produce different embeddings for same text."""
        api_key = get_api_key()
        text = "Test text for model comparison."

        embeddings = {}
        for model_name in ["voyage-4", "voyage-4-lite", "voyage-4-large"]:
            model = VoyageAIEmbeddings(api_key=api_key, model=model_name)
            output = model(text)
            embeddings[model_name] = output[0].embedding

        # Embeddings should be different between models
        assert embeddings["voyage-4"] != embeddings["voyage-4-lite"]
        assert embeddings["voyage-4"] != embeddings["voyage-4-large"]
        assert embeddings["voyage-4-lite"] != embeddings["voyage-4-large"]


class TestContextualizedEmbeddings:
    """Test contextualized embedding models (voyage-context-3)."""

    def test_voyage_context_3_embedding(self):
        """Test voyage-context-3 model generates valid embeddings."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-context-3")
        output = model("The quick brown fox jumps over the lazy dog.")

        assert isinstance(output, list)
        assert len(output) == 1
        assert isinstance(output[0], DocumentWithEmbedding)
        assert isinstance(output[0].embedding, list)
        assert len(output[0].embedding) == 1024  # Default dimensions
        assert all(isinstance(x, float) for x in output[0].embedding)

    def test_voyage_context_3_batch(self):
        """Test voyage-context-3 model with batch input."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-context-3")
        texts = [
            "First document about machine learning.",
            "Second document about deep learning.",
            "Third document about neural networks.",
        ]
        output = model(texts)

        assert len(output) == 3
        assert all(isinstance(doc, DocumentWithEmbedding) for doc in output)
        assert all(len(doc.embedding) == 1024 for doc in output)


class TestTokenAwareBatching:
    """Test token-aware batching functionality."""

    def test_token_aware_batching_small_input(self):
        """Test that small inputs work without batching issues."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")
        texts = ["Short text.", "Another short one."]
        output = model(texts)
        assert len(output) == 2
        assert all(len(doc.embedding) == 1024 for doc in output)

    def test_token_aware_batching_preserves_order(self):
        """Test that batching preserves the order of inputs."""
        model = VoyageAIEmbeddings(api_key=get_api_key(), model="voyage-4")
        texts = [
            "First document about cats.",
            "Second document about dogs.",
            "Third document about birds.",
            "Fourth document about fish.",
        ]
        output = model(texts)

        # Verify order is preserved by checking content
        assert output[0].content == texts[0]
        assert output[1].content == texts[1]
        assert output[2].content == texts[2]
        assert output[3].content == texts[3]

    def test_output_dimension_parameter(self):
        """Test that output_dimension parameter works for voyage-4 models."""
        model = VoyageAIEmbeddings(
            api_key=get_api_key(),
            model="voyage-4",
            output_dimension=512,
        )
        output = model("Test text for dimension check.")
        assert len(output[0].embedding) == 512

    def test_output_dimension_256(self):
        """Test 256-dimensional output."""
        model = VoyageAIEmbeddings(
            api_key=get_api_key(),
            model="voyage-4-lite",
            output_dimension=256,
        )
        output = model("Test text.")
        assert len(output[0].embedding) == 256

    def test_custom_batch_size(self):
        """Test custom batch_size parameter."""
        model = VoyageAIEmbeddings(
            api_key=get_api_key(),
            model="voyage-4",
            batch_size=2,
        )
        texts = ["Text one.", "Text two.", "Text three.", "Text four."]
        output = model(texts)
        assert len(output) == 4
        # All should have embeddings
        assert all(len(doc.embedding) > 0 for doc in output)


class TestVoyageAIReranking:
    """Integration tests for VoyageAI reranker models."""

    def test_rerank_2_5_basic(self):
        """Test rerank-2.5 model basic functionality."""
        reranker = VoyageAIReranking(api_key=get_api_key(), model_name="rerank-2.5")

        docs = [
            Document(content="Python is a programming language."),
            Document(content="The cat sat on the mat."),
            Document(content="Python programming tutorials for beginners."),
        ]
        query = "How to learn Python programming?"

        result = reranker.run(docs, query)

        assert len(result) == 3
        # All documents should have reranking scores
        assert all("reranking_score" in doc.metadata for doc in result)
        # Scores should be between 0 and 1
        assert all(0 <= doc.metadata["reranking_score"] <= 1 for doc in result)

    def test_rerank_2_5_lite(self):
        """Test rerank-2.5-lite model."""
        reranker = VoyageAIReranking(
            api_key=get_api_key(), model_name="rerank-2.5-lite"
        )

        docs = [
            Document(content="Machine learning is a subset of AI."),
            Document(content="The weather is sunny today."),
            Document(content="Deep learning neural networks."),
        ]
        query = "What is machine learning?"

        result = reranker.run(docs, query)

        assert len(result) == 3
        assert all("reranking_score" in doc.metadata for doc in result)

    def test_rerank_relevance_ordering(self):
        """Test that reranker properly orders documents by relevance."""
        reranker = VoyageAIReranking(api_key=get_api_key(), model_name="rerank-2.5")

        # Create documents where relevance is obvious
        docs = [
            Document(content="The history of ancient Rome."),
            Document(content="Python programming language tutorial."),
            Document(content="Best practices for Python development."),
        ]
        query = "Python programming tutorial"

        result = reranker.run(docs, query)

        # Results should be ordered by relevance (highest first)
        scores = [doc.metadata["reranking_score"] for doc in result]
        assert scores == sorted(scores, reverse=True)

        # The Python-related docs should score higher than Rome doc
        rome_doc = next(d for d in result if "Rome" in d.content)
        python_docs = [d for d in result if "Python" in d.content]
        assert all(
            d.metadata["reranking_score"] > rome_doc.metadata["reranking_score"]
            for d in python_docs
        )

    def test_rerank_with_top_k(self):
        """Test reranker with top_k parameter."""
        reranker = VoyageAIReranking(
            api_key=get_api_key(),
            model_name="rerank-2.5",
            top_k=2,
        )

        docs = [
            Document(content="Document one."),
            Document(content="Document two."),
            Document(content="Document three."),
            Document(content="Document four."),
        ]
        query = "Find documents"

        result = reranker.run(docs, query)

        # Should only return top 2 documents
        assert len(result) == 2

    def test_rerank_empty_documents(self):
        """Test reranker with empty document list."""
        reranker = VoyageAIReranking(api_key=get_api_key(), model_name="rerank-2.5")

        result = reranker.run([], "query")

        assert result == []

    def test_rerank_2_legacy(self):
        """Test legacy rerank-2 model still works."""
        reranker = VoyageAIReranking(api_key=get_api_key(), model_name="rerank-2")

        docs = [
            Document(content="Test document one."),
            Document(content="Test document two."),
        ]
        query = "Test query"

        result = reranker.run(docs, query)

        assert len(result) == 2
        assert all("reranking_score" in doc.metadata for doc in result)
