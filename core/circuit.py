"""RC 저역통과필터 계산 모듈.

표준 소자 후보 생성, 차단주파수·오차율 계산, 주파수 응답, 단위 표기를 담당한다.
탐색 로직(search.py)과 화면(app.py)이 모두 이 모듈의 함수를 사용한다.
"""
import math

# 표준 소자값 시리즈 (1~10 사이 기준값)
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E6 = [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]

SERIES = {"E6": E6, "E12": E12, "E24": E24}


def make_candidates(series, min_value, max_value):
    """기준값 시리즈를 10배씩 늘려가며 min~max 범위의 표준 소자값 목록을 만든다."""
    values = []
    decade = 10 ** math.floor(math.log10(min_value))
    while decade <= max_value:
        for base in series:
            # 1.1 * 1000 = 1100.0000000000002 같은 소수점 오차를 유효숫자 3자리로 정리
            value = float(f"{base * decade:.3g}")
            if min_value <= value <= max_value:
                values.append(value)
        decade *= 10
    return values


def resistor_candidates(min_r=1e3, max_r=100e3, series="E24"):
    return make_candidates(SERIES[series], min_r, max_r)


def capacitor_candidates(min_c=1e-9, max_c=1e-6, series="E12"):
    return make_candidates(SERIES[series], min_c, max_c)


def cutoff_frequency(r, c):
    """RC 저역통과필터 차단주파수 fc = 1 / (2πRC)  [Hz]"""
    return 1 / (2 * math.pi * r * c)


def error_rate(fc, target_fc):
    """목표 대비 오차율 [%]"""
    return abs(fc - target_fc) / target_fc * 100


def gain_db(freq, r, c):
    """RC 저역통과필터의 주파수별 이득 |H(jω)| [dB] = -10·log10(1 + (f/fc)²)"""
    fc = cutoff_frequency(r, c)
    return -10 * math.log10(1 + (freq / fc) ** 2)


def brute_force(rs, cs, target_fc, tolerance):
    """모든 조합을 계산한 정답지. (최선 조합, 최선 오차, 허용오차 만족 조합 수)를 반환한다.

    AI 탐색이 찾은 결과가 실제로 얼마나 좋은지 검증할 때만 사용하고,
    탐색 과정에서는 사용하지 않는다.
    """
    best, best_err, n_ok = None, float("inf"), 0
    for r in rs:
        for c in cs:
            err = error_rate(cutoff_frequency(r, c), target_fc)
            if err <= tolerance:
                n_ok += 1
            if err < best_err:
                best, best_err = (r, c), err
    return best, best_err, n_ok


_PREFIXES = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"),
             (1e-6, "µ"), (1e-9, "n"), (1e-12, "p")]


def fmt_si(value, unit, digits=3):
    """16000, 'Ω' -> '16 kΩ' / 1e-8, 'F' -> '10 nF' 처럼 공학 단위로 표기한다."""
    if value == 0:
        return f"0 {unit}"
    for scale, prefix in _PREFIXES:
        if abs(value) >= scale * 0.999999:
            return f"{float(f'{value / scale:.{digits}g}'):g} {prefix}{unit}"
    scale, prefix = _PREFIXES[-1]
    return f"{float(f'{value / scale:.{digits}g}'):g} {prefix}{unit}"


if __name__ == "__main__":
    rs = resistor_candidates()
    cs = capacitor_candidates()
    print(f"저항 후보 {len(rs)}개: {rs[:5]} ... {rs[-3:]}")
    print(f"커패시터 후보 {len(cs)}개: {cs[:5]} ... {cs[-3:]}")
    print(f"전체 조합 수: {len(rs) * len(cs)}")

    # PPT 예시 검증: R=16kΩ, C=10nF → 약 994.7 Hz, 오차 0.53%
    fc = cutoff_frequency(16e3, 10e-9)
    print(f"\n[예시] R=16kΩ, C=10nF → fc={fc:.1f} Hz, 오차={error_rate(fc, 1000):.2f}%")

    best, best_err, n_ok = brute_force(rs, cs, 1000, 2)
    print(f"[전수 탐색 정답지] 최선 R={fmt_si(best[0], 'Ω')}, C={fmt_si(best[1], 'F')}, "
          f"오차={best_err:.3f}%, ±2% 만족 조합 {n_ok}개")
