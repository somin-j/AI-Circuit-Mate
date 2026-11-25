"""소자값 탐색 알고리즘.

세 가지 탐색 방법을 같은 조건(같은 후보, 같은 목표, 같은 최대 횟수)으로 실행한다.

- "ai"     : AI 탐색. Optuna 위에서 동작하는 회로 대리모델(surrogate) 샘플러.
             지금까지의 실험 결과로 "소자값 → 차단주파수" 관계를 학습하고,
             목표에 가장 가까울 것으로 예측되는 다음 R·C 조합을 고른다.
- "tpe"    : Optuna 기본 TPE 샘플러 (예선 계획안, 비교용).
- "random" : Random Search. 아직 시도하지 않은 조합 중 무작위로 고른다.

탐색 과정에서 AI는 fc = 1/(2πRC) 공식을 모른다. 후보를 넣으면 fc를 돌려주는
"시뮬레이터"(simulate 함수)의 결과만 보고 다음 후보를 정한다.
추후 simulate를 ngspice 호출로 바꿔도 탐색 코드는 그대로 동작한다.
"""
import math
import random
import time
from dataclasses import dataclass, field

import numpy as np
import optuna
from optuna.distributions import CategoricalDistribution

from core.circuit import cutoff_frequency, error_rate

optuna.logging.set_verbosity(optuna.logging.WARNING)

METHODS = {
    "ai": "AI 탐색 (대리모델)",
    "tpe": "Optuna TPE (예선안)",
    "random": "Random Search",
}


def simulate(r, c, load_r=None):
    """회로 시뮬레이터 자리. 지금은 RC 공식으로 계산하고, 추후 ngspice로 교체할 수 있다.

    load_r: 출력단에 연결된 부하 저항 [Ω]. None이면 이상적인 무부하 RC 필터.
            부하가 있으면 C에서 본 저항이 R ∥ R_L로 줄어 fc가 높아진다.
            (AI의 대리모델 형태와 실제 관계가 어긋나는 상황의 한계 검증용)
    """
    if load_r:
        return cutoff_frequency(r * load_r / (r + load_r), c)
    return cutoff_frequency(r, c)


@dataclass
class TrialRecord:
    trial: int            # 몇 번째 실험인지 (중복 없는 조합 기준)
    r: float
    c: float
    fc: float
    error: float          # 목표 대비 오차율 [%]
    best_error: float     # 지금까지의 최소 오차율 [%]
    success: bool         # 허용오차 이내인지
    reason: str           # 이 후보를 고른 이유 (화면 표시용)
    predicted_fc: float | None = None   # AI가 실험 전에 예측한 fc
    weights: list | None = None         # AI가 학습한 관계식 계수 [w0, wR, wC]
    elapsed: float = 0.0  # 탐색 시작부터 걸린 시간 [s]


@dataclass
class SearchResult:
    method: str
    records: list = field(default_factory=list)

    @property
    def best(self):
        return min(self.records, key=lambda rec: rec.error) if self.records else None

    @property
    def success_trial(self):
        """허용오차에 처음 도달한 실험 번호. 도달하지 못하면 None."""
        for rec in self.records:
            if rec.success:
                return rec.trial
        return None


# ----------------------------------------------------------------------------
# Optuna 샘플러
# ----------------------------------------------------------------------------
def _completed(study):
    """완료된 실험들의 (R, C, fc) 목록."""
    out = []
    for t in study.get_trials(deepcopy=False, states=[optuna.trial.TrialState.COMPLETE]):
        if "R" in t.params and "C" in t.params:
            out.append((t.params["R"], t.params["C"], t.user_attrs["fc"]))
    return out


