"""AI 탐색 ② 진행 화면: 탐색을 실행하면서 Trial마다 화면을 갱신한다."""
import time

import streamlit as st

from core.circuit import fmt_si
from core.search import METHODS, SearchResult, run_search
from ui import charts
from ui.components import records_df, steps
from ui.search.settings import candidates

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
