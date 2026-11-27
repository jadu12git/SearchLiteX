"""Live PostgreSQL and HTTP API integration test. Uses only Python stdlib."""
import json
import os
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = os.getenv("SEARCHLITEX_URL", "http://localhost:8000")
def call(method, path, data=None):
    req = Request(BASE + path, method=method, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read()) if resp.status != 204 else None

def main():
    for attempt in range(90):
        try:
            _, health = call("GET", "/health")
            if health["status"] == "ok":
                break
        except (URLError, HTTPError, OSError, TimeoutError, ConnectionError):
            pass  # API may reset connections while its process is starting.
        time.sleep(1)
    else:
        raise AssertionError("API not ready after 90 seconds; check: docker compose logs api")
    marker = uuid.uuid4().hex
    ids = []
    python_term = "python" + marker
    try:
        status, a = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/a", "title": "Python search", "content": f"{python_term} {python_term} inverted index tf idf"})
        assert status == 201
        ids.append(a["id"])
        _, b = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/b", "title": "Java client", "content": "java java java rest api"})
        ids.append(b["id"])
        _, duplicate = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/a", "title": "Python search", "content": f"{python_term} {python_term} inverted index tf idf"})
        assert duplicate["id"] == a["id"]
        _, result = call("GET", f"/api/search?q={python_term}")
        assert result["results"] and result["results"][0]["id"] == a["id"]
        _, empty = call("GET", "/api/search?q=")
        assert empty["results"] == []
        _, listing = call("GET", "/api/documents")
        assert any(row["id"] == a["id"] for row in listing)
        # Re-indexing must remove stale postings, not merely preserve the ID.
        replacement_term = "replacement" + marker
        _, updated = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/a", "title": "Updated document", "content": replacement_term})
        assert updated["id"] == a["id"]
        _, stale = call("GET", f"/api/search?q={python_term}")
        assert all(row["id"] != a["id"] for row in stale["results"])
        _, fresh = call("GET", f"/api/search?q={replacement_term}")
        assert any(row["id"] == a["id"] for row in fresh["results"])
        status, _ = call("DELETE", f"/api/documents/{a['id']}")
        assert status == 204
        ids.remove(a["id"])
        _, deleted = call("GET", f"/api/search?q={replacement_term}")
        assert all(row["id"] != a["id"] for row in deleted["results"])
    finally:
        for id in ids:
            call("DELETE", f"/api/documents/{id}")
    print("PASS real PostgreSQL upsert, duplicate URL deduplication, TF-IDF ranking, query and listing")
    print("ALL SEARCHLITEX INTEGRATION CHECKS PASSED")

if __name__ == "__main__":
    main()
