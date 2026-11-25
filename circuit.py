import math

# 표준 소자값 시리즈 (1~10 사이 기준값)
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


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


def resistor_candidates(min_r=1e3, max_r=100e3):
    return make_candidates(E24, min_r, max_r)


def capacitor_candidates(min_c=1e-9, max_c=1e-6):
    return make_candidates(E12, min_c, max_c)


def cutoff_frequency(r, c):
    """RC 저역통과필터 차단주파수 fc = 1 / (2πRC)  [Hz]"""
    return 1 / (2 * math.pi * r * c)


def error_rate(fc, target_fc):
    """목표 대비 오차율 [%]"""
    return abs(fc - target_fc) / target_fc * 100


if __name__ == "__main__":
    rs = resistor_candidates()
    cs = capacitor_candidates()
    print(f"저항 후보 {len(rs)}개: {rs[:5]} ... {rs[-3:]}")
    print(f"커패시터 후보 {len(cs)}개: {cs[:5]} ... {cs[-3:]}")
    print(f"전체 조합 수: {len(rs) * len(cs)}")

    # PPT 예시 검증: R=16kΩ, C=10nF → 약 994.7 Hz, 오차 0.53%
    fc = cutoff_frequency(16e3, 10e-9)
    print(f"\n[예시] R=16kΩ, C=10nF → fc={fc:.1f} Hz, 오차={error_rate(fc, 1000):.2f}%")

    # 정답지: 모든 조합을 다 계산했을 때의 최선값 (AI 탐색 결과 검증용)
    target = 1000
    best = min(((r, c) for r in rs for c in cs),
               key=lambda rc: error_rate(cutoff_frequency(*rc), target))
    best_fc = cutoff_frequency(*best)
    print(f"[전수 탐색 최선] R={best[0]:.0f}Ω, C={best[1]:.2e}F → "
          f"fc={best_fc:.1f} Hz, 오차={error_rate(best_fc, target):.3f}%")