import math

from circuit import (brute_force, capacitor_candidates, cutoff_frequency, error_rate, fmt_si,
                     gain_db, resistor_candidates)


def test_candidate_counts_and_values():
    rs = resistor_candidates()
    cs = capacitor_candidates()
    assert len(rs) == 49 and rs[0] == 1000 and rs[-1] == 100_000
    assert len(cs) == 37 and math.isclose(cs[0], 1e-9) and math.isclose(cs[-1], 1e-6)
    assert 16_000 in rs and 1100 in rs           # 소수점 오차 없이 정확한 값
    assert len(set(rs)) == len(rs)


def test_cutoff_and_error_match_ppt_example():
    fc = cutoff_frequency(16e3, 10e-9)
    assert round(fc, 1) == 994.7
    assert round(error_rate(fc, 1000), 2) == 0.53


def test_gain_is_minus_3db_at_cutoff():
    fc = cutoff_frequency(10e3, 10e-9)
    assert math.isclose(gain_db(fc, 10e3, 10e-9), -3.0103, abs_tol=1e-3)


def test_brute_force_answer_key():
    best, err, n_ok = brute_force(resistor_candidates(), capacitor_candidates(), 1000, 2)
    assert round(err, 3) == 0.528 and n_ok == 2


def test_fmt_si():
    assert fmt_si(16_000, "Ω") == "16 kΩ"
    assert fmt_si(10e-9, "F") == "10 nF"
    assert fmt_si(1.2e-9, "F") == "1.2 nF"
    assert fmt_si(1e-6, "F") == "1 µF"
