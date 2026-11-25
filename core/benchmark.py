"""검증 실험: 10개 목표 시나리오에서 AI 탐색 / Optuna TPE / Random Search 비교.

같은 후보(E24 저항 × E12 커패시터), 같은 허용오차(±2%), 같은 최대 횟수(20회)로
seed를 바꿔 가며 반복 실행하고, 결과를 data/benchmark_runs.csv에 저장한다.

실험 조건 2가지
- ideal : 이상적인 무부하 RC 필터 (본 실험)
- load  : 출력에 부하 저항 20 kΩ 연결 (한계 검증: AI의 대리모델 형태와
          실제 관계가 어긋날 때도 동작하는지 확인)

실행:  python -m core.benchmark            (기본 30회 반복)
       python -m core.benchmark --seeds 10 (빠르게 확인)
"""
import argparse
import os

import pandas as pd

from core.circuit import capacitor_candidates, error_rate, resistor_candidates
from core.search import METHODS, search, simulate

# 목표 시나리오 10개: 실습·응용에서 자주 쓰는 저역통과 차단주파수
SCENARIOS = [
    (50, "전원 험(hum) 제거"),
    (100, "저주파 센서 신호"),
    (300, "음성 대역 하한"),
    (500, "저역 오디오"),
    (1000, "실습 기본 예제"),
    (2000, "오디오 톤 필터"),
    (3400, "전화 음성 대역"),
    (5000, "ADC 앞단 안티앨리어싱"),
    (10000, "고역 노이즈 제거"),
    (20000, "가청 대역 상한"),
]

TOLERANCE = 2.0
MAX_TRIALS = 20
CONDITIONS = {"ideal": None, "load": 20e3}
CONDITION_LABELS = {"ideal": "이상적 RC (무부하)", "load": "부하 20 kΩ 연결 (한계 검증)"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "benchmark_runs.csv")


def answer_key(rs, cs, target, load_r):
    """전수 계산 정답지: (최선 오차, 허용오차 만족 조합 수). 검증에만 사용한다."""
    errs = [error_rate(simulate(r, c, load_r), target) for r in rs for c in cs]
    return min(errs), sum(e <= TOLERANCE for e in errs)


def run_benchmark(n_seeds=30, condition="ideal", rs=None, cs=None, progress=None):
    rs = rs or resistor_candidates()
    cs = cs or capacitor_candidates()
    load_r = CONDITIONS[condition]
    rows = []
    total = len(SCENARIOS) * len(METHODS) * n_seeds
    done = 0
    for target, label in SCENARIOS:
        best_err, n_ok = answer_key(rs, cs, target, load_r)
        for method in METHODS:
            for seed in range(n_seeds):
                res = search(method, target, TOLERANCE, MAX_TRIALS, rs, cs, seed=seed,
                             load_r=load_r)
                rows.append({
                    "condition": condition,
                    "target_hz": target,
                    "scenario": label,
                    "method": method,
                    "seed": seed,
                    "success": res.success_trial is not None,
                    "trials_to_success": res.success_trial,
                    "trials_used": len(res.records),
                    "best_error_pct": res.best.error,
                    "elapsed_ms": res.records[-1].elapsed * 1000,
                    "optimal_error_pct": best_err,
                    "valid_combos": n_ok,
                })
                done += 1
                if progress:
                    progress(done / total)
    return pd.DataFrame(rows)


def summarize(df):
    """방법별 요약: 성공률, 평균 도달 횟수, 평균 최선 오차, 평균 실행 시간."""
    g = df.groupby("method")
    out = pd.DataFrame({
        "성공률(%)": g["success"].mean() * 100,
        "평균 도달 Trial": g["trials_to_success"].mean(),
        "최대 도달 Trial": g["trials_to_success"].max(),
        "평균 최선 오차(%)": g["best_error_pct"].mean(),
        "평균 실행시간(ms)": g["elapsed_ms"].mean(),
        "실행 횟수": g.size(),
    })
    out = out.reindex(list(METHODS))
    out.index = [METHODS[m] for m in out.index]
    return out


def per_scenario(df):
    """시나리오 × 방법별 성공률(%)."""
    t = df.pivot_table(index=["target_hz", "scenario", "valid_combos"], columns="method",
                       values="success", aggfunc="mean") * 100
    t = t[list(METHODS)]
    t.columns = [METHODS[m] for m in t.columns]
    return t.reset_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    args = ap.parse_args()

    df = pd.concat([run_benchmark(args.seeds, cond) for cond in CONDITIONS], ignore_index=True)
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    print(f"저장: {DATA_PATH} ({len(df)}회 실행)")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        for cond, label in CONDITION_LABELS.items():
            part = df[df["condition"] == cond]
            print(f"\n=== {label} ===")
            print(summarize(part).round(2))
            print()
            print(per_scenario(part).round(1))
