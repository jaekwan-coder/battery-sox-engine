"""
HPPC 파라미터 추출 — ecm.py의 역과정

이론적 배경: docs/02_theory/W3_parameter_identification.md (M3.3)
설계 근거: docs/02_theory/W3_hppc_code.md

ecm.py:  R0, R1, C1 (안다고 치고) -> 전압 계산 (순방향)
hppc.py: 전압, 전류 (측정했다고 치고) -> R0, R1, C1 역산 (역방향)

1차 구현 범위: 1RC만 다룬다 (R2, C2 확장은 다음 단계).
이유는 W3_hppc_code.md "2RC를 이번 1차 구현에서 제외하는 이유" 참고 —
시상수 분리 문제를 1RC로 파이프라인부터 안정화한 뒤 다룬다.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from scipy.optimize import curve_fit

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.models.ecm import ECM, ECMParameters, make_hppc_pulse_current


# ----------------------------------------------------------------------
# 결과를 담는 그릇
# ----------------------------------------------------------------------
@dataclass
class HPPCFitResult:
    """
    한 번의 HPPC 펄스에서 추출한 파라미터.
    R2, C2는 1차 구현 범위 밖이라 0.0으로 채워 ECMParameters와 호환되게 한다.
    """
    R0: float
    R1: float
    C1: float
    tau1: float
    fit_rmse: float  # 완화곡선 피팅이 실제 데이터와 얼마나 잘 맞았는지 (진단용)

    def to_ecm_parameters(self, Q_Ah: float) -> ECMParameters:
        """이 결과를 ecm.py의 ECMParameters 형태로 변환 (1RC이므로 R2=C2=0에
        가까운 더미 값을 넣어 2RC 인터페이스와 호환시킴)."""
        return ECMParameters(
            R0=self.R0, R1=self.R1, C1=self.C1,
            R2=1e-9, C2=1e-9,  # 사실상 없는 것처럼 (tau2가 0에 가까워 무시됨)
            Q_Ah=Q_Ah,
        )


# ----------------------------------------------------------------------
# 계산 1: 펄스 구간 찾기
# ----------------------------------------------------------------------
def find_pulse_edges(current_A: np.ndarray, threshold: float = 1e-6) -> list[tuple[int, int]]:
    """
    전류가 0(휴지)에서 벗어났다가(펄스 시작) 다시 0으로 돌아오는(펄스 끝)
    구간들을 찾는다. 여러 펄스가 있는 시계열도 다룰 수 있게 리스트로 반환.

    Returns
    -------
    [(펄스시작_인덱스, 펄스끝_인덱스), ...]
    """
    is_active = np.abs(current_A) > threshold
    edges = []
    start = None
    for i, active in enumerate(is_active):
        if active and start is None:
            start = i
        elif not active and start is not None:
            edges.append((start, i))  # i는 펄스가 끝나고 처음 0이 된 지점
            start = None
    if start is not None:
        edges.append((start, len(current_A)))
    return edges


# ----------------------------------------------------------------------
# 계산 2: R0 (즉시 강하)
# ----------------------------------------------------------------------
def extract_r0(voltage: np.ndarray, current_A: np.ndarray,
                pulse_start_idx: int, n_instant: int = 1) -> float:
    """
    펄스 시작 직전 n_instant개 샘플의 평균 전압과, 펄스 시작 직후
    n_instant개 샘플의 평균 전압 차이를 전류로 나눠 R0를 계산한다.
    (W3_parameter_identification.md M3.3 "R0 뽑기" 참고)

    n_instant를 1보다 크게 주면 노이즈에 덜 민감해지지만, 그만큼
    "즉시"라는 가정에서 멀어진다는 트레이드오프가 있다.
    """
    before = voltage[max(0, pulse_start_idx - n_instant):pulse_start_idx].mean()
    after = voltage[pulse_start_idx:pulse_start_idx + n_instant].mean()
    I = current_A[pulse_start_idx]
    if abs(I) < 1e-12:
        raise ValueError("펄스 시작 지점의 전류가 0에 가깝다 — 인덱스를 확인하라")
    return (before - after) / I


# ----------------------------------------------------------------------
# 계산 3: R1, C1 (완화곡선 피팅) — 여기가 비선형 피팅이 필요한 부분
# ----------------------------------------------------------------------
def _relaxation_model(t: np.ndarray, v_inf: float, a1: float, tau1: float) -> np.ndarray:
    """V(t) = V_inf + A1 * exp(-t/tau1)  (W1 M1.5의 RC 완화 형태 그대로)"""
    return v_inf + a1 * np.exp(-t / tau1)


def fit_relaxation(
    time_s: np.ndarray,
    voltage: np.ndarray,
    initial_guess: Optional[dict] = None,
) -> dict:
    """
    완화구간(펄스 종료 후 전압이 서서히 안정되는 구간)에 지수함수를
    피팅해 R1, C1을 얻는다.

    time_s, voltage는 "펄스가 끝난 시점"을 t=0으로 다시 맞춘 배열이어야 한다
    (호출하는 쪽에서 슬라이싱 + 시간 원점 이동을 해서 넘겨줄 것).

    initial_guess가 없으면 데이터에서 대략적인 값을 추정해 시도한다.
    W3_parameter_identification.md M3.3에서 강조했듯 비선형 피팅은
    초기값에 민감하므로, 필요시 이 인자로 직접 지정할 수 있게 열어둔다.
    """
    v_inf_guess = voltage[-1]
    a1_guess = voltage[0] - v_inf_guess
    # tau 초기값: 전체 구간의 1/5 정도로 어림잡음 (완전 임의는 아니고,
    # "관측 구간 안에 최소 한두 번의 시상수가 들어있을 것"이라는
    # 상식적 가정에 근거)
    tau1_guess = (time_s[-1] - time_s[0]) / 5.0

    p0 = initial_guess or {"v_inf": v_inf_guess, "a1": a1_guess, "tau1": tau1_guess}

    popt, _ = curve_fit(
        _relaxation_model, time_s, voltage,
        p0=[p0["v_inf"], p0["a1"], p0["tau1"]],
        maxfev=10000,
    )
    v_inf, a1, tau1 = popt

    fitted = _relaxation_model(time_s, *popt)
    rmse = float(np.sqrt(np.mean((voltage - fitted) ** 2)))

    # R1, C1 환산: 완화 시작 시점의 전류(펄스 전류)를 알아야 R1을 얻는다.
    # 이 함수는 전류를 모르므로, R1=A1/I 환산은 호출하는 쪽(extract_hppc_parameters)
    # 에서 수행한다. 여기서는 a1(=R1*I)과 tau1만 돌려준다.
    return {"v_inf": v_inf, "a1": a1, "tau1": tau1, "rmse": rmse}


# ----------------------------------------------------------------------
# 대장 함수: 위 셋을 조합
# ----------------------------------------------------------------------
def extract_hppc_parameters(
    time_s: np.ndarray,
    voltage: np.ndarray,
    current_A: np.ndarray,
    pulse_index: int = 0,
    relaxation_fraction: float = 0.9,
    initial_guess: Optional[dict] = None,
    pulse_edges: Optional[list] = None,
    edge_threshold: float = 1e-6,
) -> HPPCFitResult:
    """
    하나의 HPPC 펄스 데이터에서 R0, R1, C1을 한 번에 추출한다.

    Parameters
    ----------
    time_s, voltage, current_A : 균일 샘플링된 전체 시계열
    pulse_index : pulse_edges 목록 중 몇 번째를 쓸지
    relaxation_fraction : 펄스 종료 후 휴지 구간 중 앞부분 몇 %를
        완화곡선 피팅에 쓸지 (뒤쪽은 노이즈 대비 신호가 작아 덜 신뢰함)
    pulse_edges : 이미 find_pulse_edges로 찾아둔 펄스 목록. **반드시 넘길 것**.
        호출하는 쪽(예: extract_soc_table.py)이 특정 threshold로 찾은
        목록의 "몇 번째"를 pulse_index로 지정하는데, 이 함수가 예전처럼
        내부에서 다른 threshold로 펄스를 다시 찾으면 번호가 서로 다른
        펄스를 가리키게 되는 심각한 불일치가 생긴다. 실측 데이터에서
        실제로 확인된 버그다 - PAU 구간의 부동소수점 잔류값(예: -3e-5A)이
        threshold=1e-6에서는 "펄스"로 잘못 잡혀 이후 모든 펄스 번호가
        밀렸고, 그 결과 R0/R1/C1이 매번 엉뚱한 펄스에서 계산되고 있었다.
        하위호환을 위해 None이면 edge_threshold로 자체 탐색하되,
        이 경우 호출하는 쪽과 threshold를 반드시 맞춰야 한다(위험하므로
        가급적 pulse_edges를 명시적으로 넘길 것).
    edge_threshold : pulse_edges가 None일 때만 사용하는 자체 탐색 threshold.
    """
    edges = pulse_edges if pulse_edges is not None else find_pulse_edges(current_A, threshold=edge_threshold)
    if pulse_index >= len(edges):
        raise ValueError(f"pulse_index={pulse_index}, 찾은 펄스 개수={len(edges)}")

    pulse_start, pulse_end = edges[pulse_index]
    I_pulse = current_A[pulse_start]

    r0 = extract_r0(voltage, current_A, pulse_start)

    # 완화구간: 펄스가 끝난 시점부터, 다음 펄스가 시작되기 전까지
    next_pulse_start = edges[pulse_index + 1][0] if pulse_index + 1 < len(edges) else len(time_s)
    relax_end = pulse_end + int((next_pulse_start - pulse_end) * relaxation_fraction)

    t_relax = time_s[pulse_end:relax_end] - time_s[pulse_end]  # t=0으로 원점 이동
    v_relax = voltage[pulse_end:relax_end]

    fit = fit_relaxation(t_relax, v_relax, initial_guess)

    r1 = fit["a1"] / (-I_pulse)  # 방전 시 전압이 낮아지는 방향으로 a1이 나오므로 부호 정리
    r1 = abs(r1)
    c1 = fit["tau1"] / r1

    return HPPCFitResult(R0=r0, R1=r1, C1=c1, tau1=fit["tau1"], fit_rmse=fit["rmse"])


# ----------------------------------------------------------------------
# 검증: ecm.py로 합성 데이터를 만들어 이 파일 전체를 자체 검증
# ----------------------------------------------------------------------
def validate_with_synthetic_data(
    true_params: ECMParameters,
    dt_s: float = 0.1,
    rest_before_s: float = 60.0,
    pulse_s: float = 18.0,
    rest_after_s: float = 120.0,
    pulse_current_A: float = 3.0,
    tolerance: float = 0.05,
    verbose: bool = True,
) -> bool:
    """
    W3_parameter_identification.md에서 강조한 "합성 데이터로 먼저 검증"
    원칙을 자동화한 함수.

    1. ecm.py로 true_params를 이용해 가짜 HPPC 데이터를 생성
    2. 이 파일의 extract_hppc_parameters로 파라미터를 재추출
    3. true_params와 상대오차가 tolerance 이내인지 확인

    주의: true_params는 1RC로 간주하고 검증한다(R2, C2는 무시됨).
    ecm.py 쪽에 2RC 성분이 섞여 있으면 이 검증은 통과하지 못할 수 있다 —
    이는 실패가 아니라 "1RC 가정 자체의 한계"를 보여주는 것이다.
    """
    current = make_hppc_pulse_current(
        dt_s=dt_s, rest_before_s=rest_before_s, pulse_s=pulse_s,
        rest_after_s=rest_after_s, pulse_current_A=pulse_current_A,
    )
    time_s = np.arange(len(current)) * dt_s

    ecm = ECM(true_params)
    result = ecm.simulate(time_s, current, soc0=0.9)
    voltage = result["voltage"]

    fit = extract_hppc_parameters(time_s, voltage, current, pulse_index=0)

    checks = {
        "R0": (true_params.R0, fit.R0),
        "R1": (true_params.R1, fit.R1),
        "C1": (true_params.C1, fit.C1),
    }

    all_pass = True
    for name, (true_val, fit_val) in checks.items():
        rel_err = abs(fit_val - true_val) / abs(true_val)
        passed = rel_err < tolerance
        all_pass = all_pass and passed
        if verbose:
            status = "PASS" if passed else "FAIL"
            print(f"{status}: {name} 참값={true_val:.6g}, 추출값={fit_val:.6g}, "
                  f"상대오차={rel_err*100:.2f}%")

    if verbose:
        print(f"완화곡선 피팅 RMSE = {fit.fit_rmse:.6g} V")

    return all_pass


if __name__ == "__main__":
    # W3_hppc_code.md 검증계획 2단계: 1RC 전체 파이프라인 확인
    print("=== 1RC 합성 데이터 검증 ===")
    true_params = ECMParameters(R0=0.02, R1=0.01, C1=100.0, R2=1e-9, C2=1e-9, Q_Ah=3.0)
    ok = validate_with_synthetic_data(true_params)
    print("\n결과:", "통과" if ok else "실패")
