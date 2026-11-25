"""화면 공통 스타일(CSS)."""
import streamlit as st

CSS = """
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
"""


def apply_style():
    st.markdown(CSS, unsafe_allow_html=True)
