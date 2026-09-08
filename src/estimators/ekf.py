"""
확장 칼만필터(EKF) — 노이즈 섞인 전압·전류로 SOC를 실시간 추정

이론적 배경: docs/02_theory/W0_foundations.md Q3(상태공간), Q4(가관측성,
야코비안), Q6(가우시안 곱=칼만필터의 정체)

설계 원칙: 예측 모델(상태전이·출력방정식)은 새로 짜지 않고, 이미 검증된
ecm.py(ECM.discretize_zoh, ECM.output_voltage)와 dynamic_ecm.py의
"매 스텝 SOC로 파라미터 재조회" 패턴을 그대로 재사용한다. 지난 두 버그
(펄스 인덱스 불일치, 이중 부호반전)에서 배운 "같은 계산을 여러 곳에서
각자 다시 하면 어긋난다"는 교훈을 여기서도 지킨다.

상태벡터: x = [SOC, V_RC1, V_RC2] (ecm.py와 동일. R2,C2는 parameter_lookup
에서 이미 사실상 0으로 고정해뒀으므로 V_RC2는 사실상 죽은 상태 -
1RC까지만 유효한 현재 범위의 자연스러운 결과)

출력 야코비안: H = [dOCV/dSOC, -1, -1]
    dOCV/dSOC는 lookup.OCV_slope()를 그대로 사용 - 룩업테이블을 직접
    차분하지 않고 스플라인 미분을 쓴 이유는 W0_foundations.md Q4에서
    이미 설명한 대로다 ("차분하면 노이즈, 스플라인으로 미분").

상태전이 야코비안: F = Ad (discretize_zoh가 그 스텝의 파라미터로 계산한
    이산 상태행렬을 그대로 사용). 엄밀히는 R0/R1/C1 자체가 SOC의 함수라
    Ad를 SOC로 한 번 더 미분해야 완전한 선형화지만, 이건 EKF 문헌에서
    흔히 쓰는 표준 근사다(그 스텝의 파라미터를 "그 순간의 상수"로 취급).
    이 근사의 영향은 검증 결과의 수렴 양상으로 간접 확인한다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np

from src.models.ecm import ECM
from src.identification.parameter_lookup import ECMParameterLookup


class BatteryEKF:
    """
    배터리 SOC(및 V_RC1, V_RC2) 실시간 추정기.

    사용법:
        ekf = BatteryEKF(lookup, Q_Ah=3.0, soc0_guess=0.5, ...)
        for I, V_measured in zip(currents, voltages):
            soc_est = ekf.step(I, V_measured, dt)
    """

    def __init__(
        self,
        lookup: ECMParameterLookup,
        Q_Ah: float,
        soc0_guess: float,
        p0_soc_var: float = 0.05 ** 2,   # 초기 SOC 불확실성 (표준편차 5%)
        p0_vrc_var: float = 1e-6,
        process_noise_soc: float = 1e-9,  # W0 Q6의 Q: 모델을 얼마나 못 믿는지
        process_noise_vrc: float = 1e-8,
        measurement_noise_V: float = 0.005 ** 2,  # W0 Q6의 R: 센서 정확도
                                                     # (0.1% of 5V FS ~= 5mV, Readme 스펙 근거)
    ):
        self.lookup = lookup
        self.Q_Ah = Q_Ah

        self.x = np.array([soc0_guess, 0.0, 0.0])
        self.P = np.diag([p0_soc_var, p0_vrc_var, p0_vrc_var])
        self.Qmat = np.diag([process_noise_soc, process_noise_vrc, process_noise_vrc])
        self.R_meas = measurement_noise_V

        # 계산 재사용을 위한 ECM 골격 하나 (dynamic_ecm.py와 같은 패턴:
        # self.p만 매 스텝 갈아 끼우고, 계산 함수는 그대로 재사용)
        init_params = lookup.snapshot_at(soc0_guess, Q_Ah=Q_Ah)
        self._ecm = ECM(init_params, ocv_fn=lookup.OCV, ocv_slope_fn=lookup.OCV_slope)

        # 진단용 기록 (NIS 등 검증에 쓸 수 있게 남겨둠)
        self.last_innovation = None
        self.last_innovation_var = None

    def step(self, current_A: float, voltage_measured: float, dt: float) -> float:
        """
        한 스텝(예측+갱신)을 수행하고, 갱신된 SOC 추정값을 반환한다.
        """
        # ---- 예측 단계 ----
        current_soc_guess = self.x[0]
        self._ecm.p = self.lookup.snapshot_at(current_soc_guess, Q_Ah=self.Q_Ah)

        Ad, Bd = self._ecm.discretize_zoh(dt)
        F = Ad  # 상태전이 야코비안 = 이산 상태행렬 그 자체 (선형 부분이므로 정확)

        x_pred = Ad @ self.x + Bd.flatten() * current_A
        x_pred[0] = np.clip(x_pred[0], 0.0, 1.0)

        P_pred = F @ self.P @ F.T + self.Qmat

        # ---- 갱신 단계 ----
        v_pred = self._ecm.output_voltage(x_pred, current_A, h=0.0)

        ocv_slope = float(self.lookup.OCV_slope(x_pred[0])[0])
        H = np.array([ocv_slope, -1.0, -1.0])  # 출력 야코비안 (W0 Q3/Q4)

        innovation = voltage_measured - v_pred
        S = H @ P_pred @ H.T + self.R_meas  # 혁신 공분산 (스칼라)
        K = (P_pred @ H) / S                 # 칼만 이득 (W0 Q6: P/(P+R)의 벡터 버전)

        x_upd = x_pred + K * innovation
        x_upd[0] = np.clip(x_upd[0], 0.0, 1.0)

        I3 = np.eye(3)
        P_upd = (I3 - np.outer(K, H)) @ P_pred

        self.x = x_upd
        self.P = P_upd
        self.last_innovation = innovation
        self.last_innovation_var = S

        return float(self.x[0])

    @property
    def soc_std(self) -> float:
        """현재 SOC 추정의 표준편차 (불확실성 크기, W0 Q5 참고)"""
        return float(np.sqrt(self.P[0, 0]))


if __name__ == "__main__":
    # 검증: dynamic_ecm.py(이미 검증된 진짜 삼성 셀 모델)로 "진짜" 시나리오를
    # 만들고, 노이즈를 섞은 뒤, 일부러 틀린 초기 SOC로 EKF를 시작시켜
    # 진짜 SOC로 수렴하는지 확인한다. 비교군으로 "보정 없는 순수
    # 쿨롱카운팅"도 같이 돌려, EKF가 실제로 갖는 가치를 대조한다.
    from src.models.dynamic_ecm import simulate_dynamic

    lookup = ECMParameterLookup(
        "data/processed/25degC_hppc_params.csv",
        "data/processed/25degC_ocv_curve.csv",
    )

    Q_Ah = 3.0
    dt = 60.0
    n = int(2.5 * 3600 / dt)  # 2.5시간 시뮬레이션
    time_s = np.arange(n) * dt
    current_A = np.full(n, 1.0)  # 약 C/3 방전

    true = simulate_dynamic(lookup, time_s, current_A, soc0=1.0, Q_Ah=Q_Ah)

    rng = np.random.default_rng(42)
    voltage_noisy = true["voltage"] + rng.normal(0, 0.005, n)  # 5mV 측정노이즈
    current_noisy = current_A + rng.normal(0, 0.01, n)          # 약간의 전류센서 노이즈

    # EKF: 일부러 틀린 초기값(0.5)에서 시작 (진짜는 1.0)
    ekf = BatteryEKF(lookup, Q_Ah=Q_Ah, soc0_guess=0.5)
    ekf_soc = np.zeros(n)
    for k in range(n):
        ekf_soc[k] = ekf.step(current_noisy[k], voltage_noisy[k], dt)

    # 비교군: 보정 없는 순수 쿨롱카운팅, 역시 틀린 초기값(0.5)에서 시작
    cc_soc = np.zeros(n)
    cc_soc[0] = 0.5
    for k in range(1, n):
        cc_soc[k] = np.clip(
            cc_soc[k-1] - current_noisy[k] * dt / (Q_Ah * 3600.0), 0.0, 1.0,
        )

    print("시간     진짜SOC    EKF추정    EKF오차   순수적산    순수적산오차")
    for i in range(0, n, max(1, n // 15)):
        t_h = time_s[i] / 3600
        print(f"{t_h:5.2f}h   {true['soc'][i]*100:6.2f}%   {ekf_soc[i]*100:6.2f}%   "
              f"{(ekf_soc[i]-true['soc'][i])*100:+6.2f}%p   {cc_soc[i]*100:6.2f}%   "
              f"{(cc_soc[i]-true['soc'][i])*100:+6.2f}%p")

    print(f"\n최종 시점 EKF 오차: {(ekf_soc[-1]-true['soc'][-1])*100:+.2f}%p")
    print(f"최종 시점 순수적산 오차: {(cc_soc[-1]-true['soc'][-1])*100:+.2f}%p")
    print(f"EKF의 현재 SOC 불확실성(표준편차): {ekf.soc_std*100:.2f}%p")