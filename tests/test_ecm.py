"""
ECM 단위 테스트.

전략 (docs/00_learning_log.md에서 강조한 원칙):
합성 데이터(정답을 아는 상황)로 먼저 검증한다. 여기서는 W0에서 손으로
유도한 RC 계단응답의 해석해(V=IR(1-e^{-t/tau}))와 시뮬레이션 결과를
직접 비교한다.
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.models.ecm import ECM, ECMParameters, HysteresisModel, make_hppc_pulse_current


def test_r0_instantaneous_drop():
    """
    R0 성분: 전류 인가 시 즉시(첫 스텝) 전압이 I*R0만큼 떨어져야 한다.
    (W1.5 관문1 - 즉각적)
    """
    params = ECMParameters(R0=0.02, R1=0.01, C1=100.0, R2=0.005, C2=2000.0, Q_Ah=3.0)
    ecm = ECM(params)

    dt = 0.1
    t = np.arange(0, 5, dt)
    I = np.full_like(t, 1.0)  # 1A 방전 유지

    result = ecm.simulate(t, I, soc0=0.9)

    ocv_at_start = float(ecm.ocv_fn(np.array([0.9]))[0])
    v0 = result["voltage"][0]

    # 첫 스텝에서는 RC1, RC2가 아직 0이므로 V = OCV - I*R0 이어야 함
    expected_v0 = ocv_at_start - 1.0 * params.R0
    assert abs(v0 - expected_v0) < 1e-9, f"R0 즉시강하 불일치: {v0} vs {expected_v0}"
    print("PASS: R0 즉시강하 검증")


def test_rc_step_response_matches_analytic():
    """
    W0_foundations.md Q1의 해석해와 비교:
    V_RC(t) = I*R*(1 - exp(-t/tau))

    R1 하나만 있는 것처럼 R2를 아주 작게, C2도 극단적으로 만들어
    RC1 성분만 지배적이게 한 뒤 검증한다.
    """
    R1, C1 = 0.03, 50.0  # tau1 = 1.5s
    params = ECMParameters(R0=0.0, R1=R1, C1=C1, R2=1e-9, C2=1e-9, Q_Ah=3.0)
    ecm = ECM(params)

    dt = 0.01
    t = np.arange(0, 10, dt)
    I = np.full_like(t, 2.0)  # 2A 방전

    result = ecm.simulate(t, I, soc0=0.5)

    tau1 = R1 * C1
    analytic_v_rc1 = 2.0 * R1 * (1 - np.exp(-t / tau1))

    # 초반 몇 스텝의 수치오차를 감안해 마지막 구간에서 비교
    diff = np.abs(result["v_rc1"][-1] - analytic_v_rc1[-1])
    assert diff < 1e-3, f"RC 계단응답 해석해와 불일치: {diff}"
    print(f"PASS: RC1 계단응답이 해석해와 일치 (오차={diff:.2e})")


def test_tau_63_percent_rule():
    """
    W0_foundations.md Q1: t=tau일 때 최종값의 63.2%에 도달해야 한다.
    """
    R1, C1 = 0.02, 100.0
    tau1 = R1 * C1  # 2.0s
    params = ECMParameters(R0=0.0, R1=R1, C1=C1, R2=1e-9, C2=1e-9, Q_Ah=3.0)
    ecm = ECM(params)

    dt = 0.001
    t = np.arange(0, 20, dt)
    I = np.full_like(t, 1.0)
    result = ecm.simulate(t, I, soc0=0.5)

    idx_tau = int(tau1 / dt)
    v_at_tau = result["v_rc1"][idx_tau]
    v_final = 1.0 * R1  # I*R

    ratio = v_at_tau / v_final
    assert abs(ratio - 0.632) < 0.01, f"63.2% 규칙 불일치: {ratio}"
    print(f"PASS: t=tau에서 {ratio*100:.1f}% 도달 (기대값 63.2%)")


def test_soc_decreases_on_discharge():
    """SOC가 방전 시 감소하고, 쿨롱카운팅이 대략 맞는지 확인."""
    params = ECMParameters(R0=0.02, R1=0.01, C1=100.0, R2=0.005, C2=2000.0, Q_Ah=3.0)
    ecm = ECM(params)

    dt = 1.0
    duration_s = 3600.0  # 1시간
    t = np.arange(0, duration_s, dt)
    I = np.full_like(t, 3.0)  # 3A = 1C

    result = ecm.simulate(t, I, soc0=1.0)

    # 1C로 1시간 방전하면 이론상 SOC가 약 100% -> 0%
    final_soc = result["soc"][-1]
    assert final_soc < 0.05, f"1C 1시간 방전 후 SOC가 예상보다 높음: {final_soc}"
    print(f"PASS: 1C 1시간 방전 후 SOC={final_soc*100:.1f}% (기대: ~0%)")


def test_hppc_pulse_shape():
    """합성 HPPC 펄스가 의도한 구조(휴지-펄스-휴지)를 갖는지 확인."""
    dt = 0.1
    I = make_hppc_pulse_current(
        dt_s=dt, rest_before_s=5.0, pulse_s=10.0, rest_after_s=5.0,
        pulse_current_A=3.0,
    )
    n_rest = int(5.0 / dt)
    n_pulse = int(10.0 / dt)

    assert np.all(I[:n_rest] == 0.0)
    assert np.all(I[n_rest:n_rest + n_pulse] == 3.0)
    assert np.all(I[n_rest + n_pulse:] == 0.0)
    print("PASS: HPPC 펄스 프로파일 구조 검증")


def test_hysteresis_converges_to_h_max():
    """
    히스테리시스 상태가 지속적인 방전 시 -h_max로 수렴하는지 확인.
    수렴 시상수는 Q_As/(k*|I|)이므로, 이 시상수의 5배 이상(5tau, 99% 수렴)
    지속해야 한다 (W0_foundations.md Q1의 "5tau에서 99%" 규칙과 동일).
    """
    params = ECMParameters(R0=0.02, R1=0.01, C1=100.0, R2=0.005, C2=2000.0, Q_Ah=3.0)
    hyst = HysteresisModel(h_max_V=0.02, k=5.0)
    ecm = ECM(params, hysteresis=hyst)

    Q_As = params.Q_Ah * 3600.0
    I_mag = 1.0
    conv_tau = Q_As / (hyst.k * I_mag)  # 수렴 시상수
    duration = 6 * conv_tau  # 5tau 이상 확보 (99%+ 수렴)

    dt = 1.0
    t = np.arange(0, duration, dt)
    I = np.full_like(t, I_mag)  # 지속적 방전

    result = ecm.simulate(t, I, soc0=0.8)
    h_final = result["h"][-1]

    assert abs(h_final - (-0.02)) < 5e-4, f"히스테리시스 수렴 실패: {h_final}"
    print(f"PASS: 히스테리시스가 -h_max로 수렴 (h_final={h_final:.4f}, 소요={duration:.0f}s)")


if __name__ == "__main__":
    test_r0_instantaneous_drop()
    test_rc_step_response_matches_analytic()
    test_tau_63_percent_rule()
    test_soc_decreases_on_discharge()
    test_hppc_pulse_shape()
    test_hysteresis_converges_to_h_max()
    print("\n모든 테스트 통과.")
