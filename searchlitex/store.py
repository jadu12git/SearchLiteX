import os
import hashlib
from collections import Counter
from uuid import UUID
import psycopg
from psycopg.rows import dict_row
from .text import frequencies
from .ranking import rank

DDL = """
CREATE TABLE IF NOT EXISTS documents (
 id BIGSERIAL PRIMARY KEY,
 url TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL,
 body TEXT NOT NULL,
 checksum CHAR(64) NOT NULL,
 indexed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS postings (
 document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 term TEXT NOT NULL,
 frequency INTEGER NOT NULL CHECK (frequency > 0),
 PRIMARY KEY (document_id, term)
);
CREATE INDEX IF NOT EXISTS postings_term_idx ON postings(term);
"""

class Store:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL", "postgresql://searchlite:searchlite@localhost:5432/searchlite")

    def connection(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def initialize(self):
        with self.connection() as db:
            db.execute(DDL)

    def upsert(self, url: str, title: str, body: str):
        if not url or not isinstance(url, str) or not isinstance(title, str) or not isinstance(body, str):
            raise ValueError("url, title and body must be strings")
        if not body.strip() or len(body.encode("utf-8")) > 1_000_000:
            raise ValueError("Body must be nonempty and at most 1 MB")
        checksum = hashlib.sha256(body.encode()).hexdigest()
        counts = frequencies(title + " " + body)
        with self.connection() as db:
            row = db.execute("""
                INSERT INTO documents(url,title,body,checksum) VALUES (%s,%s,%s,%s)
                ON CONFLICT(url) DO UPDATE SET title=EXCLUDED.title,
                body=EXCLUDED.body, checksum=EXCLUDED.checksum,
                indexed_at=NOW() RETURNING id
            """, (url, title[:300], body, checksum)).fetchone()
            doc_id = row["id"]
            db.execute("DELETE FROM postings WHERE document_id=%s", (doc_id,))
            with db.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO postings(document_id,term,frequency) VALUES (%s,%s,%s)",
                    [(doc_id, term, count) for term, count in counts.items()]
                )
        return {"id": doc_id, "url": url, "title": title[:300], "checksum": checksum, "term_count": sum(counts.values())}

    def list(self):
        with self.connection() as db:
            return db.execute("SELECT id,url,title,checksum FROM documents ORDER BY id").fetchall()

    def delete(self, doc_id: int):
        with self.connection() as db:
            return bool(db.execute("DELETE FROM documents WHERE id=%s", (doc_id,)).rowcount)

    def search(self, query: str, limit: int = 10):
        if not query.strip():
            return []
        # Fetch only docs containing at least one query term; compute corpus-wide IDF on the full index.
        from .text import tokenize
        terms = sorted(set(tokenize(query)))
        if not terms:
            return []
        with self.connection() as db:
            rows = db.execute("SELECT id,url,title,body FROM documents ORDER BY id").fetchall()
            postings = db.execute("SELECT document_id,term,frequency FROM postings").fetchall()
        contents = {str(row["id"]): {} for row in rows}
        for post in postings:
            contents[str(post["document_id"])][post["term"]] = post["frequency"]
        scored = rank(query, contents, limit)
        by_id = {str(row["id"]): row for row in rows}
        return [
            {"id": int(doc_id), "url": by_id[doc_id]["url"], "title": by_id[doc_id]["title"],
             "snippet": by_id[doc_id]["body"][:180], "score": round(score, 6)}
            for doc_id, score in scored
        ]
