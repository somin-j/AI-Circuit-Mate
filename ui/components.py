"""여러 페이지에서 함께 쓰는 화면 부품: 카드, 단계 표시, 회로도, 표·수식 변환."""
import math
import os

import pandas as pd
import streamlit as st

from core.benchmark import DATA_PATH
from core.circuit import fmt_si

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