class _CombinationSampler(optuna.samplers.BaseSampler):
    """R·C를 한 쌍으로 함께 고르는 샘플러의 공통 부분."""

    def __init__(self, rs, cs, seed=None):
        self.rs, self.cs = list(rs), list(cs)
        self.rng = random.Random(seed)
        self.last_decision = {}

    def infer_relative_search_space(self, study, trial):
        return {"R": CategoricalDistribution(self.rs), "C": CategoricalDistribution(self.cs)}

    def sample_independent(self, study, trial, param_name, param_distribution):
        return self.rng.choice(param_distribution.choices)

    def _untried(self, study):
        tried = {(r, c) for r, c, _ in _completed(study)}
        return [(r, c) for r in self.rs for c in self.cs if (r, c) not in tried]

    def sample_relative(self, study, trial, search_space):
        if not search_space:
            return {}
        untried = self._untried(study)
        if not untried:
            return {}
        r, c = self.choose(study, untried)
        return {"R": r, "C": c}

    def choose(self, study, untried):
        raise NotImplementedError


class RandomComboSampler(_CombinationSampler):
    """Random Search: 시도하지 않은 조합 중 무작위 선택 (중복 없이)."""

    def choose(self, study, untried):
        self.last_decision = {"reason": "무작위 선택 (이전 결과를 사용하지 않음)"}
        return self.rng.choice(untried)


class SurrogateSampler(_CombinationSampler):
    """AI 탐색: 실험 결과로 회로 대리모델을 학습해 다음 후보를 고른다.

    대리모델:  ln(fc) ≈ w0 + wR·ln(R) + wC·ln(C)
      - 계수 w0, wR, wC는 정해 두지 않고, 지금까지의 실험 결과(R, C, fc)로부터
        가중 최소제곱법으로 학습한다. (RC 회로라면 wR, wC가 -1 근처로 학습된다.)
      - 목표에 가까웠던 실험일수록 큰 가중치를 준다. 실제 관계가 모델과 조금
        다르더라도(예: 부하 저항) 목표 근처에서는 정확하게 맞추기 위해서다.
      - 로그 공간 선형 모델을 고른 이유: 소자값이 E 시리즈처럼 로그 간격으로
        분포하고, 수동 소자 회로의 성능 지표는 대개 소자값의 거듭제곱 꼴이기 때문.
    선택 규칙:
      - 처음 n_startup번은 관계를 배우기 위한 탐색 실험(무작위).
      - 이후에는 학습한 모델로 아직 시도하지 않은 모든 표준 조합의 fc를 예측하고,
        목표에 가장 가깝다고 예측되는 조합을 다음 실험으로 고른다.
    """

    def __init__(self, rs, cs, target_fc, n_startup=3, seed=None):
        super().__init__(rs, cs, seed)
        self.target_fc = target_fc
        self.n_startup = n_startup

    def fit(self, data):
        """실험 데이터로 대리모델 계수를 학습한다. 데이터가 부족하면 None."""
        if len(data) < self.n_startup:
            return None
        x = np.array([[1.0, math.log(r), math.log(c)] for r, c, _ in data])
        y = np.array([math.log(fc) for _, _, fc in data])
        if np.linalg.matrix_rank(x) < 3:
            return None
        weight = 1 / (np.abs(y - math.log(self.target_fc)) + 0.05)
        w, *_ = np.linalg.lstsq(x * weight[:, None], y * weight, rcond=None)
        return w

    def choose(self, study, untried):
        data = _completed(study)
        w = self.fit(data)
        if w is None:
            self.last_decision = {
                "reason": f"관계 학습을 위한 탐색 실험 ({len(data) + 1}/{self.n_startup})",
            }
            return self.rng.choice(untried)

        log_target = math.log(self.target_fc)

        def predicted_gap(rc):
            return abs(w[0] + w[1] * math.log(rc[0]) + w[2] * math.log(rc[1]) - log_target)

        r, c = min(untried, key=predicted_gap)
        pred = math.exp(w[0] + w[1] * math.log(r) + w[2] * math.log(c))
        self.last_decision = {
            "reason": f"학습한 관계로 예측: fc ≈ {pred:,.1f} Hz (목표에 가장 가까운 후보)",
            "predicted_fc": pred,
            "weights": [float(v) for v in w],
        }
        return r, c


