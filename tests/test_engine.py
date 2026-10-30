import pytest
from searchlitex.text import tokenize, frequencies
from searchlitex.ranking import rank
from searchlitex.crawler import parse_html, safe_url

def test_tokenization():
    assert tokenize("Hello, WORLD! hello") == ["hello", "world", "hello"]

def test_unicode():
    assert tokenize("Café RÉSUMÉ") == ["café", "résumé"]

def test_frequencies():
    assert frequencies("cat cat dog") == {"cat": 2, "dog": 1}

def test_query_ranking():
    docs = {"1": {"python": 3, "search": 1}, "2": {"java": 3, "engine": 1}, "3": {"python": 1, "java": 4}}
    result = rank("python search", docs)
    assert result[0][0] == "1"

def test_empty_query():
    assert rank("", {"1": {"cat": 1}}) == []

def test_unknown_terms():
    assert rank("unicorn", {"1": {"cat": 1}}) == []

def test_tie_is_deterministic():
    assert [x[0] for x in rank("cat", {"2": {"cat": 1}, "1": {"cat": 1}})] == ["1", "2"]


def test_ranking_penalizes_unrelated_terms():
    docs = {
        "focused": {"python": 2},
        "noisy": {"python": 2, "java": 20},
    }
    assert rank("python", docs)[0][0] == "focused"

def test_ranking_uses_corpus_wide_idf():
    docs = {
        "rare": {"rare": 1},
        "common": {"common": 1},
        "both": {"rare": 1, "common": 1},
    }
    assert rank("rare", docs)[0][0] == "rare"

def test_unseen_query_term_and_result_limit():
    docs = {"1": {"python": 3}, "2": {"python": 1, "java": 3}}
    assert [doc_id for doc_id, _ in rank("python missing", docs, limit=1)] == ["1"]
    assert rank("python", docs, limit=0) == []

def test_html_cleaning():
    title, text = parse_html("<html><head><title>Hi</title><script>bad()</script></head><body><p>Search content</p></body></html>")
    assert title == "Hi" and "Search content" in text and "bad()" not in text

def test_empty_html_rejected():
    with pytest.raises(ValueError):
        parse_html("<script>ignore</script>")

def test_malformed_documents():
    with pytest.raises(ValueError):
        tokenize(None)

def test_private_url_blocked():
    with pytest.raises(ValueError):
        safe_url("http://127.0.0.1/private")

def test_file_scheme_blocked():
    with pytest.raises(ValueError):
        safe_url("file:///etc/passwd")
