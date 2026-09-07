"""
OCV(SOC) 곡선 시각화

extract_ocv_curve.py가 계산한 결과(방전/충전/평균 곡선, 히스테리시스)를
그래프로 그린다. 함수 형태로 만들어, 다른 온도 데이터가 추가되어도
같은 코드를 재사용할 수 있게 했다.

실행 방법:
    PYTHONPATH=. python3 src/identification/plot_ocv_curve.py \
        "data/raw/samsung_30t/25degC/729_C20DisCh.csv" \
        "docs/03_results/ocv_curve_25degc.png"
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import matplotlib
matplotlib.use("Agg")  # 화면 없는 환경(터미널)에서도 파일로 저장 가능하게
import matplotlib.pyplot as plt

from src.identification.samsung_loader import load_hppc_csv
from src.identification.extract_ocv_curve import build_ocv_curve


def plot_ocv_curve(csv_path: str, output_path: str, title_suffix: str = "") -> None:
    """
    C20DisCh CSV로부터 OCV(SOC) 곡선과 히스테리시스를 그려 저장한다.

    Parameters
    ----------
    csv_path : C20DisCh 원본 CSV 경로
    output_path : 저장할 PNG 경로
    title_suffix : 그래프 제목에 덧붙일 문구 (예: "25degC" — 다른
        온도 데이터를 그릴 때 구분용)
    """
    data = load_hppc_csv(csv_path)
    # 부호 반전은 samsung_loader.py 안에서 한 곳에서만 처리한다.
    # (중복 반전 버그 이력: docs/00_learning_log.md 참고)
    current_A = data.current_A

    result = build_ocv_curve(
        data.time_s, data.voltage, current_A, data.status, Q_Ah=3.0,
    )

    soc_pct = result["soc_grid"] * 100

    fig, axes = plt.subplots(
        2, 1, figsize=(9, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    axes[0].plot(soc_pct, result["ocv_discharge"], label="Discharge branch (C/20)",
                 color="steelblue", lw=1.8)
    axes[0].plot(soc_pct, result["ocv_charge"], label="Charge branch (C/20)",
                 color="indianred", lw=1.8)
    axes[0].plot(soc_pct, result["ocv_mean"], label="OCV estimate (average)",
                 color="black", lw=2.2, linestyle="--")
    axes[0].set_ylabel("Voltage [V]")
    title = "Samsung INR21700-30T — OCV(SOC)"
    if title_suffix:
        title += f" ({title_suffix})"
    title += "\n(from C/20 charge/discharge test)"
    axes[0].set_title(title)
    axes[0].legend(loc="lower right")
    axes[0].grid(alpha=0.3)

    axes[1].plot(soc_pct, result["hysteresis"] * 1000, color="darkorange", lw=1.8)
    axes[1].axhline(0, color="gray", lw=0.8)
    axes[1].fill_between(soc_pct, result["hysteresis"] * 1000, 0,
                          alpha=0.2, color="darkorange")
    axes[1].set_ylabel("Hysteresis [mV]\n(charge - discharge)")
    axes[1].set_xlabel("SOC [%]")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=140)
    plt.close(fig)
    print(f"저장 완료: {output_path}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else \
        "data/raw/samsung_30t/25degC/729_C20DisCh.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else \
        "docs/03_results/ocv_curve_25degc.png"
    title_suffix = sys.argv[3] if len(sys.argv) > 3 else "25degC"

    plot_ocv_curve(csv_path, output_path, title_suffix)