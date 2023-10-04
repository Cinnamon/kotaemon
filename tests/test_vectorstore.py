import json

from kotaemon.documents.base import Document
from kotaemon.vectorstores import ChromaVectorStore, InMemoryVectorStore


class TestChromaVectorStore:
    def test_add(self, tmp_path):
        """Test that the DB add correctly"""
        db = ChromaVectorStore(path=str(tmp_path))

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        ids = ["1", "2"]

        assert db._collection.count() == 0, "Expected empty collection"
        output = db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        assert output == ids, "Expected output to be the same as ids"
        assert db._collection.count() == 2, "Expected 2 added entries"

    def test_add_from_docs(self, tmp_path):
        db = ChromaVectorStore(path=str(tmp_path))

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        documents = [
            Document(embedding=embedding, metadata=metadata)
            for embedding, metadata in zip(embeddings, metadatas)
        ]
        assert db._collection.count() == 0, "Expected empty collection"
        output = db.add_from_docs(documents)
        assert len(output) == 2, "Expected outputing 2 ids"
        assert db._collection.count() == 2, "Expected 2 added entries"

    def test_delete(self, tmp_path):
        db = ChromaVectorStore(path=str(tmp_path))

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        ids = ["a", "b", "c"]

        db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        assert db._collection.count() == 3, "Expected 3 added entries"
        db.delete(ids=["a", "b"])
        assert db._collection.count() == 1, "Expected 1 remaining entry"
        db.delete(ids=["c"])
        assert db._collection.count() == 0, "Expected 0 remaining entry"

    def test_query(self, tmp_path):
        db = ChromaVectorStore(path=str(tmp_path))

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        ids = ["a", "b", "c"]

        db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)

        _, sim, out_ids = db.query(embedding=[0.1, 0.2, 0.3], top_k=1)
        assert sim == [1.0]
        assert out_ids == ["a"]

        _, _, out_ids = db.query(embedding=[0.42, 0.52, 0.53], top_k=1)
        assert out_ids == ["b"]

    def test_save_load_delete(self, tmp_path):
        """Test that save/load func behave correctly."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        ids = ["1", "2", "3"]
        db = ChromaVectorStore(path=str(tmp_path))
        db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        db.save()

        db2 = ChromaVectorStore(path=str(tmp_path))
        db2.load()
        assert (
            db2._collection.count() == 3
        ), "load function does not load data completely"

        # test delete collection function
        db2.delete_collection()
        # reinit the chroma with the same collection name
        db2 = ChromaVectorStore(path=str(tmp_path))
        assert (
            db2._collection.count() == 0
        ), "delete collection function does not work correctly"


class TestInMemoryVectorStore:
    def test_add(self):
        """Test that add func adds correctly."""

        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        ids = ["1", "2"]
        db = InMemoryVectorStore()

        output = db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        assert output == ids, "Excepted output to be the same as ids"

    def test_save_load_delete(self, tmp_path):
        """Test that delete func deletes correctly."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        metadatas = [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        ids = ["1", "2", "3"]
        db = InMemoryVectorStore()
        db.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        db.delete(["3"])
        db.save(save_path=tmp_path / "test_save_load_delete.json")
        f = open(tmp_path / "test_save_load_delete.json")
        data = json.load(f)
        assert (
            "1" and "2" in data["text_id_to_ref_doc_id"]
        ), "save function does not save data completely"
        assert (
            "3" not in data["text_id_to_ref_doc_id"]
        ), "delete function does not delete data completely"
        db2 = InMemoryVectorStore()
        db2.load(load_path=tmp_path / "test_save_load_delete.json")
        assert db2.get("2") == [
            0.4,
            0.5,
            0.6,
        ], "load function does not load data completely"
