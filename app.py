"""AI Circuit Mate - 목표 성능에 맞는 소자값을 AI로 탐색.

실행:  streamlit run app.py
"""
import math
import os
import time

import pandas as pd
import streamlit as st

import charts
from benchmark import (CONDITION_LABELS, DATA_PATH, MAX_TRIALS, SCENARIOS, TOLERANCE,
                       per_scenario, run_benchmark, summarize)
from circuit import (SERIES, capacitor_candidates, cutoff_frequency, error_rate, fmt_si,
                     resistor_candidates)
from search import METHODS, SearchResult, run_search, search, simulate

st.set_page_config(page_title="AI Circuit Mate", page_icon="🔌", layout="wide")

# ----------------------------------------------------------------------------
# 공통 스타일·조각
# ----------------------------------------------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 3.5rem; max-width: 1320px;}
.acm-card {background: rgba(128,128,128,0.08); border-radius: 18px; padding: 20px 22px; height: 100%;}
.acm-card.dark {background: #1d1d1f; color: #f5f5f7;}
.acm-card .lbl {font-size: 0.88rem; opacity: 0.65; margin-bottom: 6px;}
.acm-card .big {font-size: 1.45rem; font-weight: 700; line-height: 1.3; margin-bottom: 8px;}
.acm-card .txt {font-size: 0.95rem; opacity: 0.85; line-height: 1.5;}
.acm-hero {font-size: 1.35rem; font-weight: 600; color: #0A6CF0; line-height: 1.5; margin: 6px 0 18px;}
.acm-step {display:inline-block; padding: 6px 14px; border-radius: 999px; margin-right: 6px;
           font-size: 0.9rem; background: rgba(128,128,128,0.12);}
.acm-step.on {background: #0A6CF0; color: white; font-weight: 600;}
.acm-flow {text-align:center; font-size: 1.6rem; opacity: 0.4; padding-top: 48px;}
</style>
""", unsafe_allow_html=True)

SCHEMATIC_SVG = """
<svg viewBox="0 0 320 130" width="100%" style="max-width:320px" xmlns="http://www.w3.org/2000/svg"
     fill="none" stroke="currentColor" stroke-width="2" font-family="sans-serif">
  <circle cx="40" cy="70" r="18"/>
  <path d="M30 70 q5 -10 10 0 q5 10 10 0"/>
  <line x1="40" y1="52" x2="40" y2="30"/><line x1="40" y1="30" x2="95" y2="30"/>
  <polyline points="95,30 102,20 116,40 130,20 144,40 158,20 165,30"/>
  <line x1="165" y1="30" x2="270" y2="30"/>
  <circle cx="210" cy="30" r="3" fill="currentColor"/>
  <line x1="210" y1="30" x2="210" y2="62"/>
  <line x1="190" y1="62" x2="230" y2="62"/><line x1="190" y1="74" x2="230" y2="74"/>
  <line x1="210" y1="74" x2="210" y2="110"/>
  <line x1="40" y1="88" x2="40" y2="110"/><line x1="40" y1="110" x2="270" y2="110"/>
  <circle cx="270" cy="30" r="3" fill="currentColor"/><circle cx="270" cy="110" r="3" fill="currentColor"/>
  <g stroke="none" fill="currentColor" font-size="14">
    <text x="4" y="40">Vin</text><text x="122" y="16">R</text>
    <text x="238" y="72">C</text><text x="278" y="35">Vout</text>
  </g>
</svg>
"""


def card(label, big, text="", dark=False):
    st.markdown(
        f'<div class="acm-card{" dark" if dark else ""}"><div class="lbl">{label}</div>'
        f'<div class="big">{big}</div><div class="txt">{text}</div></div>',
        unsafe_allow_html=True,
    )


def steps(active):
    names = ["① 목표 설정", "② AI 탐색 진행", "③ 탐색 결과"]
    html = "".join(f'<span class="acm-step{" on" if i == active else ""}">{n}</span>'
                   for i, n in enumerate(names, 1))
    st.markdown(html, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_benchmark():
    if not os.path.exists(DATA_PATH):
        return None
    return pd.read_csv(DATA_PATH)


def sci_tex(v):
    """16000 -> '1.6 \\times 10^{4}' 형태의 LaTeX 문자열."""
    exp = math.floor(math.log10(abs(v)))
    mant = float(f"{v / 10 ** exp:.3g}")
    return f"{mant:g}" if exp == 0 else rf"{mant:g} \times 10^{{{exp}}}"


def records_df(records):
    return pd.DataFrame([{
        "Trial": r.trial,
        "R": fmt_si(r.r, "Ω"),
        "C": fmt_si(r.c, "F"),
        "fc (Hz)": round(r.fc, 1),
        "오차 (%)": round(r.error, 2),
        "목표 만족": "✅" if r.success else "",
        "AI 예측 fc (Hz)": round(r.predicted_fc, 1) if r.predicted_fc else None,
        "선택 이유": r.reason,
    } for r in records])


# ----------------------------------------------------------------------------
# 페이지 1. 소개
# ----------------------------------------------------------------------------
def page_home():
    st.title("[AI Circuit Mate]")
    st.subheader("목표 성능에 맞는 소자값을 AI로 탐색")
    st.markdown('<div class="acm-hero">RC 저역통과필터의 소자값을 반복해서 바꿔 보는 시행착오를, '
                '이전 실험 결과로부터 배우는 AI 탐색으로 줄입니다.</div>', unsafe_allow_html=True)

    df = load_benchmark()
    ai_trials, ai_rate, rnd_rate = "≈ 4회", "100%", "8%"
    if df is not None:
        ideal = df[df["condition"] == "ideal"]
        g = ideal.groupby("method")
        ai_trials = f"평균 {g['trials_to_success'].mean()['ai']:.1f}회"
        ai_rate = f"{g['success'].mean()['ai'] * 100:.0f}%"
        rnd_rate = f"{g['success'].mean()['random'] * 100:.0f}%"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("누구를 위해", "정보전기전자<br>공학과 학생", "회로 시뮬레이션 실습을 처음 배우는 학습자")
    with c2:
        card("어떤 문제를", "반복 시행착오", "R·C 값을 바꿔 가며 목표 차단주파수를 맞춰야 함")
    with c3:
        card("AI로 어떻게", "실험 결과로<br>관계를 학습", "학습한 관계로 다음 유망한 표준 R·C 조합을 선택")
    with c4:
        card("검증된 효과", f"{ai_trials} 도달",
             f"10개 목표 × 30회 실험에서 ±2% 도달률 {ai_rate}<br>(같은 조건 Random Search {rnd_rate})", dark=True)

    st.write("")
    st.markdown("### 대상과 문제")
    a, b = st.columns([3, 2])
    with a:
        card("무엇이 불편한가요",
             "값 입력 → 시뮬레이션 → 결과 확인 → 재입력",
             "• 실습 과제 예: <b>\"표준 부품(E24 저항, E12 커패시터)으로 차단주파수 1 kHz, 오차 ±2% 이내의 "
             "RC 저역통과필터를 설계하라\"</b><br>"
             "• 표준값만 쓸 수 있어서 공식으로 계산한 값을 그대로 쓸 수 없고, 반올림하면 오차가 생김<br>"
             "• 1 kHz 목표에서 ±2%를 만족하는 조합은 1,813개 중 <b>단 2개</b> → 감으로 바꾸면 오래 걸림<br>"
             "• 결과만 맞추면 소자값과 성능의 관계를 이해하기 어려움")
    with b:
        # TODO: 실제 설문 문항을 한 줄로 적어 넣으면 근거가 더 구체적이 됩니다.
        card("근거", "78.6%", "출처: 구글 설문조사 (28명 참여)")

    st.write("")
    st.markdown("### 사용 방법")
    s1, s2, s3 = st.columns(3)
    with s1:
        card("STEP 1", "목표 설정", "목표 차단주파수, 허용 오차, 최대 탐색 횟수, 소자 범위를 입력")
    with s2:
        card("STEP 2", "AI 탐색 진행", "AI가 실험 결과로 관계를 학습하며 다음 후보를 고르는 과정을 실시간으로 확인")
    with s3:
        card("STEP 3", "결과 확인·저장", "추천 R·C, 오차 감소 그래프, 주파수 응답, 추천 이유와 학습 포인트 확인 후 CSV 저장")
    st.write("")
    st.page_link(PAGES["search"], label="AI 탐색 시작하기", icon="▶️")


# ----------------------------------------------------------------------------
# 페이지 2. AI 탐색
# ----------------------------------------------------------------------------
R_STOPS = [100.0, 1e3, 10e3, 100e3, 1e6]
C_STOPS = [100e-12, 1e-9, 10e-9, 100e-9, 1e-6, 10e-6]


def settings_panel():
    st.markdown("#### ① 목표 설정")
    st.selectbox("회로 선택", ["RC 저역통과필터 (Low-Pass Filter)"],
                 help="이번 프로토타입은 1차 RC 저역통과필터 하나에 집중합니다.")
    st.markdown(SCHEMATIC_SVG, unsafe_allow_html=True)
    st.caption("고주파 성분은 줄이고 저주파 신호는 통과시키는 기본 필터입니다.  fc = 1 / (2πRC)")

    with st.form("settings"):
        st.markdown("**목표 성능**")
        c1, c2 = st.columns(2)
        target = c1.number_input("목표 차단주파수 fc (Hz)", 1.0, 1_000_000.0, 1000.0, step=100.0)
        tol = c2.number_input("허용 오차 (%)", 0.1, 20.0, TOLERANCE, step=0.5)

        st.markdown("**탐색 범위**")
        r_lo, r_hi = st.select_slider("저항 R 범위", R_STOPS, value=(1e3, 100e3),
                                      format_func=lambda v: fmt_si(v, "Ω"))
        c_lo, c_hi = st.select_slider("커패시터 C 범위", C_STOPS, value=(1e-9, 1e-6),
                                      format_func=lambda v: fmt_si(v, "F"))
        c3, c4 = st.columns(2)
        r_series = c3.selectbox("저항 표준 시리즈", list(SERIES), index=2)
        c_series = c4.selectbox("커패시터 표준 시리즈", list(SERIES), index=1)

        st.markdown("**탐색 옵션**")
        max_trials = st.number_input("최대 탐색 횟수", 5, 50, MAX_TRIALS)
        method = st.radio("탐색 방법", list(METHODS), format_func=METHODS.get, horizontal=True,
                          help="AI 탐색이 기본입니다. 나머지 두 방법은 비교용입니다.")

        with st.expander("고급 설정"):
            seed = st.number_input("Seed (같은 값이면 같은 결과 재현)", 0, 9999, 42)
            delay = st.slider("시연용 표시 속도 (Trial 간 간격, 초)", 0.0, 1.5, 0.4, 0.1)
            use_load = st.checkbox("출력에 부하 저항 연결 (실제 측정 환경)", value=False,
                                   help="다음 단 회로나 측정 장비가 출력에 연결되면 fc가 달라집니다.")
            load_k = st.number_input("부하 저항 (kΩ)", 1.0, 10_000.0, 20.0, disabled=False)

        start = st.form_submit_button("▶ 탐색 시작", type="primary", width="stretch")
        compare = st.form_submit_button("세 방법 비교 실행 (AI · TPE · Random)", width="stretch")

    cfg = dict(target=float(target), tol=float(tol), r_lo=r_lo, r_hi=r_hi, c_lo=c_lo, c_hi=c_hi,
               r_series=r_series, c_series=c_series, max_trials=int(max_trials), method=method,
               seed=int(seed), delay=float(delay), load_r=float(load_k) * 1e3 if use_load else None)
    return cfg, start, compare


def candidates(cfg):
    rs = resistor_candidates(cfg["r_lo"], cfg["r_hi"], cfg["r_series"])
    cs = capacitor_candidates(cfg["c_lo"], cfg["c_hi"], cfg["c_series"])
    return rs, cs


def live_run(cfg, area):
    """탐색을 실행하면서 Trial마다 화면을 갱신한다 (② AI 탐색 진행)."""
    rs, cs = candidates(cfg)
    method = cfg["method"]
    with area.container():
        steps(2)
        st.markdown(f"#### ② {METHODS[method]} 진행 중")
        st.caption("AI가 실험 결과를 바탕으로 다음 소자값 조합을 고르고 있습니다.")
        info = st.empty()
        prog = st.progress(0.0)
        chart_ph = st.empty()
        current = st.empty()
        table_ph = st.empty()

    records = []
    for rec in run_search(method, cfg["target"], cfg["tol"], cfg["max_trials"], rs, cs,
                          cfg["seed"], cfg["load_r"]):
        records.append(rec)
        prog.progress(min(rec.trial / cfg["max_trials"], 1.0),
                      text=f"Trial {rec.trial} / {cfg['max_trials']}")
        with info.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("목표 주파수", f"{cfg['target']:,.0f} Hz")
            m2.metric("허용 오차", f"±{cfg['tol']:g}%")
            m3.metric("현재 탐색", f"{rec.trial} / {cfg['max_trials']}")
            m4.metric("최소 오차", f"{rec.best_error:.2f}%")
        chart_ph.plotly_chart(charts.error_chart(records, cfg["tol"], cfg["max_trials"], method),
                              key=f"live_chart_{rec.trial}")
        current.info(f"**현재 탐색 후보 - Trial #{rec.trial}**  \n"
                     f"R = {fmt_si(rec.r, 'Ω')},  C = {fmt_si(rec.c, 'F')}  →  "
                     f"fc = {rec.fc:,.1f} Hz,  오차 {rec.error:.2f}%  \n"
                     f"선택 이유: {rec.reason}")
        table_ph.dataframe(records_df(records), hide_index=True, key=f"live_table_{rec.trial}")
        if cfg["delay"]:
            time.sleep(cfg["delay"])
    return SearchResult(method, records)


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
            st.markdown(f"**AI가 실험 데이터로 학습한 관계식** (공식을 알려주지 않음)")
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


def render_compare(cfg, results):
    st.markdown("#### 같은 조건에서 세 방법 비교")
    st.caption(f"목표 {cfg['target']:,.0f} Hz, 허용 오차 ±{cfg['tol']:g}%, 최대 {cfg['max_trials']}회, seed {cfg['seed']}")
    st.plotly_chart(charts.compare_chart(results, cfg["tol"], cfg["max_trials"]), key="cmp_chart")
    rows = []
    for m, res in results.items():
        b = res.best
        rows.append({"방법": METHODS[m], "목표 도달 Trial": f"{res.success_trial}회" if res.success_trial else "미도달",
                     "사용한 탐색 횟수": len(res.records), "최선 R": fmt_si(b.r, "Ω"), "최선 C": fmt_si(b.c, "F"),
                     "최선 fc (Hz)": round(b.fc, 1), "최선 오차 (%)": round(b.error, 2)})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("한 번의 실행 결과입니다. seed에 따라 달라질 수 있으므로, 반복 실험 결과는 '검증 결과' 페이지에서 확인하세요.")
    st.divider()


def page_search():
    st.title("AI 소자값 탐색")
    left, right = st.columns([1, 2], gap="large")
    with left:
        cfg, start, compare = settings_panel()

    rs, cs = candidates(cfg)
    if not rs or not cs:
        right.error("탐색 범위에 해당하는 표준 소자값이 없습니다. 범위를 다시 설정하세요.")
        return
    lo, hi = simulate(rs[-1], cs[-1], cfg["load_r"]), simulate(rs[0], cs[0], cfg["load_r"])

    area = right.empty()
    if start or compare:
        if not (lo * 0.98 <= cfg["target"] <= hi * 1.02):
            right.warning(f"이 범위로 만들 수 있는 fc는 약 {lo:,.1f} ~ {hi:,.1f} Hz입니다. "
                          "목표가 범위 밖이라 목표 도달이 어려울 수 있습니다.")
        if compare:
            ai = live_run({**cfg, "method": "ai"}, area)
            results = {"ai": ai}
            with right:
                with st.spinner("Optuna TPE와 Random Search를 같은 조건으로 실행하는 중..."):
                    for m in ("tpe", "random"):
                        results[m] = search(m, cfg["target"], cfg["tol"], cfg["max_trials"], rs, cs,
                                            cfg["seed"], cfg["load_r"])
            st.session_state["run"] = {"cfg": {**cfg, "method": "ai"}, "result": ai, "compare": results}
        else:
            res = live_run(cfg, area)
            st.session_state["run"] = {"cfg": cfg, "result": res, "compare": None}
        st.rerun()

    run = st.session_state.get("run")
    with area.container():
        if run is None:
            steps(1)
            st.markdown("#### 시작하기")
            st.markdown(
                "왼쪽에서 목표 성능을 입력하고 **▶ 탐색 시작**을 누르세요.\n\n"
                f"- 현재 설정의 표준 소자 후보: 저항 {len(rs)}개 × 커패시터 {len(cs)}개 = **{len(rs) * len(cs):,}개 조합**\n"
                f"- 이 범위로 만들 수 있는 차단주파수: 약 {lo:,.1f} Hz ~ {hi:,.1f} Hz\n"
                "- AI는 처음 3번은 관계를 배우기 위한 탐색 실험을 하고, 이후에는 학습한 관계로 다음 후보를 고릅니다.\n"
                "- **세 방법 비교 실행**을 누르면 같은 조건에서 AI 탐색 / Optuna TPE / Random Search를 비교합니다."
            )
            st.info("AI는 fc = 1/(2πRC) 공식을 모르는 상태에서, 시뮬레이션 결과만 보고 다음 실험을 고릅니다.")
        else:
            if run["compare"]:
                render_compare(run["cfg"], run["compare"])
            render_result(run["cfg"], run["result"])


# ----------------------------------------------------------------------------
# 페이지 3. 검증 결과
# ----------------------------------------------------------------------------
def page_validation():
    st.title("검증 결과")
    st.markdown("AI를 썼다는 주장보다, **같은 조건에서 탐색 효율이 실제로 개선되는지**를 수치로 확인했습니다.")

    with st.expander("실험 설계", expanded=False):
        st.markdown(
            f"- **목표 시나리오 10개**: " + ", ".join(f"{t:,} Hz({lbl})" for t, lbl in SCENARIOS) + "\n"
            f"- **후보**: E24 저항(1 kΩ~100 kΩ, 49개) × E12 커패시터(1 nF~1 µF, 37개) = 1,813개 조합\n"
            f"- **성공 기준**: 허용 오차 ±{TOLERANCE:g}% 이내 조합을 최대 {MAX_TRIALS}회 안에 찾기\n"
            "- **비교 방법**: AI 탐색(대리모델) / Optuna TPE(예선 계획안) / Random Search\n"
            "- **반복**: 시나리오 × 방법마다 seed 0~29로 30회 → 조건당 900회 실행\n"
            "- **조건 2가지**: 이상적인 RC(본 실험), 출력에 부하 20 kΩ 연결(한계 검증)\n"
            "- **공정성**: 세 방법 모두 같은 조합을 두 번 실험하지 않고, 목표 도달 시 즉시 멈춤\n"
            "- 재현 방법: `python benchmark.py`"
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


# ----------------------------------------------------------------------------
# 페이지 4. AI 작동 원리
# ----------------------------------------------------------------------------
def page_how():
    st.title("AI 작동 원리")
    st.markdown("AI의 역할은 소자값을 공식으로 계산하는 것이 아니라 “**다음에 실험할 유망한 후보를 고르는 것**”으로 제한했습니다.")

    c1, a1, c2, a2, c3 = st.columns([4, 1, 4, 1, 4])
    with c1:
        card("입력 (AI가 받는 것)", "목표와 실험 기록",
             "• 목표 차단주파수, 허용 오차, 최대 횟수<br>• 표준 소자 후보 (E 시리즈)<br>"
             "• 지금까지 실험한 (R, C) → 시뮬레이션 fc 결과")
    a1.markdown('<div class="acm-flow">→</div>', unsafe_allow_html=True)
    with c2:
        card("AI 탐색 (AI가 판단하는 것)", "관계 학습 → 다음 후보 선택",
             "① 실험 기록으로 대리모델 학습<br>&nbsp;&nbsp;&nbsp;ln fc ≈ w0 + wR·ln R + wC·ln C<br>"
             "② 아직 안 해 본 모든 표준 조합의 fc 예측<br>③ 목표에 가장 가깝다고 예측된 조합을 다음 실험으로 선택",
             dark=True)
    a2.markdown('<div class="acm-flow">→</div>', unsafe_allow_html=True)
    with c3:
        card("출력 (AI가 만드는 것)", "추천 R·C와 근거",
             "• 추천 R·C, 예상 차단주파수, 오차율<br>• Trial별 오차 감소 그래프<br>"
             "• 학습한 관계식 (지수 wR, wC)")

    st.write("")
    st.markdown("### 탐색 한 번(Trial)의 흐름")
    st.markdown(
        "1. **처음 3번**: 관계를 배우기 위해 서로 다른 조합을 무작위로 실험합니다.\n"
        "2. **학습**: 실험 결과로 대리모델의 계수 w0, wR, wC를 가중 최소제곱법으로 학습합니다. "
        "목표에 가까웠던 실험일수록 큰 가중치를 줘서, 모델이 조금 틀려도 목표 근처에서는 정확해지도록 했습니다.\n"
        "3. **선택**: 학습한 모델로 아직 실험하지 않은 모든 표준 조합의 fc를 예측하고, 목표에 가장 가까운 조합을 고릅니다.\n"
        "4. **실험**: 고른 조합을 시뮬레이터로 계산(현재는 RC 공식, 추후 ngspice로 교체 가능)하고 결과를 기록에 추가합니다.\n"
        "5. 허용 오차를 만족하면 멈추고, 아니면 2번으로 돌아갑니다."
    )

    st.markdown("### 무엇을 라이브러리가 하고, 무엇을 직접 구현했나")
    st.markdown(
        "| 구분 | 역할 |\n|---|---|\n"
        "| **Optuna** (라이브러리) | 실험 기록 관리(Study), ask/tell 탐색 루프, 비교군 TPE 샘플러 |\n"
        "| **직접 구현** | E 시리즈 표준 후보 생성, 회로 대리모델 샘플러(Optuna 커스텀 샘플러), 가중 학습, "
        "중복 실험 방지·조기 종료, 정답지(전수 계산) 검증, 10개 시나리오 비교 실험, 시각화 |\n"
        "| **Streamlit · Plotly** (라이브러리) | 웹 화면과 그래프 표시 |"
    )

    st.markdown("### 예선 이후 바뀐 점")
    st.markdown(
        "| | 예선 계획 | 본선 구현 | 바꾼 이유 |\n|---|---|---|---|\n"
        "| 탐색 방법 | Optuna 기본 TPE | Optuna + 회로 대리모델 샘플러 | 검증 결과 TPE 성공률(약 12%)이 Random(약 8%)과 큰 차이가 없음 |\n"
        "| 비교 대상 | Random Search | Random Search + TPE(예선안) | 방법을 바꾼 근거를 같은 조건의 수치로 보여 주기 위해 |\n"
        "| 검증 | 10개 목표 | 10개 목표 × 30회 반복 + 부하 조건 한계 검증 | 한 번의 결과는 우연일 수 있어서 |\n"
        "| 결과 표시 | 추천값 | 추천값 + 전수 계산 정답지 비교 | 'AI가 찾은 값이 실제로 얼마나 좋은지' 확인 가능하도록 |"
    )

    st.markdown("### 자주 받을 질문")
    with st.expander("공식 fc = 1/(2πRC)로 바로 계산하면 되지 않나요?"):
        st.markdown(
            "이상적인 1차 RC 필터라면 공식으로 C를 계산하고 표준값으로 반올림한 뒤 주변 값을 확인하는 방법도 가능합니다. "
            "이 프로젝트가 다르게 접근한 이유는 두 가지입니다.\n\n"
            "1. **학습 도구로서**: 결과만 알려주면 '왜 그 값인지'를 이해하기 어렵습니다. AI가 실험 데이터에서 "
            "'R이나 C를 2배 하면 fc가 절반'이라는 관계(지수 -1)를 찾아가는 과정을 함께 보여 줍니다.\n"
            "2. **확장성**: 탐색 코드는 공식을 사용하지 않고 시뮬레이터 결과만 사용합니다. 부하 저항이 연결된 조건처럼 "
            "공식이 달라지는 경우에도 코드 변경 없이 동작하며, 검증 페이지의 한계 검증이 그 근거입니다."
        )
    with st.expander("AI가 항상 최적해를 찾나요?"):
        st.markdown(
            "보장하지 않습니다. 그래서 결과를 '최적값'이 아니라 '**제한된 횟수에서 찾은 최선 후보**'로 표시하고, "
            "탐색이 끝난 뒤 전수 계산 정답지와 비교해 실제 오차를 함께 보여 줍니다. "
            "부하가 연결된 조건에서는 20회 안에 찾지 못하는 경우가 약 15% 있었습니다."
        )
    with st.expander("왜 딥러닝이 아닌가요?"):
        st.markdown(
            "실험 한 번이 비싼(시뮬레이션·측정) 상황에서 20회 이내의 적은 데이터로 판단해야 하므로, "
            "대량 학습 데이터가 필요한 딥러닝보다 적은 데이터로 학습하는 대리모델 기반 탐색이 적합하다고 판단했습니다. "
            "미리 수집한 학습 데이터 없이, 탐색 중에 생성되는 실험 결과만 사용합니다."
        )

    st.markdown("### 한계")
    st.markdown(
        "- 현재는 **1차 RC 저역통과필터 한 종류**만 지원합니다.\n"
        "- 시뮬레이터는 RC 공식 계산이며, ngspice 연동은 아직 하지 않았습니다.\n"
        "- 대리모델은 '소자값의 거듭제곱 꼴' 관계를 가정합니다. 이 가정에서 크게 벗어나는 회로에서는 성능이 떨어질 수 있습니다.\n"
        "- 실제 부품의 공차(예: 저항 ±5%, 커패시터 ±10%)는 고려하지 않았습니다.\n"
        "- 사용 데이터는 프로그램이 실행 중에 생성한 시뮬레이션 결과뿐이며, 개인정보는 수집하지 않습니다."
    )


# ----------------------------------------------------------------------------
# 내비게이션
# ----------------------------------------------------------------------------
PAGES = {
    "home": st.Page(page_home, title="소개", icon="🏠", default=True),
    "search": st.Page(page_search, title="AI 탐색", icon="🔍", url_path="search"),
    "validation": st.Page(page_validation, title="검증 결과", icon="📊", url_path="validation"),
    "how": st.Page(page_how, title="AI 작동 원리", icon="🧠", url_path="how"),
}

st.navigation(list(PAGES.values()), position="top").run()
