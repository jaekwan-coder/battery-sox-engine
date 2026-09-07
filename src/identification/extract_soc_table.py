"""
실측 HPPC 데이터에서 SOC별 R0/R1/C1 표(파라미터 표면) 추출

이론적 배경: docs/02_theory/W3_parameter_identification.md M3.3
("SOC 10%씩 내려가며 반복 -> R0(SOC), R1(SOC), C1(SOC) 룩업테이블")

이 스크립트가 하는 일 (순서):
1. samsung_loader.load_hppc_csv로 원본 CSV를 읽는다 (부호 반전 반영 필요,
   src/identification/samsung_loader.py의 load_hppc_csv 함수 안에서
   처리하도록 사용자가 직접 한 줄 추가한 상태를 전제로 한다)
2. 자체 쿨롱카운팅으로 각 시점의 근사 SOC를 계산한다
   (W3_parameter_identification.md M3.0: 실험실 데이터는 정밀 장비로
   측정되어 쿨롱카운팅을 신뢰할 수 있다는 논리를 그대로 적용)
3. find_pulse_edges로 모든 펄스를 찾는다
4. 각 펄스마다 extract_hppc_parameters를 시도한다 (실패하는 펄스는
   건너뛰고 이유를 기록 - 실측 데이터는 합성 데이터와 달리 전부
   성공하지 않을 수 있음을 W3 문서에서 이미 예상했다)
5. 결과를 SOC 순으로 정렬한 표로 만들어 CSV로 저장한다

실행 방법:
    PYTHONPATH=. python3 src/identification/extract_soc_table.py \
        data/raw/samsung_30t/25degC/729_HPPC.csv \
        data/processed/25degC_hppc_params.csv
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd

from src.identification.samsung_loader import load_hppc_csv
from src.identification.hppc import find_pulse_edges, extract_hppc_parameters


def coulomb_count_soc(time_s: np.ndarray, current_A: np.ndarray, Q_Ah: float,
                       soc_start: float = 1.0) -> np.ndarray:
    """
    자체 쿨롱카운팅으로 시간에 따른 SOC를 근사 계산한다.
    current_A는 방전=양수 규약(ecm.py와 동일)을 따른다고 가정한다.

    W3_parameter_identification.md M3.0 논리 그대로: 이 데이터는 실험실
    정밀 장비(0.1% FS 정확도)로 짧은 시간(34시간) 동안 측정된 것이므로,
    쿨롱카운팅 표류가 무시할 수준이라 참값으로 취급할 수 있다.

    사다리꼴 적분(trapezoid)을 사용 - ecm.py의 discretize_zoh에서
    SOC를 직사각형 근사로 처리한 것보다 이쪽이 더 정밀하다(여기서는
    실시간 재귀 계산이 아니라 사후 일괄 계산이라 더 나은 방법을
    골라도 비용 문제가 없다).
    """
    ah_discharged = np.concatenate([[0.0], np.cumsum(
        (current_A[1:] + current_A[:-1]) / 2.0 * np.diff(time_s) / 3600.0
    )])
    soc = soc_start - ah_discharged / Q_Ah
    return soc


def extract_soc_parameter_table(
    time_s: np.ndarray,
    voltage: np.ndarray,
    current_A: np.ndarray,
    Q_Ah: float,
    min_pulse_current_A: float = 0.5,
    min_pulse_duration_s: float = 1.0,
    max_pulse_duration_s: float = 60.0,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    전체 시계열에서 찾을 수 있는 모든 펄스에 대해 R0/R1/C1을 추출하고,
    각 펄스 시작 시점의 SOC와 함께 표로 정리한다.

    실측 Samsung 30T HPPC 데이터를 직접 확인한 결과(2026), find_pulse_edges가
    찾아내는 "펄스" 중에는 다음 두 종류의 비-특성화 구간이 섞여 있음이
    확인되었다:

    1. 길이 1초 미만의 극히 짧은 전류 스파이크(0.0초, 단일 샘플 수준).
       리턴 충전 직후 제어 전환 시점에 남는 찌꺼기로 추정되며, 데이터
       포인트가 사실상 없어 완화곡선 피팅이 실패하거나 물리적으로
       불가능한 값(C1<0 등)을 낸다.
    2. 길이 수백 초에 달하는 저전류 구간. 이는 HPPC 펄스가 아니라
       "다음 SOC 지점으로 실제 이동시키는" 구간이다(실측 예: 0.899A x
       591.2s = 0.148Ah = 3Ah 대비 약 4.9%, 정확히 SOC 5%p 이동과 일치).
       이 구간은 전류가 흐르는 동안 SOC 자체가 크게 변하므로, "즉시
       강하 + 완화"를 가정하는 HPPC 피팅 모델 자체가 맞지 않는다.

    min_pulse_duration_s, max_pulse_duration_s로 이 두 종류를 걸러내고,
    Readme에 명시된 실제 HPPC 펄스 길이(~10초)에 해당하는 구간만
    파라미터 추출 대상으로 삼는다. 걸러진 구간은 폐기하지 않고 별도로
    세어 보고한다 - 특히 긴 구간은 자체 쿨롱카운팅(coulomb_count_soc)에는
    이미 반영되어 있으므로 SOC 추적 자체에는 영향이 없다.

    min_pulse_current_A: 이보다 작은 전류의 "펄스"는 애초에 find_pulse_edges
    단계에서 걸러진다 (find_pulse_edges의 threshold로 전달).
    """
    soc_series = coulomb_count_soc(time_s, current_A, Q_Ah)

    edges = find_pulse_edges(current_A, threshold=min_pulse_current_A)
    if verbose:
        print(f"찾은 구간(펄스 후보) 개수: {len(edges)}")

    rows = []
    n_failed = 0
    n_too_short = 0
    n_too_long = 0
    for i, (start, end) in enumerate(edges):
        duration = time_s[end - 1] - time_s[start] if end > start else 0.0

        if duration < min_pulse_duration_s:
            n_too_short += 1
            continue
        if duration > max_pulse_duration_s:
            n_too_long += 1
            continue

        try:
            # 중요: pulse_edges를 명시적으로 넘겨서, 이 함수가 밖에서 찾은
            # edges(threshold=min_pulse_current_A 기준)와 반드시 같은
            # 번호 체계를 쓰게 한다. 이걸 안 넘기면 extract_hppc_parameters가
            # 내부에서 다른 threshold로 펄스를 다시 세어, pulse_index가
            # 전혀 다른 펄스를 가리키는 버그가 생긴다(실측 데이터로 확인됨).
            fit = extract_hppc_parameters(time_s, voltage, current_A,
                                           pulse_index=i, pulse_edges=edges)
            rows.append({
                "pulse_index": i,
                "soc_at_pulse_start": soc_series[start],
                "pulse_current_A": current_A[start],
                "pulse_duration_s": duration,
                "R0": fit.R0,
                "R1": fit.R1,
                "C1": fit.C1,
                "tau1_s": fit.tau1,
                "fit_rmse_V": fit.fit_rmse,
            })
        except Exception as e:
            n_failed += 1
            if verbose:
                print(f"  펄스 {i} (idx {start}-{end}, {duration:.1f}s) 추출 실패: {e}")
            continue

    if verbose:
        print(f"특성화 펄스로 채택: {len(rows)}개")
        print(f"제외 - 너무 짧음(<{min_pulse_duration_s}s, 찌꺼기 추정): {n_too_short}개")
        print(f"제외 - 너무 김(>{max_pulse_duration_s}s, SOC이동구간 추정): {n_too_long}개")
        print(f"추출 실패: {n_failed}개")

    df = pd.DataFrame(rows)
    if len(df) > 0:
        df = df.sort_values("soc_at_pulse_start", ascending=False).reset_index(drop=True)
    return df


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else \
        "data/raw/samsung_30t/25degC/729_HPPC.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else \
        "data/processed/25degC_hppc_params.csv"

    print(f"입력: {input_path}")
    data = load_hppc_csv(input_path)
    print(f"읽은 행 수: {data.n_rows}, 시간범위: {data.time_s[-1]/3600:.1f}시간")

    # Nominal Capacity(Readme 메타정보상 3Ah)를 총 용량으로 사용.
    # 더 정확히 하려면 별도 Cap_1C 시험 결과값으로 교체할 것(W3 그룹2 파일).
    Q_AH_NOMINAL = 3.0

    table = extract_soc_parameter_table(
        data.time_s, data.voltage, data.current_A, Q_Ah=Q_AH_NOMINAL,
    )

    if len(table) == 0:
        print("추출된 파라미터가 없다 — samsung_loader.py의 부호 반전이 "
              "적용되었는지, threshold 값이 적절한지 확인할 것.")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        table.to_csv(output_path, index=False)
        print(f"\n결과 저장: {output_path}")
        print(table.head(10).to_string(index=False))
