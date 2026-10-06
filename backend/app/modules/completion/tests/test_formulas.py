from decimal import Decimal

from app.modules.completion import formulas as f


def _subs(n_approved, score, n_rejected=0):
    return [{"status": "approved", "ai_quality_score": score} for _ in range(n_approved)] + [
        {"status": "rejected", "ai_quality_score": 0.1} for _ in range(n_rejected)
    ]


def test_member_stats_basic_and_null_score():
    st = f.member_stats(_subs(4, 0.8, 1))
    assert st["submitted"] == 5 and st["approved"] == 4
    assert abs(st["approval_ratio"] - 0.8) < 1e-9 and abs(st["impact"] - 0.8) < 1e-9
    assert abs(st["raw"] - 3.2) < 1e-9
    assert f.member_stats([{"status": "approved", "ai_quality_score": None}])["impact"] == 0.5
    z = f.member_stats([])
    assert z["raw"] == 0 and z["approval_ratio"] == 0 and z["impact"] == 0


def test_worked_example_sums_exactly():
    a = f.member_stats(_subs(4, 0.8, 1))
    b = f.member_stats(_subs(1, 0.9))
    shares = f.compute_shares({"A": a["raw"], "B": b["raw"]})
    assert abs(sum(shares.values()) - 1) < 1e-9
    amounts = f.split_amounts(shares, 30000)
    assert amounts["A"] == 23132.53 and amounts["B"] == 6867.47
    assert sum(Decimal(str(v)) for v in amounts.values()) == Decimal("30000")


def test_remainder_goes_to_top_earner():
    shares = {"a": 1 / 3, "b": 1 / 3, "c": 1 / 3}
    amounts = f.split_amounts(shares, 100)
    assert sum(Decimal(str(v)) for v in amounts.values()) == Decimal("100.00")
    shares = {"a": 0.5, "b": 0.25, "c": 0.25}
    amounts = f.split_amounts(shares, 0.01)
    assert sum(Decimal(str(v)) for v in amounts.values()) == Decimal("0.01")
    assert amounts["a"] == 0.01


def test_zero_shares():
    assert f.compute_shares({"a": 0, "b": 0}) == {"a": 0.0, "b": 0.0}
    assert f.split_amounts({"a": 0.0}, 100) == {"a": 0.0}


def test_project_score_and_rating_average():
    assert f.project_score(0, 3.2, 0) == 1.0
    assert f.project_score(3.2, 3.2, 0.8) == 4.6
    assert f.project_score(2, 2, 1) == 5.0
    assert f.new_final_rating([4.0], 5.0) == 4.5
    assert f.new_final_rating([], 3.0) == 3.0


def test_researcher_split_equal_weighted_remainder():
    eq = f.split_researcher_pool(100, {"l": None, "a": None, "b": None}, "l")
    assert eq == {"l": 33.34, "a": 33.33, "b": 33.33}
    assert f.split_researcher_pool(60000, {"l": None, "c": None}, "l") == {"l": 30000.0, "c": 30000.0}
    w = f.split_researcher_pool(60000, {"l": 70, "c": 30}, "l")
    assert w == {"l": 42000.0, "c": 18000.0}
    odd = f.split_researcher_pool(100, {"l": 33.33, "a": 33.33, "b": 33.34}, "l")
    assert sum(Decimal(str(v)) for v in odd.values()) == Decimal("100.00")
    assert f.split_researcher_pool(0.01, {"l": 50, "a": 50}, "l") == {"l": 0.01, "a": 0.0} or \
        sum(Decimal(str(v)) for v in f.split_researcher_pool(0.01, {"l": 50, "a": 50}, "l").values()) == Decimal("0.01")


def test_effective_pcts():
    assert f.effective_researcher_pcts([("a", None), ("b", 50)]) == {"a": 50.0, "b": 50.0}
    assert f.effective_researcher_pcts([("a", 70), ("b", 30)]) == {"a": 70.0, "b": 30.0}
