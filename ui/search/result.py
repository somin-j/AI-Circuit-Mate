"""AI 탐색 ③ 결과 화면: 추천 값, 추천 이유, 수식, 그래프, 저장."""
import math

import streamlit as st

from core.circuit import error_rate, fmt_si
from core.search import METHODS, simulate
from ui import charts
from ui.components import records_df, sci_tex, steps
from ui.search.settings import candidates

def render_result(cfg, res):
    """③ 탐색 결과."""
    rs, cs = candidates(cfg)
    best = res.best
    hit = res.success_trial
    method = res.method
    total = len(rs) * len(cs)

    steps(3)
    st.markdown(f"#### ③ 탐색 결과 - {METHODS[method]}")
    if hit:
        st.success(f"**목표 조건을 만족했습니다!** {hit}번째 탐색에서 허용 오차 ±{cfg['tol']:g}% 이내 조합을 찾았습니다.")
    else:
        st.warning(f"{cfg['max_trials']}회 안에 허용 오차 ±{cfg['tol']:g}%를 만족하는 조합을 찾지 못했습니다. "
                   "찾은 후보 중 가장 좋은 조합을 보여 줍니다.")

    m = st.columns(3)
    m[0].metric("추천 저항 R", fmt_si(best.r, "Ω"), border=True)
    m[1].metric("추천 커패시터 C", fmt_si(best.c, "F"), border=True)
    m[2].metric("차단주파수 (시뮬레이션)", f"{best.fc:,.1f} Hz", border=True)
    m = st.columns(3)
    m[0].metric("목표 주파수", f"{cfg['target']:,.0f} Hz")
    m[1].metric("오차", f"{best.error:.2f}%")
    m[2].metric("탐색 횟수", f"{len(res.records)}회")

    # 정답지(전수 계산)는 탐색이 끝난 뒤 결과 검증에만 사용한다.
    errs = [error_rate(simulate(r, c, cfg["load_r"]), cfg["target"]) for r in rs for c in cs]
    opt_err = min(errs)
    n_ok = sum(e <= cfg["tol"] for e in errs)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("##### 💡 추천 이유")
        reasons = [
            f"**목표에 가장 근접한 성능** - 실험한 {len(res.records)}개 조합 중 R = {fmt_si(best.r, 'Ω')}, "
            f"C = {fmt_si(best.c, 'F')}가 fc = {best.fc:,.1f} Hz로 목표({cfg['target']:,.0f} Hz)에 가장 가깝습니다.",
            f"**허용 오차 {'만족' if best.error <= cfg['tol'] else '미달'}** - 오차 {best.error:.2f}%"
            f"{' ≤ ' if best.error <= cfg['tol'] else ' > '}허용 오차 {cfg['tol']:g}%",
            f"**효율적 탐색** - 가능한 표준 조합 {total:,}개 중 {len(res.records)}개({len(res.records) / total * 100:.1f}%)만 실험했습니다.",
            f"**정답지와 비교** - 모든 조합을 계산해 보면 최선 오차는 {opt_err:.2f}%이고, "
            f"±{cfg['tol']:g}%를 만족하는 조합은 {total:,}개 중 {n_ok}개입니다. "
            + ("찾은 조합이 이론상 최선값과 같습니다." if abs(best.error - opt_err) < 1e-9
               else f"찾은 조합은 최선값보다 {best.error - opt_err:.2f}%p 큽니다."),
        ]
        if n_ok == 0:
            reasons.append("**참고** - 이 범위·시리즈에서는 허용 오차를 만족하는 조합이 존재하지 않습니다. "
                           "범위를 넓히거나 더 촘촘한 시리즈(E24)를 선택해 보세요.")
        for i, t in enumerate(reasons, 1):
            st.markdown(f"{i}. {t}")
        if cfg["load_r"]:
            st.caption(f"※ 부하 저항 {fmt_si(cfg['load_r'], 'Ω')}이 연결된 조건으로 계산했습니다.")

    with right:
        st.markdown("##### 📐 회로 원리 및 수식")
        st.latex(r"f_c = \frac{1}{2\pi RC}")
        if not cfg["load_r"]:
            st.latex(rf"= \frac{{1}}{{2\pi \times ({sci_tex(best.r)}) \times ({sci_tex(best.c)})}}")
            st.latex(rf"\approx {best.fc:,.1f}\ \mathrm{{Hz}}")
        else:
            st.latex(r"f_c = \frac{1}{2\pi (R \parallel R_L) C}")
        st.info("**학습 포인트** - fc는 R과 C의 곱에 반비례합니다. R이나 C를 2배로 키우면 fc는 절반이 됩니다. "
                "그래서 R·C 곱이 같은 16 kΩ·10 nF와 1.6 kΩ·100 nF는 같은 fc를 가집니다.")
        w = next((r.weights for r in reversed(res.records) if r.weights), None)
        if w:
            st.markdown("**AI가 실험 데이터로 학습한 관계식** (공식을 알려주지 않음)")
            st.latex(rf"f_c \approx {math.exp(w[0]):.3g} \times R^{{{w[1]:.3f}}} \times C^{{{w[2]:.3f}}}")
            n_explore = len([r for r in res.records if not r.weights])
            if abs(w[1] + 1) < 0.05 and abs(w[2] + 1) < 0.05:
                st.caption(f"이론식은 0.159 × R⁻¹ × C⁻¹ 입니다. AI는 {n_explore}번의 탐색 실험만으로 "
                           "지수가 -1에 가깝다는 관계를 스스로 찾아냈습니다.")
            else:
                st.caption("무부하 RC의 이론식은 0.159 × R⁻¹ × C⁻¹ 입니다. 학습한 지수가 -1과 다른 것은 "
                           "부하 저항처럼 단순한 RC 공식과 다른 조건이 있기 때문이며, AI는 목표 근처에서 "
                           "실제 관계에 맞도록 근사한 식을 학습한 것입니다.")

    tabs = st.tabs(["📉 오차 변화", "🗺️ 탐색 공간 지도", "📈 주파수 응답", "🧠 AI 학습 과정", "📋 탐색 기록"])
    with tabs[0]:
        st.plotly_chart(charts.error_chart(res.records, cfg["tol"], cfg["max_trials"], method,
                                           title="탐색 과정 요약 - 오차 변화"), key="res_err")
    with tabs[1]:
        st.plotly_chart(charts.search_space_chart(rs, cs, cfg["target"], res.records, cfg["load_r"], method),
                        key="res_space")
        st.caption("진한 칸이 목표에 가까운 조합입니다. 대각선 띠 모양은 'R·C 곱이 같으면 fc가 같다'는 관계를 보여 줍니다. "
                   "AI는 첫 탐색 실험 뒤 바로 이 띠 위의 조합을 고릅니다.")
    with tabs[2]:
        st.plotly_chart(charts.bode_chart(best.r, best.c, cfg["target"], cfg["load_r"]), key="res_bode")
        st.caption("차단주파수는 출력이 통과 대역보다 3 dB(약 70.7%) 줄어드는 주파수입니다.")
    with tabs[3]:
        if any(r.weights for r in res.records):
            st.plotly_chart(charts.weights_chart(res.records), key="res_w")
            st.caption("각 Trial의 후보를 고를 때 AI가 사용한 관계식의 지수입니다. 실험이 쌓일수록 이론값 -1에 가까워집니다.")
        else:
            st.write("이 탐색 방법은 관계식을 학습하지 않습니다. (AI 탐색에서만 표시)")
    with tabs[4]:
        st.dataframe(records_df(res.records), hide_index=True)

    df = records_df(res.records)
    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button("💾 결과 저장 (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"ai_circuit_mate_{cfg['target']:.0f}Hz.csv", mime="text/csv",
                       width="stretch")
    if d2.button("↺ 다시 탐색하기", width="stretch"):
        st.session_state.pop("run", None)
        st.rerun()
