import httpx
import pytest

from searchlitex import crawler


@pytest.mark.parametrize(
    ("charset", "body", "expected"),
    [
        ("iso-8859-1", "<html><body>café résumé</body></html>".encode("iso-8859-1"), "café résumé"),
        ("utf-8", "<html><body>東京 café</body></html>".encode("utf-8"), "東京 café"),
        ("unknown-charset", "<html><body>café</body></html>".encode("utf-8"), "café"),
    ],
)
def test_crawl_respects_response_charset(monkeypatch, charset, body, expected):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"Content-Type": f"text/html; charset={charset}"},
            content=body,
        )
    )
    real_client = httpx.Client
    monkeypatch.setattr(crawler, "safe_url", lambda url: url)
    monkeypatch.setattr(
        crawler.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    url, _, text = crawler.crawl("https://example.com/document")
    assert url == "https://example.com/document"
    assert expected in text
