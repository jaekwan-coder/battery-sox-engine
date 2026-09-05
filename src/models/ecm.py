"""
등가회로모델(ECM) 시뮬레이터 — 2RC + 히스테리시스

이론적 배경: docs/02_theory/W1_electrochemistry_ecm.md (M1.6)
관련 설계 결정: docs/01_decisions.md D-001 (RC 개수), D-002 (이산화 방법)

회로 구조:
    OCV(SOC) -- R0 -- [R1||C1] -- [R2||C2] -- 단자

상태벡터:
    x = [SOC, V_RC1, V_RC2]

이산화 방법: ZOH (Zero-Order Hold)
    W0_foundations.md Q8에서 다룬 대로, 전진 오일러는 시상수 대비
    샘플링 주기가 크면 불안정해질 수 있다(Δt > 2τ에서 발산).
    RC 회로는 해석해가 존재하므로 근사 오차 없이 정확히 이산화할 수 있는
    ZOH를 사용한다 (D-002 참고).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import numpy as np


@dataclass
class ECMParameters:
    """
    ECM의 파라미터. 실제로는 SOC와 온도의 함수(룩업테이블)이지만,
    이 클래스는 "현재 시점에 평가된 스칼라 값들"을 담는 용도다.
    시간에 따라 변하는 파라미터를 다루는 방법은 src/identification/를 참고.

    R0, R1, R2: 옴 [Ohm]
    C1, C2: 패럿 [F]
    Q: 총 용량 [Ah] — 쿨롱카운팅 스케일링에 사용 (W3 M3.1 참고)
    """
    R0: float
    R1: float
    C1: float
    R2: float
    C2: float
    Q_Ah: float

    @property
    def tau1(self) -> float:
        """빠른 시상수 [s] — 전극표면 전하이동 반응 (W1.5 관문2)"""
        return self.R1 * self.C1

    @property
    def tau2(self) -> float:
        """느린 시상수 [s] — 고체 내 확산 (W1.5 관문3)"""
        return self.R2 * self.C2


def default_ocv_curve() -> Callable[[np.ndarray], np.ndarray]:
    """
    OCV(SOC) 곡선의 기본 근사 함수 (NMC 계열의 전형적 형태, 데모용).

    실전에서는 이 함수를 M3.2에서 뽑은 실측 룩업테이블(보간 함수)로
    교체해야 한다. 지금은 ECM 자체의 동작을 검증하기 위한 합성 곡선이다
    (W0_foundations.md에서 강조한 "합성 데이터로 코드를 먼저 검증한다"는
    원칙을 여기서도 따른다).

    SOC=0일 때 약 3.0V, SOC=1일 때 약 4.2V가 되도록 만든 매끄러운 곡선.
    """
    def ocv(soc: np.ndarray) -> np.ndarray:
        soc = np.clip(soc, 0.0, 1.0)
        # 로지스틱 형태 성분(중간 구간의 완만한 변화) + 양 끝단 급변 보정
        base = 3.0 + 1.2 * soc
        knee_low = 0.15 * np.exp(-soc * 25)       # SOC 0 근처 급락 보정
        knee_high = -0.10 * np.exp(-(1 - soc) * 25)  # SOC 1 근처 급등 보정
        return base + knee_low + knee_high

    return ocv


def default_ocv_slope() -> Callable[[np.ndarray], np.ndarray]:
    """
    d(OCV)/d(SOC) — EKF의 야코비안에 필요한 해석적 미분
    (W0_foundations.md Q3, Q4 참고: 이 기울기가 0에 가까워지면
    가관측성이 소실된다).
    """
    def slope(soc: np.ndarray) -> np.ndarray:
        soc = np.clip(soc, 0.0, 1.0)
        d_base = 1.2
        d_knee_low = 0.15 * (-25) * np.exp(-soc * 25)
        d_knee_high = -0.10 * (-25) * np.exp(-(1 - soc) * 25) * (-1)
        return d_base + d_knee_low + d_knee_high

    return slope


class HysteresisModel:
    """
    1차 히스테리시스 상태 모델 (W1.4 참고).

    간단한 1차 지연 형태로 구현한다:
        dh/dt = -|I|*k/Q * (h - sign(I)*h_max)

    전류 방향에 따라 h가 +h_max(충전 방향) 또는 -h_max(방전 방향)로
    서서히 수렴한다. NMC처럼 히스테리시스가 작은 소재는 h_max를 작게,
    Si 음극처럼 큰 소재는 h_max를 크게 설정한다 (W1.4의 소재별 크기 표 참고).
    """

    def __init__(self, h_max_V: float = 0.005, k: float = 1.0):
        self.h_max_V = h_max_V
        self.k = k

    def dhdt(self, h: float, current_A: float, Q_Ah: float) -> float:
        """
        부호 규약: 전류(current_A)는 방전을 양수로 정의한다(ECM 클래스와 동일).
        방전이 지속되면 h -> -h_max (단자전압을 OCV보다 낮추는 방향),
        충전이 지속되면 h -> +h_max (단자전압을 OCV보다 높이는 방향).
        이는 W1.4에서 다룬 "충전 곡선이 진짜 OCV보다 위에, 방전 곡선이
        아래에 위치한다"는 관례와 일치시킨 것이다.
        """
        Q_As = Q_Ah * 3600.0
        target = -self.h_max_V * np.sign(current_A) if current_A != 0 else 0.0
        rate = self.k * abs(current_A) / Q_As
        return -rate * (h - target)


class ECM:
    """
    2RC 등가회로모델. 연속시간 상태공간을 ZOH로 이산화해 시뮬레이션한다.

    부호 규약: 전류(current_A)는 **방전을 양수**로 정의한다.
    (W1.5, W1.6과 동일한 규약 — 방전 시 SOC가 감소하도록)
    """

    N_STATES = 3  # [SOC, V_RC1, V_RC2]

    def __init__(
        self,
        params: ECMParameters,
        ocv_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        ocv_slope_fn: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        hysteresis: Optional[HysteresisModel] = None,
        coulombic_efficiency: float = 1.0,
    ):
        self.p = params
        self.ocv_fn = ocv_fn or default_ocv_curve()
        self.ocv_slope_fn = ocv_slope_fn or default_ocv_slope()
        self.hysteresis = hysteresis
        self.eta = coulombic_efficiency

    # ------------------------------------------------------------------
    # 연속시간 상태공간 (W0_foundations.md Q3 참고)
    # ------------------------------------------------------------------
    def continuous_A(self) -> np.ndarray:
        """
        상태행렬 A. SOC 행이 0인 것에 주목 — 감쇠 없는 순수 적분기
        (W0 Q3: "쿨롱카운팅이 표류하는 이유의 수학적 근거").
        """
        return np.array([
            [0.0, 0.0, 0.0],
            [0.0, -1.0 / self.p.tau1, 0.0],
            [0.0, 0.0, -1.0 / self.p.tau2],
        ])

    def continuous_B(self) -> np.ndarray:
        Q_As = self.p.Q_Ah * 3600.0
        return np.array([
            [-self.eta / Q_As],
            [1.0 / self.p.C1],
            [1.0 / self.p.C2],
        ])

    def discretize_zoh(self, dt_s: float) -> tuple[np.ndarray, np.ndarray]:
        """
        ZOH(영차 유지) 이산화. RC 회로는 해석해가 있으므로 근사 없이
        정확히 이산화된다 (W0_foundations.md Q8, D-002 참고).

            A_d = exp(A*dt)
            B_d = A^-1 (A_d - I) B   (단, A의 SOC 행은 0이라 특이하므로
                                       그 행만 별도로 직접 적분 처리)
        """
        A = self.continuous_A()
        B = self.continuous_B()

        # SOC 행(적분기)은 A^-1이 정의되지 않으므로 해석적으로 직접 처리
        Ad = np.eye(3)
        Bd = np.zeros((3, 1))

        # SOC: 순수 적분 -> Ad[0,0]=1, Bd[0]=B[0]*dt (사다리꼴 대신 직사각형,
        # 필요시 더 정밀한 적분 규칙으로 교체 가능)
        Ad[0, 0] = 1.0
        Bd[0, 0] = B[0, 0] * dt_s

        # RC1, RC2: 표준 1차 시스템의 정확한 ZOH
        for i, tau in zip([1, 2], [self.p.tau1, self.p.tau2]):
            a = A[i, i]
            Ad[i, i] = np.exp(a * dt_s)
            Bd[i, 0] = (Ad[i, i] - 1.0) / a * B[i, 0]

        return Ad, Bd

    # ------------------------------------------------------------------
    # 출력 방정식
    # ------------------------------------------------------------------
    def output_voltage(self, state: np.ndarray, current_A: float, h: float = 0.0) -> float:
        """
        V_term = OCV(SOC) - I*R0 - V_RC1 - V_RC2 + h
        (W1.6의 단자전압 방정식 그대로)
        """
        soc, v_rc1, v_rc2 = state
        ocv = float(self.ocv_fn(np.array([soc]))[0])
        return ocv - current_A * self.p.R0 - v_rc1 - v_rc2 + h

    # ------------------------------------------------------------------
    # 시뮬레이션
    # ------------------------------------------------------------------
    def simulate(
        self,
        time_s: np.ndarray,
        current_A: np.ndarray,
        soc0: float = 1.0,
    ) -> dict:
        """
        주어진 전류 프로파일에 대해 단자전압·SOC·RC 상태를 시뮬레이션한다.

        Parameters
        ----------
        time_s : 균일 간격의 시간 벡터 [s]
        current_A : 각 시점의 전류 [A] (방전 양수)
        soc0 : 초기 SOC (0~1)

        Returns
        -------
        dict with keys: 'soc', 'v_rc1', 'v_rc2', 'voltage', 'h'
        """
        n = len(time_s)
        dt = float(time_s[1] - time_s[0])
        Ad, Bd = self.discretize_zoh(dt)

        state = np.array([soc0, 0.0, 0.0])
        h = 0.0

        soc_hist = np.zeros(n)
        v_rc1_hist = np.zeros(n)
        v_rc2_hist = np.zeros(n)
        voltage_hist = np.zeros(n)
        h_hist = np.zeros(n)

        for k in range(n):
            I = current_A[k]
            voltage_hist[k] = self.output_voltage(state, I, h)
            soc_hist[k] = state[0]
            v_rc1_hist[k] = state[1]
            v_rc2_hist[k] = state[2]
            h_hist[k] = h

            # 다음 스텝으로 전진
            state = Ad @ state + (Bd.flatten() * I)
            state[0] = np.clip(state[0], 0.0, 1.0)

            if self.hysteresis is not None:
                h = h + self.hysteresis.dhdt(h, I, self.p.Q_Ah) * dt

        return {
            "soc": soc_hist,
            "v_rc1": v_rc1_hist,
            "v_rc2": v_rc2_hist,
            "voltage": voltage_hist,
            "h": h_hist,
        }


def make_hppc_pulse_current(
    dt_s: float,
    rest_before_s: float,
    pulse_s: float,
    rest_after_s: float,
    pulse_current_A: float,
) -> np.ndarray:
    """
    합성 HPPC 펄스 전류 프로파일 생성 (검증/테스트용).
    W3_parameter_identification.md M3.1의 절차를 코드로 재현한 것.

    양수 pulse_current_A = 방전 펄스.
    """
    n_rest_before = int(rest_before_s / dt_s)
    n_pulse = int(pulse_s / dt_s)
    n_rest_after = int(rest_after_s / dt_s)

    current = np.concatenate([
        np.zeros(n_rest_before),
        np.full(n_pulse, pulse_current_A),
        np.zeros(n_rest_after),
    ])
    return current
