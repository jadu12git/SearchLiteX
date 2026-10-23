"""Live PostgreSQL and HTTP API integration test. Uses only Python stdlib."""
import json
import os
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE = os.getenv("SEARCHLITEX_URL", "http://localhost:8000")
def call(method, path, data=None):
    req = Request(BASE + path, method=method, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read()) if resp.status != 204 else None

def main():
    for _ in range(50):
        try:
            _, health = call("GET", "/health")
            if health["status"] == "ok": break
        except URLError: time.sleep(1)
    else: raise AssertionError("API not ready")
    marker = uuid.uuid4().hex
    ids = []
    try:
        status, a = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/a", "title": "Python search", "content": "python python inverted index tf idf"})
        assert status == 201
        ids.append(a["id"])
        _, b = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/b", "title": "Java client", "content": "java java java rest api"})
        ids.append(b["id"])
        _, duplicate = call("POST", "/api/documents", {"url": f"https://example.org/{marker}/a", "title": "Python search", "content": "python python inverted index tf idf"})
        assert duplicate["id"] == a["id"]
        _, result = call("GET", "/api/search?q=python%20index")
        assert result["results"] and result["results"][0]["id"] == a["id"]
        _, empty = call("GET", "/api/search?q=")
        assert empty["results"] == []
        _, listing = call("GET", "/api/documents")
        assert any(row["id"] == a["id"] for row in listing)
        print("PASS real PostgreSQL upsert, duplicate URL deduplication, TF-IDF ranking, query and listing")
        print("ALL SEARCHLITEX INTEGRATION CHECKS PASSED")
    finally:
        for id in ids:
            call("DELETE", f"/api/documents/{id}")

if __name__ == "__main__":
    main()
