import pytest

from benchmark import SCENARIOS
from circuit import capacitor_candidates, resistor_candidates
from search import METHODS, search

RS, CS = resistor_candidates(), capacitor_candidates()


@pytest.mark.parametrize("target", [t for t, _ in SCENARIOS])
def test_ai_reaches_tolerance_on_all_scenarios(target):
    res = search("ai", target, 2, 20, RS, CS, seed=0)
    assert res.success_trial is not None and res.success_trial <= 10
    assert res.best.error <= 2


@pytest.mark.parametrize("method", list(METHODS))
def test_no_duplicate_trials_and_budget(method):
    res = search(method, 777, 0.01, 20, RS, CS, seed=1)   # 거의 불가능한 목표 → 예산 끝까지
    combos = [(r.r, r.c) for r in res.records]
    assert len(combos) == len(set(combos))
    assert len(res.records) == 20
    assert [r.trial for r in res.records] == list(range(1, 21))


@pytest.mark.parametrize("method", list(METHODS))
def test_same_seed_is_reproducible(method):
    a = search(method, 3400, 2, 20, RS, CS, seed=7)
    b = search(method, 3400, 2, 20, RS, CS, seed=7)
    assert [(r.r, r.c) for r in a.records] == [(r.r, r.c) for r in b.records]


def test_stops_early_on_success():
    res = search("ai", 1000, 2, 20, RS, CS, seed=0)
    assert res.records[-1].success and sum(r.success for r in res.records) == 1


def test_ai_learns_exponents_close_to_theory():
    res = search("ai", 1000, 2, 20, RS, CS, seed=0)
    w = [r.weights for r in res.records if r.weights][-1]
    assert abs(w[1] + 1) < 0.01 and abs(w[2] + 1) < 0.01


def test_works_with_load_resistor():
    res = search("ai", 1000, 2, 20, RS, CS, seed=0, load_r=20e3)
    assert res.best.error < 5
