"""
동적(SOC-의존) ECM 시뮬레이터

이론적 배경: W3_parameter_identification.md ("SOC별 룩업테이블"),
W1_ecm_code.md ("OCV 함수를 갈아 끼울 수 있게 설계한 이유"와 같은 원리를
R0/R1/C1에도 확장)

기존 ecm.py의 ECM 클래스는 R0/R1/C1이 "생성 시점에 고정된 스칼라"라는
전제로 만들어졌다(검증된 코드, 회귀 위험을 피하려 건드리지 않는다).
이 파일은 ecm.py를 고치는 대신, 그 위에 "매 스텝마다 그 순간 SOC로
파라미터를 다시 조회하는" 새 시뮬레이션 루프를 얹는다.

이게 가능한 이유: ECM.discretize_zoh()와 ECM.output_voltage()는 둘 다
호출될 때마다 self.p(파라미터 봉투)를 그 자리에서 읽는다. 즉 시뮬레이션
도중 self.p를 다른 값으로 바꿔 끼우면, 그 다음 호출부터는 새 값을
자동으로 쓰게 된다 - ecm.py 내부 코드는 한 글자도 안 바꿨다.

한계 (현재 범위):
- 1RC까지만 지원 (R2, C2는 parameter_lookup.py와 마찬가지로 사실상
  없는 값으로 고정). 2RC 확장은 다음 과제.
- 온도는 25도로 고정 (룩업테이블 자체가 25도 데이터만 가지고 있음).
- 매 스텝 discretize_zoh를 다시 계산하므로, 고정 파라미터 버전보다
  느리다. 오프라인 분석 용도로는 문제없지만, 실시간/임베디드 용도로는
  최적화가 더 필요하다(W8에서 다룰 주제).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np

from src.models.ecm import ECM, ECMParameters, HysteresisModel
from src.identification.parameter_lookup import ECMParameterLookup


def simulate_dynamic(
    lookup: ECMParameterLookup,
    time_s: np.ndarray,
    current_A: np.ndarray,
    soc0: float = 1.0,
    Q_Ah: float = 3.0,
    hysteresis: "HysteresisModel | None" = None,
    coulombic_efficiency: float = 1.0,
) -> dict:
    """
    SOC에 따라 R0/R1/C1이 실시간으로 갱신되는 시뮬레이션.

    ecm.py의 ECM.simulate()와 인터페이스는 거의 같지만, 내부적으로
    매 스텝마다 lookup으로부터 그 순간 SOC에 맞는 파라미터를 새로
    가져와 self.p를 갈아 끼운 뒤 계산한다.

    Parameters
    ----------
    lookup : parameter_lookup.py의 ECMParameterLookup 인스턴스
    time_s, current_A : 시뮬레이션할 전류 프로파일 (방전=양수)
    soc0 : 시작 SOC
    Q_Ah : 총 용량 (룩업테이블 자체와는 별개로, 쿨롱카운팅 스케일에 사용)

    Returns
    -------
    dict: soc, voltage, r0_used, r1_used, c1_used 시계열
          (r0_used 등은 "이 스텝에서 실제로 쓰인 파라미터값" - 검증/
          진단용으로 남겨둔다)
    """
    n = len(time_s)
    dt = float(time_s[1] - time_s[0])

    # 초기 파라미터로 ECM 골격 하나를 만든다. ocv_fn은 룩업테이블의
    # OCV 함수를 그대로 사용 - SOC가 바뀌어도 자동으로 그 SOC에 맞는
    # OCV를 계산해주므로(W1_ecm_code.md에서 이미 이렇게 설계해둔 부분),
    # OCV는 매 스텝 self.p를 안 바꿔도 된다. R0/R1/C1만 바꿔주면 된다.
    init_params = lookup.snapshot_at(soc0, Q_Ah=Q_Ah)
    ecm = ECM(
        init_params,
        ocv_fn=lookup.OCV,
        ocv_slope_fn=lookup.OCV_slope,
        hysteresis=hysteresis,
        coulombic_efficiency=coulombic_efficiency,
    )

    state = np.array([soc0, 0.0, 0.0])
    h = 0.0

    soc_hist = np.zeros(n)
    voltage_hist = np.zeros(n)
    r0_hist = np.zeros(n)
    r1_hist = np.zeros(n)
    c1_hist = np.zeros(n)

    for k in range(n):
        current_soc = state[0]

        # 핵심: 이 순간 SOC로 파라미터를 다시 조회해 self.p를 갈아 끼운다.
        # ecm.py 코드는 그대로, self.p라는 "봉투"만 매번 새로 채운다
        # (W1_ecm_code.md의 ocv_fn 교체 설계와 같은 원리를 R0/R1/C1까지 확장한 것).
        ecm.p = lookup.snapshot_at(current_soc, Q_Ah=Q_Ah)

        I = current_A[k]
        voltage_hist[k] = ecm.output_voltage(state, I, h)
        soc_hist[k] = current_soc
        r0_hist[k] = ecm.p.R0
        r1_hist[k] = ecm.p.R1
        c1_hist[k] = ecm.p.C1

        # 이 스텝의 파라미터로 이산화 (매 스텝 다시 계산 - 정적 버전과의 차이)
        Ad, Bd = ecm.discretize_zoh(dt)
        state = Ad @ state + (Bd.flatten() * I)
        state[0] = np.clip(state[0], 0.0, 1.0)

        if ecm.hysteresis is not None:
            h = h + ecm.hysteresis.dhdt(h, I, Q_Ah) * dt

    return {
        "soc": soc_hist,
        "voltage": voltage_hist,
        "r0_used": r0_hist,
        "r1_used": r1_hist,
        "c1_used": c1_hist,
    }


if __name__ == "__main__":
    # 검증: 1C로 SOC 100%에서 계속 방전시키며, 쓰인 R0가 룩업테이블의
    # 값과 SOC 구간별로 일치하는지 확인 (직접 재조회해서 대조)
    lookup = ECMParameterLookup(
        "data/processed/25degC_hppc_params.csv",
        "data/processed/25degC_ocv_curve.csv",
    )

    Q_Ah = 3.0
    dt = 60.0  # 1분 간격
    duration_s = 3.0 * 3600 / (Q_Ah / 20)  # 대략 SOC가 0 근처까지 가도록 여유있게
    n = int(3.0 * 3600 / 1.0 / dt)  # 1A로 3시간(=SOC 약 100%->0%, C/1 방전)
    time_s = np.arange(n) * dt
    current_A = np.full(n, 1.0)  # 약 C/3 방전 (완만하게 SOC 변화 관찰)

    result = simulate_dynamic(lookup, time_s, current_A, soc0=1.0, Q_Ah=Q_Ah)

    print("시간에 따른 SOC, 전압, 그 순간 쓰인 R0:")
    for i in range(0, n, max(1, n // 15)):
        soc = result["soc"][i]
        print(f"  t={time_s[i]/3600:5.2f}h  SOC={soc*100:5.1f}%  "
              f"V={result['voltage'][i]:.4f}  R0_used={result['r0_used'][i]:.5f}  "
              f"(lookup 재조회={lookup.R0(soc):.5f})")

    # 교차검증: 시뮬레이션 도중 실제 쓰인 R0가 룩업테이블에서 그 SOC로
    # 다시 조회한 값과 정확히 같은지 (같아야 정상 - 다르면 버그)
    mismatch = np.abs(result["r0_used"] - np.array([lookup.R0(s) for s in result["soc"]]))
    print(f"\nR0 일치성 검증 - 최대 불일치: {mismatch.max():.2e} (0에 가까워야 정상)")