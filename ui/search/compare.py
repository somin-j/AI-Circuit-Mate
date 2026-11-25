"""세 방법(AI · TPE · Random) 비교 결과 화면."""
import pandas as pd
import streamlit as st

from core.circuit import fmt_si
from core.search import METHODS
from ui import charts

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
