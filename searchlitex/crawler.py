"""Explicit-URL HTML retrieval with SSRF safety rules. No arbitrary recursive spidering."""
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit
import httpx
from bs4 import BeautifulSoup

MAX_DOCUMENT_BYTES = 1_000_000

def safe_url(raw: str) -> str:
    if not isinstance(raw, str) or len(raw) > 2048:
        raise ValueError("Invalid URL")
    # urlsplit() and URL.port can raise ValueError for malformed IPv6 or ports.
    # Normalize these to a validation error so the API returns HTTP 422, not 500.
    try:
        u = urlsplit(raw)
        hostname = u.hostname
        port = u.port
    except ValueError as exc:
        raise ValueError("Invalid URL") from exc
    if port == 0:
        raise ValueError("Invalid URL")
    if u.scheme not in ("https", "http") or not hostname or u.username or u.password:
        raise ValueError("Only public HTTP(S) URLs are supported")
    try:
        addresses = socket.getaddrinfo(hostname, port or (443 if u.scheme == "https" else 80))
    except OSError as exc:
        raise ValueError("Cannot resolve hostname") from exc
    if not addresses:
        raise ValueError("Cannot resolve hostname")
    for addr in addresses:
        ip = ipaddress.ip_address(addr[4][0])
        if not ip.is_global:
            raise ValueError("Local, private and reserved network targets are forbidden")
    return urlunsplit((u.scheme, u.netloc.lower(), u.path or "/", u.query, ""))

def parse_html(html: str) -> tuple[str, str]:
    if not isinstance(html, str):
        raise ValueError("HTML must be text")
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled page"
    text = soup.get_text(" ", strip=True)
    if not text:
        raise ValueError("Document has no searchable content")
    return title[:300], text[:MAX_DOCUMENT_BYTES]

def crawl(url: str) -> tuple[str, str, str]:
    url = safe_url(url)
    # Trust no redirects; never let a public URL redirect into a private network.
    with httpx.Client(follow_redirects=False, timeout=10.0, trust_env=False) as client:
        with client.stream("GET", url, headers={"User-Agent": "SearchLiteX/1.0 (educational crawler)"}) as response:
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError("Redirects are not followed")
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                raise ValueError("Only HTML pages can be crawled")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_DOCUMENT_BYTES:
                    raise ValueError("Document exceeds size limit")
    title, text = parse_html(body.decode("utf-8", errors="replace"))
    return url, title, text
