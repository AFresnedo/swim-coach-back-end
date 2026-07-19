"""Step 0 of the hybrid RAG training-coach pipeline: clean the raw question
before it's embedded for retrieval (see the "Hybrid RAG training-coach
endpoint" Trello card).

Query rewriting/sharpening is deliberately NOT here. It lives in Step 3b - a
miss-triggered rescue between retrieval (Step 2) and the web-search fallback
(Step 4), gated by a runtime Redis flag - not an unconditional Step 0 pass.
Sharpening only pays off when it flips a KB miss into a hit, and that can only
happen once the KB actually holds matching content; sharpening on every
request (including ones that were already going to hit) pays the cost with no
matching payoff. Swimmer profile/goals also don't belong in the embedded
query text: concatenating them shifts the retrieval vector off-topic and
hurts cosine matching. They flow into the Step 3b rescue prompt and the final
answer prompt instead - see the card's Architecture checklist.
"""

import re

_WHITESPACE = re.compile(r"\s+")


def clean_question(raw_question: str) -> str:
    """Collapse all whitespace runs (newlines, tabs, repeated spaces) to single
    spaces and strip the ends, so pasted or multi-line input embeds the same
    as the equivalent single-line question."""
    return _WHITESPACE.sub(" ", raw_question).strip()
