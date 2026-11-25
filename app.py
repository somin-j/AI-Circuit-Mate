"""AI Circuit Mate - 목표 성능에 맞는 소자값을 AI로 탐색.

실행:  streamlit run app.py

폴더 구성
  core/   계산과 탐색 로직 (화면과 무관)
  ui/     화면 부품, 그래프, 스타일
  views/  페이지 3개 (각 파일이 한 페이지)
"""
import streamlit as st

from ui.style import apply_style

st.set_page_config(page_title="AI Circuit Mate", page_icon="🔌", layout="wide")
apply_style()

pages = [
    st.Page("views/search_page.py", title="AI 탐색", icon="🔍", default=True),
    st.Page("views/validation_page.py", title="검증 결과", icon="📊", url_path="validation"),
    st.Page("views/how_page.py", title="AI 작동 원리", icon="🧠", url_path="how"),
]
st.navigation(pages, position="top").run()
