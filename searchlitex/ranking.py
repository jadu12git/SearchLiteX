import math
from collections import Counter

from .text import tokenize


def rank(query: str, document_terms: dict[str, dict[str, int]], limit: int = 10):
    """TF-IDF, log-scaled term frequency, smoothed IDF and cosine normalization."""
    tokens = tokenize(query)
    if not tokens or limit < 1 or not document_terms:
        return []

    terms = Counter(tokens)
    docs = len(document_terms)

    # Compute corpus document frequencies once, instead of rescanning every
    # document for each term of every document during normalization.
    document_frequency = Counter(
        term for counts in document_terms.values() for term in counts
    )
    idf = {
        term: math.log((1 + docs) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }
    unseen_idf = math.log(1 + docs) + 1
    qvec = {
        term: (1 + math.log(count)) * idf.get(term, unseen_idf)
        for term, count in terms.items()
    }
    qnorm = math.sqrt(sum(value ** 2 for value in qvec.values()))

    results = []
    for doc_id, counts in document_terms.items():
        dot = 0.0
        dnorm_sq = 0.0
        for term, count in counts.items():
            if count <= 0:
                continue
            weight = (1 + math.log(count)) * idf[term]
            dnorm_sq += weight * weight
            dot += weight * qvec.get(term, 0)
        if dot > 0 and dnorm_sq:
            results.append((doc_id, dot / (math.sqrt(dnorm_sq) * qnorm)))
    return sorted(results, key=lambda row: (-row[1], row[0]))[:limit]