def _snap(values, x):
    """로그 기준으로 x와 가장 가까운 표준값."""
    return min(values, key=lambda v: abs(math.log(v / x)))


# ----------------------------------------------------------------------------
# 탐색 실행
# ----------------------------------------------------------------------------
def run_search(method, target_fc, tolerance, max_trials, rs, cs, seed=42, load_r=None):
    """탐색을 실행하며 실험 한 번이 끝날 때마다 TrialRecord를 내보낸다(generator).

    - 같은 조합은 두 번 실험하지 않는다 (실험 횟수 = 서로 다른 조합 수).
    - 허용오차 이내 조합을 찾으면 즉시 멈춘다 (조기 종료).
    """
    if method == "ai":
        sampler = SurrogateSampler(rs, cs, target_fc, seed=seed)
    elif method == "random":
        sampler = RandomComboSampler(rs, cs, seed=seed)
    elif method == "tpe":
        sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True, n_startup_trials=5)
    else:
        raise ValueError(f"알 수 없는 탐색 방법: {method}")

    study = optuna.create_study(direction="minimize", sampler=sampler)
    tried = {}
    best_error = float("inf")
    n = 0
    attempts = 0
    start = time.perf_counter()
    total = len(rs) * len(cs)

    while n < min(max_trials, total) and attempts < max_trials * 50:
        attempts += 1
        trial = study.ask()
        if method == "tpe":
            # TPE는 연속값을 제안하고, 가장 가까운 표준값으로 맞춘다.
            r = _snap(rs, trial.suggest_float("R_raw", rs[0], rs[-1], log=True))
            c = _snap(cs, trial.suggest_float("C_raw", cs[0], cs[-1], log=True))
            decision = {"reason": "TPE: 좋은 결과/나쁜 결과 분포를 비교해 고른 후보"}
        else:
            r = trial.suggest_categorical("R", sampler.rs)
            c = trial.suggest_categorical("C", sampler.cs)
            decision = dict(sampler.last_decision)

        if (r, c) in tried:
            # 이미 실험한 조합: 다시 시뮬레이션하지 않고 기존 결과만 알려준다.
            trial.set_user_attr("fc", tried[(r, c)])
            study.tell(trial, error_rate(tried[(r, c)], target_fc))
            continue

        fc = simulate(r, c, load_r)
        tried[(r, c)] = fc
        err = error_rate(fc, target_fc)
        trial.set_user_attr("fc", fc)
        study.tell(trial, err)

        n += 1
        best_error = min(best_error, err)
        rec = TrialRecord(
            trial=n, r=r, c=c, fc=fc, error=err, best_error=best_error,
            success=err <= tolerance, reason=decision.get("reason", ""),
            predicted_fc=decision.get("predicted_fc"), weights=decision.get("weights"),
            elapsed=time.perf_counter() - start,
        )
        yield rec
        if rec.success:
            break


def search(method, target_fc, tolerance, max_trials, rs, cs, seed=42, load_r=None):
    """탐색을 끝까지 실행하고 SearchResult를 반환한다."""
    result = SearchResult(method)
    result.records = list(run_search(method, target_fc, tolerance, max_trials, rs, cs,
                                     seed, load_r))
    return result


if __name__ == "__main__":
    from core.circuit import capacitor_candidates, fmt_si, resistor_candidates

    rs, cs = resistor_candidates(), capacitor_candidates()
    for m, name in METHODS.items():
        res = search(m, 1000, 2, 20, rs, cs, seed=42)
        b = res.best
        print(f"[{name}] 도달 Trial={res.success_trial}, 최선 R={fmt_si(b.r, 'Ω')}, "
              f"C={fmt_si(b.c, 'F')}, fc={b.fc:.1f} Hz, 오차={b.error:.2f}%")
