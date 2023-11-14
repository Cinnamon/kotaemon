import pytest

from kotaemon.base import Document
from kotaemon.storages import InMemoryDocumentStore


def test_simple_document_store_base_interfaces(tmp_path):
    """Test all interfaces of a a document store"""

    store = InMemoryDocumentStore()
    docs = [
        Document(text=f"Sample text {idx}", meta={"meta_key": f"meta_value_{idx}"})
        for idx in range(10)
    ]

    # Test add and get all
    assert len(store.get_all()) == 0, "Document store should be empty"
    store.add(docs)
    assert len(store.get_all()) == 10, "Document store should have 10 documents"

    # Test add with provided ids
    store.add(docs=docs, ids=[f"doc_{idx}" for idx in range(10)])
    assert len(store.get_all()) == 20, "Document store should have 20 documents"

    # Test add without exist_ok
    with pytest.raises(ValueError):
        store.add(docs=docs, ids=[f"doc_{idx}" for idx in range(10)])

    # Update ok with add exist_ok
    store.add(docs=docs, ids=[f"doc_{idx}" for idx in range(10)], exist_ok=True)
    assert len(store.get_all()) == 20, "Document store should have 20 documents"

    # Test get with str id
    matched = store.get(docs[0].doc_id)
    assert len(matched) == 1, "Should return 1 document"
    assert matched[0].text == docs[0].text, "Should return the correct document"

    # Test get with list of ids
    matched = store.get([docs[0].doc_id, docs[1].doc_id])
    assert len(matched) == 2, "Should return 2 documents"
    assert [doc.text for doc in matched] == [doc.text for doc in docs[:2]]

    # Test delete with str id
    store.delete(docs[0].doc_id)
    assert len(store.get_all()) == 19, "Document store should have 19 documents"

    # Test delete with list of ids
    store.delete([docs[1].doc_id, docs[2].doc_id])
    assert len(store.get_all()) == 17, "Document store should have 17 documents"

    # Test save
    store.save(tmp_path / "store.json")
    assert (tmp_path / "store.json").exists(), "File should exist"

    # Test load
    store2 = InMemoryDocumentStore()
    store2.load(tmp_path / "store.json")
    assert len(store2.get_all()) == 17, "Laded document store should have 17 documents"
