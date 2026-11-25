"""페이지 1. 소개: 대상과 문제, 사용 방법, 검증된 효과 요약."""
import streamlit as st

from ui.components import card, load_benchmark


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
    st.page_link("views/search_page.py", label="AI 탐색 시작하기", icon="▶️")


page_home()
