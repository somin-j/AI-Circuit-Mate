"""페이지 3. 검증 결과: 10개 시나리오 비교 실험과 한계 검증."""
import pandas as pd
import streamlit as st

from core.benchmark import (CONDITION_LABELS, MAX_TRIALS, SCENARIOS, TOLERANCE, per_scenario,
                            run_benchmark, summarize)
from ui import charts
from ui.components import load_benchmark


def page_validation():
    st.title("검증 결과")
    st.markdown("AI를 썼다는 주장보다, **같은 조건에서 탐색 효율이 실제로 개선되는지**를 수치로 확인했습니다.")

    with st.expander("실험 설계", expanded=False):
        st.markdown(
            "- **목표 시나리오 10개**: " + ", ".join(f"{t:,} Hz({lbl})" for t, lbl in SCENARIOS) + "\n"
            f"- **후보**: E24 저항(1 kΩ~100 kΩ, 49개) × E12 커패시터(1 nF~1 µF, 37개) = 1,813개 조합\n"
            f"- **성공 기준**: 허용 오차 ±{TOLERANCE:g}% 이내 조합을 최대 {MAX_TRIALS}회 안에 찾기\n"
            "- **비교 방법**: AI 탐색(대리모델) / Optuna TPE(예선 계획안) / Random Search\n"
            "- **반복**: 시나리오 × 방법마다 seed 0~29로 30회 → 조건당 900회 실행\n"
            "- **조건 2가지**: 이상적인 RC(본 실험), 출력에 부하 20 kΩ 연결(한계 검증)\n"
            "- **공정성**: 세 방법 모두 같은 조합을 두 번 실험하지 않고, 목표 도달 시 즉시 멈춤\n"
            "- 재현 방법: `python -m core.benchmark`"
        )

    df = st.session_state.get("bench_df")
    if df is None:
        df = load_benchmark()
    if df is None:
        st.warning("저장된 검증 결과가 없습니다. 아래에서 실험을 실행하세요.")
    else:
        tabs = st.tabs([CONDITION_LABELS[c] for c in CONDITION_LABELS])
        for tab, cond in zip(tabs, CONDITION_LABELS):
            with tab:
                part = df[df["condition"] == cond]
                if part.empty:
                    st.write("이 조건의 결과가 없습니다.")
                    continue
                summ = summarize(part)
                names = list(summ.index)
                k = st.columns(4)
                k[0].metric(f"{names[0]} 성공률", f"{summ.iloc[0]['성공률(%)']:.0f}%")
                k[1].metric(f"{names[0]} 평균 도달", f"{summ.iloc[0]['평균 도달 Trial']:.1f}회")
                k[2].metric(f"{names[1]} 성공률", f"{summ.iloc[1]['성공률(%)']:.0f}%")
                k[3].metric(f"{names[2]} 성공률", f"{summ.iloc[2]['성공률(%)']:.0f}%")
                st.dataframe(summ.round(2))
                c1, c2 = st.columns(2)
                table = per_scenario(part)
                c1.plotly_chart(charts.benchmark_success_chart(table), key=f"bs_{cond}")
                c2.plotly_chart(charts.benchmark_curve_chart(part, MAX_TRIALS), key=f"bc_{cond}")
                st.markdown("**시나리오별 성공률 (%)** - `valid_combos` = 1,813개 중 ±2%를 만족하는 조합 수 (정답지)")
                st.dataframe(table.round(1), hide_index=True)

        st.markdown("### 결과 해석 (과장 없이)")
        st.markdown(
            "1. **문제 자체가 어렵습니다.** 시나리오마다 ±2%를 만족하는 조합은 1,813개 중 2~16개뿐이라, "
            "Random Search는 20회 안에 대부분 실패합니다(성공률 약 8%).\n"
            "2. **예선에서 계획한 Optuna TPE는 기대만큼 좋지 않았습니다.** 범용 TPE는 'R·C 곱이 같으면 fc가 같다'는 "
            "구조를 20회 안에 배우지 못해 Random과 비슷한 수준(약 12%)이었습니다. 그래서 본선에서는 탐색 방법을 보완했습니다.\n"
            "3. **AI 탐색(대리모델)은 이상적인 RC에서 모든 실행이 4회 이내에 도달했습니다.** 단, 이 조건에서는 실제 관계가 "
            "AI 모델의 형태(로그 공간 선형)와 정확히 일치하므로 가장 유리한 조건입니다.\n"
            "4. **모델과 실제가 어긋나는 조건(부하 20 kΩ)에서는 성능이 떨어집니다.** 성공률 약 85%, 평균 약 9회로 "
            "여전히 비교 방법보다 높지만, 일부 시나리오(예: 2 kHz)에서는 63%까지 내려갑니다.\n"
            "5. 결과 화면에는 '최적값' 대신 '**제한된 횟수에서 찾은 최선 후보**'로 표시하고, 전수 계산 정답지와 실제 오차를 함께 보여 줍니다."
        )

    st.markdown("### 직접 다시 실행해 보기")
    c1, c2 = st.columns([1, 3])
    n = c1.number_input("반복 횟수 (seed 수)", 3, 30, 10)
    if c1.button("검증 실험 실행", type="primary"):
        bar = c2.progress(0.0, text="실행 중...")
        parts = []
        conds = list(CONDITION_LABELS)
        for i, cond in enumerate(conds):
            parts.append(run_benchmark(int(n), cond, progress=lambda p, i=i: bar.progress(
                (i + p) / len(conds), text=f"{CONDITION_LABELS[cond]} 실행 중... {p * 100:.0f}%")))
        st.session_state["bench_df"] = pd.concat(parts, ignore_index=True)
        st.rerun()
    if st.session_state.get("bench_df") is not None:
        c2.caption("현재 화면은 방금 실행한 결과입니다. (저장된 파일은 바꾸지 않음)")


page_validation()
