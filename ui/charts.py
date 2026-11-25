"""Plotly 그래프 모음 (화면 표시용)."""
import math

import numpy as np
import plotly.graph_objects as go

from core.circuit import error_rate, fmt_si, gain_db
from core.search import METHODS, simulate

COLORS = {"ai": "#0A6CF0", "tpe": "#E8890C", "random": "#8E8E93"}
TOL_COLOR = "#E5484D"
GRID = "rgba(128,128,128,0.18)"


def _layout(fig, height=340, **kw):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        hovermode="x unified", font=dict(size=13), **kw,
    )
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def _err_floor(v):
    """로그축에 0을 그릴 수 없으므로 아주 작은 값으로 바꾼다."""
    return max(v, 1e-3)


def error_chart(records, tolerance, max_trials, method="ai", title="탐색 과정 - 오차 변화"):
    """Trial별 오차(점)와 지금까지의 최소 오차(선)."""
    fig = go.Figure()
    x = [r.trial for r in records]
    fig.add_trace(go.Scatter(
        x=x, y=[_err_floor(r.error) for r in records], mode="markers", name="이번 Trial 오차",
        marker=dict(size=9, color=COLORS[method], opacity=0.45),
        hovertemplate="Trial %{x}: %{y:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=[_err_floor(r.best_error) for r in records], mode="lines+markers",
        name="최소 오차", line=dict(color=COLORS[method], width=3), marker=dict(size=6),
        hovertemplate="최소 %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=tolerance, line=dict(color=TOL_COLOR, dash="dash"),
                  annotation_text=f"허용 오차 {tolerance:g}%", annotation_position="top left")
    hit = next((r for r in records if r.success), None)
    if hit:
        fig.add_annotation(x=hit.trial, y=math.log10(_err_floor(hit.error)),
                           text=f"목표 도달<br>{hit.error:.2f}%", showarrow=True, arrowhead=2,
                           ax=40, ay=-40, bgcolor="rgba(46,160,67,0.15)")
    fig.update_xaxes(title="탐색 횟수 (Trial)", range=[0.5, max_trials + 0.5], dtick=1 if max_trials <= 30 else None)
    fig.update_yaxes(title="오차 (%) - 로그", type="log", dtick=1)
    return _layout(fig, title=title)


def compare_chart(results, tolerance, max_trials):
    """방법별 '지금까지의 최소 오차' 비교."""
    fig = go.Figure()
    for method, res in results.items():
        recs = res.records
        fig.add_trace(go.Scatter(
            x=[r.trial for r in recs], y=[_err_floor(r.best_error) for r in recs],
            mode="lines+markers", name=METHODS[method],
            line=dict(color=COLORS[method], width=3 if method == "ai" else 2),
            hovertemplate=METHODS[method] + ": %{y:.2f}%<extra></extra>",
        ))
    fig.add_hline(y=tolerance, line=dict(color=TOL_COLOR, dash="dash"),
                  annotation_text=f"허용 오차 {tolerance:g}%", annotation_position="top left")
    fig.update_xaxes(title="탐색 횟수 (Trial)", range=[0.5, max_trials + 0.5])
    fig.update_yaxes(title="지금까지의 최소 오차 (%) - 로그", type="log", dtick=1)
    return _layout(fig, title="같은 조건에서 세 방법 비교")


def search_space_chart(rs, cs, target_fc, records, load_r=None, method="ai"):
    """전체 후보 공간(R×C)의 오차 지도 위에 실제로 실험한 조합을 표시."""
    z = np.array([[math.log10(max(error_rate(simulate(r, c, load_r), target_fc), 0.01))
                   for r in rs] for c in cs])
    xl = [fmt_si(r, "Ω") for r in rs]
    yl = [fmt_si(c, "F") for c in cs]
    fig = go.Figure(go.Heatmap(
        z=z, x=xl, y=yl, colorscale="Blues_r", zmin=-1, zmax=2.5,
        colorbar=dict(title="오차", tickvals=[-1, 0, 1, 2], ticktext=["0.1%", "1%", "10%", "100%"]),
        hovertemplate="R=%{x}, C=%{y}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[fmt_si(r.r, "Ω") for r in records], y=[fmt_si(r.c, "F") for r in records],
        mode="markers+text", text=[str(r.trial) for r in records], textposition="top center",
        textfont=dict(color="#111", size=12),
        marker=dict(size=12, color=["#2EA043" if r.success else COLORS[method] for r in records],
                    line=dict(color="white", width=1.5)),
        name="실험한 조합", hovertemplate="Trial %{text}<extra></extra>",
    ))
    fig.update_xaxes(title="저항 R", type="category", tickangle=-45, nticks=12)
    fig.update_yaxes(title="커패시터 C", type="category", nticks=12)
    _layout(fig, height=460, title="탐색 공간 - 진할수록 목표에 가까운 조합 (숫자 = Trial 순서)")
    fig.update_layout(hovermode="closest", showlegend=False)
    return fig


def bode_chart(r, c, target_fc, load_r=None):
    """추천 조합의 주파수 응답 (크기)."""
    fc = simulate(r, c, load_r)
    reff = r * load_r / (r + load_r) if load_r else r
    dc = 20 * math.log10(load_r / (r + load_r)) if load_r else 0.0
    f = np.logspace(math.log10(fc) - 2, math.log10(fc) + 2, 300)
    g = [dc + gain_db(x, reff, c) for x in f]
    fig = go.Figure(go.Scatter(x=f, y=g, mode="lines", name="추천 조합",
                               line=dict(color=COLORS["ai"], width=3),
                               hovertemplate="%{x:,.0f} Hz: %{y:.1f} dB<extra></extra>"))
    fig.add_vline(x=target_fc, line=dict(color=TOL_COLOR, dash="dash"),
                  annotation_text=f"목표 {target_fc:,.0f} Hz", annotation_position="top left")
    fig.add_trace(go.Scatter(x=[fc], y=[dc - 3.0103], mode="markers+text", name="차단주파수 (-3 dB)",
                             marker=dict(size=11, color=COLORS["ai"]),
                             text=[f"{fc:,.1f} Hz (-3 dB)"], textposition="bottom left"))
    fig.update_xaxes(title="주파수 (Hz) - 로그", type="log", dtick=1)
    fig.update_yaxes(title="이득 (dB)")
    return _layout(fig, title="주파수 응답 그래프 (추천 조합)")


def benchmark_success_chart(table):
    """시나리오별 성공률 (방법별 막대)."""
    fig = go.Figure()
    xs = [f"{t:,} Hz" for t in table["target_hz"]]
    for method, name in METHODS.items():
        fig.add_trace(go.Bar(x=xs, y=table[name], name=name, marker_color=COLORS[method],
                             hovertemplate=name + ": %{y:.0f}%<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="목표 차단주파수 시나리오")
    fig.update_yaxes(title="성공률 (%)", range=[0, 105])
    return _layout(fig, height=360, title="시나리오별 목표 도달 성공률 (20회 이내, ±2%)")


def benchmark_curve_chart(df, max_trials):
    """Trial 예산별 누적 성공률: n회 안에 목표에 도달한 비율."""
    fig = go.Figure()
    ns = list(range(1, max_trials + 1))
    for method, name in METHODS.items():
        part = df[df["method"] == method]
        rate = [((part["trials_to_success"] <= n).sum()) / len(part) * 100 for n in ns]
        fig.add_trace(go.Scatter(x=ns, y=rate, mode="lines+markers", name=name,
                                 line=dict(color=COLORS[method], width=3 if method == "ai" else 2),
                                 hovertemplate=name + ": %{y:.0f}%<extra></extra>"))
    fig.update_xaxes(title="허용한 탐색 횟수 (Trial)", dtick=2)
    fig.update_yaxes(title="누적 성공률 (%)", range=[0, 105])
    return _layout(fig, height=360, title="탐색 횟수별 누적 성공률")


def weights_chart(records):
    """AI가 학습한 지수 wR, wC가 Trial마다 어떻게 변하는지 (이론값 -1)."""
    recs = [r for r in records if r.weights]
    fig = go.Figure()
    if recs:
        fig.add_trace(go.Scatter(x=[r.trial for r in recs], y=[r.weights[1] for r in recs],
                                 mode="lines+markers", name="R의 지수 wR", line=dict(color=COLORS["ai"])))
        fig.add_trace(go.Scatter(x=[r.trial for r in recs], y=[r.weights[2] for r in recs],
                                 mode="lines+markers", name="C의 지수 wC", line=dict(color="#7C3AED")))
    fig.add_hline(y=-1, line=dict(color=TOL_COLOR, dash="dash"), annotation_text="이론값 -1")
    fig.update_xaxes(title="Trial (학습에 사용한 실험 결과가 쌓인 시점)", dtick=1)
    fig.update_yaxes(title="학습한 지수")
    return _layout(fig, height=300, title="AI가 학습한 관계식의 지수")
