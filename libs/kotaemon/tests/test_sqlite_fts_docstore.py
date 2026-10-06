import sqlite3

import pytest

from kotaemon.base import Document
from kotaemon.storages.docstores import SQLiteFTSDocumentStore
from kotaemon.storages.docstores.sqlite_fts import lexical_tokens


def test_empty_allowlist_cannot_search_all_documents():
    store = SQLiteFTSDocumentStore()
    store.add(
        [Document(id_="a", text="VPN reset"), Document(id_="b", text="VPN admin")]
    )

    assert store.query("VPN", doc_ids=[]) == []
    assert [d.doc_id for d in store.query("VPN", doc_ids=["a"])] == ["a"]


def test_match_syntax_is_quoted_not_executed():
    store = SQLiteFTSDocumentStore()
    store.add(
        [
            Document(id_="literal", text="OR is ordinary text"),
            Document(id_="unrelated", text="VPN reset"),
        ]
    )

    assert [d.doc_id for d in store.query('" OR * )')] == ["literal"]


def test_delete_updates_fts():
    store = SQLiteFTSDocumentStore()
    store.add(Document(id_="a", text="VPN reset"))

    store.delete("a")

    assert store.query("VPN") == []
    assert store.count() == 0


def test_fts_unavailable_keeps_get_usable():
    class NoFTSConnection:
        def __init__(self, connection):
            self.connection = connection

        def execute(self, sql, parameters=()):
            if "CREATE VIRTUAL TABLE" in sql:
                raise sqlite3.OperationalError("no such module: fts5")
            return self.connection.execute(sql, parameters)

        def close(self):
            self.connection.close()

    store = SQLiteFTSDocumentStore(
        connection_factory=lambda database: NoFTSConnection(sqlite3.connect(database))
    )
    document = Document(id_="a", text="VPN reset", metadata={"kind": "guide"})

    store.add(document)

    assert store.supports_lexical_search is False
    assert store.capability_reason
    assert store.get("a")[0].text == document.text
    assert store.get("a")[0].metadata == document.metadata
    with pytest.raises(RuntimeError, match="lexical search is unavailable"):
        store.query("VPN")


def test_mixed_chinese_latin_terms_recall():
    store = SQLiteFTSDocumentStore()
    store.add(Document(id_="manual", text="请检查企业VPN登录流程"))

    assert [d.doc_id for d in store.query("VPN")] == ["manual"]
    assert [d.doc_id for d in store.query("登录")] == ["manual"]


def test_cjk_bigrams_do_not_bridge_metadata_or_unrelated_fields():
    store = SQLiteFTSDocumentStore()
    store.add(
        Document(
            id_="split-fields",
            text="VPN reset",
            metadata={"note": "登录流程"},
        )
    )

    assert store.query("登录") == []


def test_cjk_bigrams_do_not_bridge_separated_text_runs():
    store = SQLiteFTSDocumentStore()
    store.add(Document(id_="separated", text="登 录"))

    assert store.query("登录") == []


def test_explicitly_delimited_single_cjk_character_is_searchable():
    store = SQLiteFTSDocumentStore()
    store.add(
        [
            Document(id_="single", text="登"),
            Document(id_="within_run", text="登出"),
        ]
    )

    assert [doc.doc_id for doc in store.query("登")] == ["single"]


def test_bm25_order_is_deterministic():
    store = SQLiteFTSDocumentStore()
    store.add(
        [
            Document(id_="z", text="VPN reset"),
            Document(id_="a", text="VPN reset"),
        ]
    )

    first = [doc.doc_id for doc in store.query("VPN reset")]
    second = [doc.doc_id for doc in store.query("VPN reset")]
    assert first == ["a", "z"]
    assert second == first


def test_bm25_relevance_precedes_id_tiebreak():
    store = SQLiteFTSDocumentStore()
    store.add(
        [
            Document(id_="a_less_relevant", text="VPN archive unrelated words"),
            Document(id_="z_more_relevant", text="VPN reset"),
        ]
    )

    assert [doc.doc_id for doc in store.query("VPN reset")] == [
        "z_more_relevant",
        "a_less_relevant",
    ]


def test_latin_tokens_use_nfkc_and_casefold():
    assert lexical_tokens("ＶＰＮ VPN Vpn") == ("vpn",)


def test_cjk_bigram_preprocessing_includes_kana_and_hangul():
    assert lexical_tokens("ひらがな") == ("ひら", "らが", "がな")
    assert lexical_tokens("서울은") == ("서울", "울은")


def test_single_cjk_character_inside_a_run_is_not_a_keyword():
    store = SQLiteFTSDocumentStore()
    store.add(Document(id_="guide", text="重置企业VPN密码"))

    assert store.query("企") == []


def test_add_get_get_all_count_and_exist_ok_semantics():
    store = SQLiteFTSDocumentStore()
    first = Document(id_="a", text="VPN reset", metadata={"version": 1})
    replacement = Document(id_="a", text="VPN admin", metadata={"version": 2})

    store.add(first)
    assert store.count() == 1
    assert store.get(["a"])[0].metadata == {"version": 1}
    assert [doc.doc_id for doc in store.get_all()] == ["a"]
    with pytest.raises(ValueError):
        store.add(replacement)

    store.add(replacement, exist_ok=True)
    assert store.get("a")[0].metadata == {"version": 2}
    assert [doc.doc_id for doc in store.query("admin")] == ["a"]
    assert store.query("reset") == []


def test_close_closes_the_connection():
    store = SQLiteFTSDocumentStore()
    connection = store._connection

    store.close()

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
