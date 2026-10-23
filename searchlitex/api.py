from contextlib import asynccontextmanager
from urllib.parse import urlsplit
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from .store import Store
from .crawler import crawl, parse_html

store = Store()

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.initialize()
    yield

app = FastAPI(title="SearchLiteX", description="A document search engine powered by PostgreSQL inverted indexing and TF-IDF", version="1.0.0", lifespan=lifespan)

class DocumentInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=1000000)

class CrawlInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)

@app.get("/health")
def health():
    try:
        with store.connection() as db:
            db.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(503, "Database unavailable")

@app.post("/api/documents", status_code=201)
def add_document(doc: DocumentInput):
    try:
        return store.upsert(doc.url, doc.title, doc.content)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

@app.post("/api/crawl", status_code=201)
def crawl_url(item: CrawlInput):
    try:
        url, title, body = crawl(item.url)
        return store.upsert(url, title, body)
    except (ValueError, OSError, Exception) as exc:
        # Deliberately avoid returning potentially sensitive network/DB details.
        raise HTTPException(422, f"Crawl failed: {type(exc).__name__}")

@app.get("/api/search")
def search(q: str = Query(default="", max_length=500), limit: int = Query(default=10, ge=1, le=50)):
    return {"query": q, "results": store.search(q, limit)}

@app.get("/api/documents")
def list_documents():
    return store.list()

@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int):
    if not store.delete(doc_id):
        raise HTTPException(404, "Document not found")
