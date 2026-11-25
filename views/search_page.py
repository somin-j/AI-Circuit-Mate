"""페이지 2. AI 탐색: ① 목표 설정 → ② 탐색 진행 → ③ 결과."""
import streamlit as st

from core.search import search, simulate
from ui.components import steps
from ui.search.compare import render_compare
from ui.search.live import live_run
from ui.search.result import render_result
from ui.search.settings import candidates, settings_panel


def page_search():
    st.title("[AI Circuit Mate]")
    st.caption("목표 성능에 맞는 RC 저역통과필터 소자값을 AI로 탐색합니다. "
               "AI는 이전 실험 결과로 소자값과 차단주파수의 관계를 학습해 다음 후보를 고릅니다.")
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


page_search()
