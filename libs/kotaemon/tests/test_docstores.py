import os
from unittest.mock import patch

import pytest
from elastic_transport import ApiResponseMeta

from kotaemon.base import Document
from kotaemon.storages import (
    ElasticsearchDocumentStore,
    InMemoryDocumentStore,
    SimpleFileDocumentStore,
)

meta_success = ApiResponseMeta(
    status=200,
    http_version="1.1",
    headers={"x-elastic-product": "Elasticsearch"},
    duration=1.0,
    node=None,
)
meta_fail = ApiResponseMeta(
    status=404,
    http_version="1.1",
    headers={"x-elastic-product": "Elasticsearch"},
    duration=1.0,
    node=None,
)
_elastic_search_responses = [
    # check exist
    (meta_fail, None),
    # create index
    (
        meta_success,
        {"acknowledged": True, "shards_acknowledged": True, "index": "test"},
    ),
    # count API
    (
        meta_success,
        [{"epoch": "1700474422", "timestamp": "10:00:22", "count": "0"}],
    ),
    # add documents
    (
        meta_success,
        {
            "took": 50,
            "errors": False,
            "items": [
                {
                    "index": {
                        "_index": "test",
                        "_id": "a3774dab-b8f1-43ba-adb8-842cb7a76eeb",
                        "_version": 1,
                        "result": "created",
                        "_shards": {"total": 2, "successful": 1, "failed": 0},
                        "_seq_no": 0,
                        "_primary_term": 1,
                        "status": 201,
                    }
                },
                {
                    "index": {
                        "_index": "test",
                        "_id": "b44f5593-7587-4f91-afd0-5736e5bd5bfe",
                        "_version": 1,
                        "result": "created",
                        "_shards": {"total": 2, "successful": 1, "failed": 0},
                        "_seq_no": 1,
                        "_primary_term": 1,
                        "status": 201,
                    }
                },
                {
                    "index": {
                        "_index": "test",
                        "_id": "13ae7825-eef9-4214-a164-983c2e6bbeaa",
                        "_version": 1,
                        "result": "created",
                        "_shards": {"total": 2, "successful": 1, "failed": 0},
                        "_seq_no": 2,
                        "_primary_term": 1,
                        "status": 201,
                    }
                },
            ],
        },
    ),
    # check exist
    (
        meta_success,
        {"_shards": {"total": 2, "successful": 1, "failed": 0}},
    ),
    # count
    (
        meta_success,
        [{"epoch": "1700474422", "timestamp": "10:00:22", "count": "3"}],
    ),
    # get_all
    (
        meta_success,
        {
            "took": 1,
            "timed_out": False,
            "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
            "hits": {
                "total": {"value": 3, "relation": "eq"},
                "max_score": 1.0,
                "hits": [
                    {
                        "_index": "test",
                        "_id": "a3774dab-b8f1-43ba-adb8-842cb7a76eeb",
                        "_score": 1.0,
                        "_source": {"content": "Sample text 0", "metadata": {}},
                    },
                    {
                        "_index": "test",
                        "_id": "b44f5593-7587-4f91-afd0-5736e5bd5bfe",
                        "_score": 1.0,
                        "_source": {"content": "Sample text 1", "metadata": {}},
                    },
                    {
                        "_index": "test",
                        "_id": "13ae7825-eef9-4214-a164-983c2e6bbeaa",
                        "_score": 1.0,
                        "_source": {"content": "Sample text 2", "metadata": {}},
                    },
                ],
            },
        },
    ),
    # get by-id
    (
        meta_success,
        {
            "took": 1,
            "timed_out": False,
            "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "max_score": 1.0,
                "hits": [
                    {
                        "_index": "test",
                        "_id": "a3774dab-b8f1-43ba-adb8-842cb7a76eeb",
                        "_score": 1.0,
                        "_source": {"content": "Sample text 0", "metadata": {}},
                    }
                ],
            },
        },
    ),
    # query
    (
        meta_success,
        {
            "took": 2,
            "timed_out": False,
            "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
            "hits": {
                "total": {"value": 3, "relation": "eq"},
                "max_score": 0.13353139,
                "hits": [
                    {
                        "_index": "test",
                        "_id": "a3774dab-b8f1-43ba-adb8-842cb7a76eeb",
                        "_score": 0.13353139,
                        "_source": {"content": "Sample text 0", "metadata": {}},
                    },
                    {
                        "_index": "test",
                        "_id": "b44f5593-7587-4f91-afd0-5736e5bd5bfe",
                        "_score": 0.13353139,
                        "_source": {"content": "Sample text 1", "metadata": {}},
                    },
                    {
                        "_index": "test",
                        "_id": "13ae7825-eef9-4214-a164-983c2e6bbeaa",
                        "_score": 0.13353139,
                        "_source": {"content": "Sample text 2", "metadata": {}},
                    },
                ],
            },
        },
    ),
    # delete
    (
        meta_success,
        {
            "took": 10,
            "timed_out": False,
            "total": 1,
            "deleted": 1,
            "batches": 1,
            "version_conflicts": 0,
            "noops": 0,
            "retries": {"bulk": 0, "search": 0},
            "throttled_millis": 0,
            "requests_per_second": -1.0,
            "throttled_until_millis": 0,
            "failures": [],
        },
    ),
    # check exists
    (
        meta_success,
        {"_shards": {"total": 2, "successful": 1, "failed": 0}},
    ),
    # count
    (
        meta_success,
        [{"epoch": "1700549363", "timestamp": "06:49:23", "count": "2"}],
    ),
]


def test_inmemory_document_store_base_interfaces(tmp_path):
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

    os.remove(tmp_path / "store.json")


def test_simplefile_document_store_base_interfaces(tmp_path):
    """Test all interfaces of a a document store"""

    store = SimpleFileDocumentStore(path=tmp_path)
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
    assert (tmp_path / "default.json").exists(), "File should exist"

    # Test load
    store2 = SimpleFileDocumentStore(path=tmp_path)
    assert len(store2.get_all()) == 17, "Laded document store should have 17 documents"

    os.remove(tmp_path / "default.json")


@patch(
    "elastic_transport.Transport.perform_request",
    side_effect=_elastic_search_responses,
)
def test_elastic_document_store(elastic_api):
    store = ElasticsearchDocumentStore(collection_name="test")

    docs = [
        Document(text=f"Sample text {idx}", meta={"meta_key": f"meta_value_{idx}"})
        for idx in range(3)
    ]

    # Test add and get all
    assert store.count() == 0, "Document store should be empty"
    store.add(docs)
    assert store.count() == 3, "Document store count should changed after adding docs"

    docs = store.get_all()
    first_doc = docs[0]
    assert len(docs) == 3, "Document store get_all() failed"

    doc_by_ids = store.get(first_doc.doc_id)
    assert doc_by_ids[0].doc_id == first_doc.doc_id, "Document store get() failed"

    docs = store.query("text")
    assert len(docs) == 3, "Document store query() failed"

    # delete test
    store.delete(first_doc.doc_id)
    assert store.count() == 2, "Document store delete() failed"

    elastic_api.assert_called()
