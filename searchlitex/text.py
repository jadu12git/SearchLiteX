import re
from collections import Counter

_WORD = re.compile(r"[^\W_]+", re.UNICODE)

def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise ValueError("Document text must be a string")
    return _WORD.findall(text.casefold())

def frequencies(text: str) -> Counter:
    return Counter(tokenize(text))
