"""AI 탐색 ① 목표 설정 패널과 설정값으로 표준 소자 후보를 만드는 함수."""
import streamlit as st

from core.benchmark import MAX_TRIALS, TOLERANCE
from core.circuit import SERIES, capacitor_candidates, fmt_si, resistor_candidates
from core.search import METHODS
from ui.components import SCHEMATIC_SVG

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
