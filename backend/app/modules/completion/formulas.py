"""Pure money / rating formulas (no I/O)."""
from decimal import ROUND_HALF_UP, Decimal
from statistics import mean

_CENT = Decimal("0.01")


def member_stats(subs):
    """subs: iterable of dicts/rows with 'status' and 'ai_quality_score'."""
    subs = list(subs)
    submitted = len(subs)
    approved_subs = [s for s in subs if s["status"] == "approved"]
    approved = len(approved_subs)
    approval_ratio = approved / submitted if submitted else 0.0
    if approved:
        impact = mean(0.5 if s["ai_quality_score"] is None else float(s["ai_quality_score"]) for s in approved_subs)
    else:
        impact = 0.0
    raw = approved * (0.5 * approval_ratio + 0.5 * impact)
    return {
        "submitted": submitted,
        "approved": approved,
        "approval_ratio": approval_ratio,
        "impact": impact,
        "raw": raw,
    }


def compute_shares(raws):
    total = sum(raws.values())
    if total <= 0:
        return {k: 0.0 for k in raws}
    return {k: v / total for k, v in raws.items()}


def split_amounts(shares, pool):
    """Split pool by shares to 2dp; rounding remainder goes to the top earner so the sum == pool."""
    if not shares:
        return {}
    pool_d = Decimal(str(pool)).quantize(_CENT, rounding=ROUND_HALF_UP)
    if sum(shares.values()) <= 0:
        return {k: 0.0 for k in shares}
    amounts = {
        k: (Decimal(str(s)) * pool_d).quantize(_CENT, rounding=ROUND_HALF_UP) for k, s in shares.items()
    }
    remainder = pool_d - sum(amounts.values())
    top = max(shares, key=lambda k: shares[k])
    amounts[top] += remainder
    return {k: float(v) for k, v in amounts.items()}


def project_score(raw, max_raw, approval_ratio):
    if raw == 0 or not max_raw:
        return 1.0
    performance = 0.5 * (raw / max_raw) + 0.5 * approval_ratio
    return round(1 + 4 * performance, 1)


def new_final_rating(previous_scores, new_score):
    return round(mean(list(previous_scores) + [new_score]), 1)


def effective_researcher_pcts(rows):
    """rows: list of (researcher_id, share_pct|None). Equal split when any share is unset."""
    rows = list(rows)
    if not rows:
        return {}
    if any(p is None for _, p in rows):
        eq = round(100 / len(rows), 2)
        return {i: eq for i, _ in rows}
    return {i: float(p) for i, p in rows}


def split_researcher_pool(pool, shares, lead_id):
    """shares: {researcher_id: pct|None}. Any None -> equal split. Remainder goes to the lead."""
    if not shares:
        return {}
    pool_d = Decimal(str(pool)).quantize(_CENT, rounding=ROUND_HALF_UP)
    n = len(shares)
    equal = any(p is None for p in shares.values())
    amounts = {}
    for rid, pct in shares.items():
        frac = Decimal(1) / n if equal else Decimal(str(pct)) / 100
        amounts[rid] = (pool_d * frac).quantize(_CENT, rounding=ROUND_HALF_UP)
    remainder = pool_d - sum(amounts.values())
    amounts[lead_id if lead_id in amounts else next(iter(amounts))] += remainder
    return {k: float(v) for k, v in amounts.items()}
