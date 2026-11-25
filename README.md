# AI-Circuit-Mate

RC 저역통과필터의 소자값을 반복해서 바꿔 보는 시행착오를, 이전 실험 결과로부터 배우는 AI 탐색으로 줄여 주는 웹사이트입니다.
(2026 안양대학교 AI 경진대회 본선 출품작)

## 실행 방법

```bash
python -m venv .venv
```

```bash
.venv\Scripts\Activate.ps1
```
(Mac/Linux: `source .venv/bin/activate`)

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

## 화면 구성

| 페이지 | 내용 |
|---|---|
| 소개 | 대상과 문제 정의, 사용 방법, 검증된 효과 요약 |
| AI 탐색 | ① 목표 설정 → ② AI 탐색 진행(실시간) → ③ 탐색 결과(추천 R·C, 추천 이유, 오차 그래프, 탐색 공간 지도, 주파수 응답, CSV 저장), 세 방법 비교 실행 |
| 검증 결과 | 10개 목표 시나리오 × 30회 반복 실험 결과, 한계 검증(부하 저항 조건), 결과 해석 |
| AI 작동 원리 | AI의 입력·판단·출력, 라이브러리와 직접 구현 범위, 예선 이후 바뀐 점, 예상 질문, 한계 |

## AI 탐색 방법

AI는 fc = 1/(2πRC) 공식을 모르는 상태에서 시뮬레이터 결과만 보고 다음 실험할 표준 R·C 조합을 고릅니다.

1. 처음 3번은 관계를 배우기 위한 탐색 실험(무작위)
2. 실험 결과로 대리모델 `ln fc ≈ w0 + wR·ln R + wC·ln C`를 가중 최소제곱법으로 학습
3. 아직 실험하지 않은 모든 표준 조합의 fc를 예측해 목표에 가장 가까운 조합을 다음 실험으로 선택
4. 허용 오차를 만족하면 종료

Optuna의 커스텀 샘플러(`search.py`의 `SurrogateSampler`)로 구현했고, 비교군으로 Optuna 기본 TPE와 Random Search를 같은 조건에서 실행합니다.

## 검증 결과 (`python benchmark.py`)

E24 저항(1 kΩ~100 kΩ) × E12 커패시터(1 nF~1 µF) = 1,813개 조합, 허용 오차 ±2%, 최대 20회, 10개 목표 × 30 seed

| 조건 | 방법 | 성공률 | 평균 도달 Trial |
|---|---|---|---|
| 이상적 RC | AI 탐색 (대리모델) | 100% | 4.0 |
| 이상적 RC | Optuna TPE (예선안) | 12.3% | 10.9 |
| 이상적 RC | Random Search | 8.3% | 11.8 |
| 부하 20 kΩ (한계 검증) | AI 탐색 (대리모델) | 85.3% | 9.4 |
| 부하 20 kΩ (한계 검증) | Optuna TPE (예선안) | 18.3% | 11.8 |
| 부하 20 kΩ (한계 검증) | Random Search | 9.3% | 11.4 |

## 파일 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit 웹 화면 |
| `circuit.py` | 표준 소자 후보 생성, 차단주파수·오차 계산, 정답지(전수 계산) |
| `search.py` | AI 탐색(대리모델 샘플러), Optuna TPE, Random Search |
| `benchmark.py` | 10개 시나리오 비교 실험 → `data/benchmark_runs.csv` |
| `charts.py` | Plotly 그래프 |
| `tests/` | 자동 테스트 (`python -m pytest`) |

## 한계

- 1차 RC 저역통과필터 한 종류만 지원
- 시뮬레이터는 RC 공식 계산 (ngspice 연동 전)
- 대리모델은 소자값의 거듭제곱 꼴 관계를 가정 → 크게 벗어나는 회로에서는 성능 저하 가능
- 부품 공차 미반영
