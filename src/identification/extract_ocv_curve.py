"""
C/20 완속 충방전 데이터에서 OCV(SOC) 곡선 추출

이론적 배경: docs/02_theory/W3_parameter_identification.md M3.2
("저율 사이클법: C/20으로 완충-완방, 충전곡선과 방전곡선의 평균으로
히스테리시스 상쇄")

이 파일이 하는 일:
1. C20DisCh CSV에서 방전 구간과 충전 구간을 Status 컬럼으로 분리
2. 각 구간에서 쿨롱카운팅으로 SOC를 계산 (samsung_loader의
   방식과 동일 원리 - hppc.py의 coulomb_count_soc 재사용)
3. 방전곡선 V(SOC)와 충전곡선 V(SOC)를 같은 SOC 격자로 보간
4. 두 곡선의 평균 = OCV(SOC) 근사값
5. ecm.py의 ocv_fn 인자로 바로 쓸 수 있는 보간 함수로 포장

한계 (W3_parameter_identification.md M3.2에 이미 명시):
이 평균법은 히스테리시스가 좌우 대칭에 가까울 때만 잘 통하는 근사다.
비대칭이 크면(Si 음극 등) 잔차가 남는다. 이 코드는 그 잔차 크기도
같이 보고해, 근사가 이 셀에서 얼마나 타당한지 정량적으로 보여준다.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
from scipy.interpolate import interp1d

from src.identification.samsung_loader import load_hppc_csv
from src.identification.extract_soc_table import coulomb_count_soc


def split_charge_discharge(status: np.ndarray, voltage: np.ndarray,
                            current_A: np.ndarray, time_s: np.ndarray,
                            soc: np.ndarray):
    """
    Status 컬럼으로 방전/충전 구간을 분리한다. 인덱스를 하드코딩하지
    않고 실제 상태값을 보고 찾는 것이 다른 온도/파일에도 안전하다.
    """
    dch_mask = status == "DCH"
    cha_mask = status == "CHA"

    if not dch_mask.any() or not cha_mask.any():
        raise ValueError("DCH 또는 CHA 구간을 찾지 못했다 - 파일이 "
                          "완전 충방전 사이클을 포함하는지 확인할 것")

    return {
        "discharge": {"soc": soc[dch_mask], "voltage": voltage[dch_mask]},
        "charge": {"soc": soc[cha_mask], "voltage": voltage[cha_mask]},
    }


def build_ocv_curve(
    time_s: np.ndarray,
    voltage: np.ndarray,
    current_A: np.ndarray,
    status: np.ndarray,
    Q_Ah: float,
    n_grid: int = 101,
    soc_start: float = 1.0,
) -> dict:
    """
    전체 C20 시계열에서 OCV(SOC) 곡선을 추출한다.

    Returns
    -------
    dict:
        soc_grid: 균일 SOC 격자 (n_grid개)
        ocv_discharge, ocv_charge: 각 방향의 곡선 (soc_grid 위로 보간됨)
        ocv_mean: 평균 (이게 최종 OCV 근사값)
        hysteresis: charge - discharge (M3.2에서 말한 히스테리시스 잔차)
        ocv_fn: soc를 넣으면 ocv_mean을 보간해 돌려주는 함수
                (ecm.py의 ocv_fn 인자로 바로 사용 가능)
    """
    soc = coulomb_count_soc(time_s, current_A, Q_Ah, soc_start=soc_start)
    parts = split_charge_discharge(status, voltage, current_A, time_s, soc)

    soc_grid = np.linspace(0.0, 1.0, n_grid)

    # 방전은 SOC가 감소하는 방향으로 기록되어 있어 interp1d가 요구하는
    # "오름차순 x" 조건을 맞추려면 정렬이 필요하다.
    def to_grid(soc_arr, v_arr):
        order = np.argsort(soc_arr)
        soc_sorted = soc_arr[order]
        v_sorted = v_arr[order]
        # 중복 SOC(같은 값 여러 개) 제거 - interp1d가 단조증가를 요구
        soc_unique, idx_unique = np.unique(soc_sorted, return_index=True)
        v_unique = v_sorted[idx_unique]
        f = interp1d(soc_unique, v_unique, bounds_error=False,
                     fill_value=(v_unique[0], v_unique[-1]))
        return f(soc_grid)

    ocv_dis = to_grid(parts["discharge"]["soc"], parts["discharge"]["voltage"])
    ocv_cha = to_grid(parts["charge"]["soc"], parts["charge"]["voltage"])
    ocv_mean = (ocv_dis + ocv_cha) / 2.0
    hysteresis = ocv_cha - ocv_dis

    ocv_fn = interp1d(soc_grid, ocv_mean, bounds_error=False,
                       fill_value=(ocv_mean[0], ocv_mean[-1]))

    return {
        "soc_grid": soc_grid,
        "ocv_discharge": ocv_dis,
        "ocv_charge": ocv_cha,
        "ocv_mean": ocv_mean,
        "hysteresis": hysteresis,
        "ocv_fn": ocv_fn,
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "data/raw/samsung_30t/25degC/729_C20DisCh.csv"

    data = load_hppc_csv(path)
    # 부호 반전은 samsung_loader.py의 load_hppc_csv 안에서 단 한 곳에서만
    # 처리한다(단일 책임 원칙). 여기서 또 반전하면 이중반전으로 부호가
    # 원본(방전=음수)으로 도로 돌아가는 버그가 생긴다 - 실제로 발생했던
    # 문제이며 docs/00_learning_log.md에 기록되어 있다.
    current_A = data.current_A

    result = build_ocv_curve(
        data.time_s, data.voltage, current_A, data.status, Q_Ah=3.0,
    )

    print("SOC(%)   방전전압   충전전압   평균(OCV)   히스테리시스(mV)")
    for i in range(0, len(result["soc_grid"]), 10):
        soc = result["soc_grid"][i]
        print(f"{soc*100:5.1f}   {result['ocv_discharge'][i]:.4f}    "
              f"{result['ocv_charge'][i]:.4f}    {result['ocv_mean'][i]:.4f}    "
              f"{result['hysteresis'][i]*1000:+.2f}")

    print()
    print("최대 히스테리시스:", np.max(np.abs(result["hysteresis"])) * 1000, "mV")
    print("평균 히스테리시스:", np.mean(np.abs(result["hysteresis"])) * 1000, "mV")

    # 저장 - ecm.py의 ocv_fn으로 쓸 수 있는 표 형태
    import pandas as pd
    out_df = pd.DataFrame({
        "soc": result["soc_grid"],
        "ocv_discharge": result["ocv_discharge"],
        "ocv_charge": result["ocv_charge"],
        "ocv_mean": result["ocv_mean"],
        "hysteresis_V": result["hysteresis"],
    })
    out_path = "data/processed/25degC_ocv_curve.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"\n저장: {out_path}")