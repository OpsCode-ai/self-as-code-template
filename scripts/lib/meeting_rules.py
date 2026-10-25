"""What a meeting's business part never carries unasked: money, ownership, jobs.

One rule, two users. The voice sorter (lib/voice_routes.py) holds back a
chapter whose title or summary trips it, and /sac meeting (sac-meeting.py)
stops a business part until the person says yes to that line. Adam, 10 and 20
October 2026: shares, the MOU, the trust, a salary, someone joining or leaving
are talked about in meetings and must never reach a business repo by accident.
Wide on purpose; a miss can be sent by hand. Not plain 'shares', which is
mostly 'shares his screen'.

This file ships in every Self as Code pack, so it carries no name: no partner,
no customer, no deal. The hub's own confidential names live in the spoke
spec's block terms (specs/spokes/opscode-builders.yml), and the voice sorter
reads them from there (found by the pack release gate, 25 Oct 2026).
"""
from __future__ import annotations

import re

HOLD = re.compile(r"\b(shareholders?|share split|equity|stakes?|mou|cap table|term sheet|vesting|valuation|"
                  r"dividends?|salary|salaries|wages?|remuneration|invest\w*|capital raise|raising capital|"
                  r"family trust|trust structure|trust deed|trustees?|the trust|acquisition|m&a|"
                  r"ownership|co-?founder agreement|partnership agreement|"
                  r"joining (?:us|opscode)|job offer|poach\w*|resign\w*|redundanc\w*)\b", re.I)


def held(text: str) -> list[str]:
    """The words in `text` that stop it, lowercased, each once, in order."""
    seen: list[str] = []
    for m in HOLD.finditer(text or ""):
        w = m.group(0).lower()
        if w not in seen:
            seen.append(w)
    return seen
