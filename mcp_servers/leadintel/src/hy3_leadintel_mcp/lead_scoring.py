from __future__ import annotations

from dataclasses import dataclass


POSITIVE_SIGNALS = {
    "automation": 12,
    "ai": 10,
    "agent": 10,
    "sales": 8,
    "export": 8,
    "manufacturing": 8,
    "motor": 10,
    "crm": 6,
    "rfq": 15,
    "采购": 15,
    "自动化": 12,
    "电机": 10,
    "出海": 8,
    "询盘": 15,
}

RISK_SIGNALS = {
    "student": 10,
    "competitor": 12,
    "unclear": 6,
    "no budget": 15,
    "个人": 8,
    "竞品": 12,
    "预算不明": 10,
}


@dataclass(frozen=True)
class LeadScore:
    score: int
    priority: str
    positive_signals: list[str]
    risks: list[str]


def score_lead_text(text: str) -> LeadScore:
    lowered = text.lower()
    score = 50
    positive: list[str] = []
    risks: list[str] = []

    for signal, weight in POSITIVE_SIGNALS.items():
        if signal.lower() in lowered:
            score += weight
            positive.append(signal)

    for signal, penalty in RISK_SIGNALS.items():
        if signal.lower() in lowered:
            score -= penalty
            risks.append(signal)

    score = max(0, min(100, score))
    if score >= 80:
        priority = "P0"
    elif score >= 65:
        priority = "P1"
    elif score >= 45:
        priority = "P2"
    else:
        priority = "P3"

    return LeadScore(score=score, priority=priority, positive_signals=positive, risks=risks)
