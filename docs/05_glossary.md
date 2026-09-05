# 용어집 (약어 풀이)

이 저장소에 등장하는 약어를 카테고리별로 정리합니다. 새 약어가
나올 때마다 추가합니다.

## 배터리 상태 (SOX)

| 약어 | 원어 | 뜻 |
|---|---|---|
| SOX | State of X | SOC·SOH·SOP의 통칭 |
| SOC | State of Charge | 충전 상태, 잔량 (%) |
| SOH | State of Health | 건강 상태, 새것 대비 열화 정도 |
| SOP | State of Power | 지금 뽑을 수 있는 출력 |
| DOD | Depth of Discharge | 방전 심도 (SOC의 반대 개념) |
| RUL | Remaining Useful Life | 잔여 수명 |
| BOL | Beginning of Life | 새 셀 상태 (수명 시작점) |
| EOL | End of Life | 수명 종료 기준 (보통 용량 70~80%) |

## 전압·회로

| 약어 | 원어 | 뜻 |
|---|---|---|
| OCV | Open Circuit Voltage | 개방회로전압, 전류 없을 때의 평형 전압 |
| ECM | Equivalent Circuit Model | 등가회로모델 |
| RC | Resistor-Capacitor | 저항-커패시터 병렬 조합 |
| EIS | Electrochemical Impedance Spectroscopy | 전기화학 임피던스 분광법 |
| SEI | Solid Electrolyte Interphase | 고체 전해질 계면 (음극 표면 막) |
| DRT | Distribution of Relaxation Times | 이완시간 분포 (겹친 반원 분해 기법) |

## 시험 방법

| 약어 | 원어 | 뜻 |
|---|---|---|
| HPPC | Hybrid Pulse Power Characterization | 펄스 기반 저항·동특성 측정 표준시험 |
| GITT | Galvanostatic Intermittent Titration Technique | 정전류 간헐 적정법 (정밀 OCV 측정) |
| CC-CV | Constant Current - Constant Voltage | 정전류-정전압 충전 프로토콜 |
| C-rate | — | 전류를 용량 대비 비율로 표현 (3Ah 셀에 3A = 1C) |
| ICA | Incremental Capacity Analysis | 증분용량 분석 (dQ/dV) |
| DVA | Differential Voltage Analysis | 미분전압 분석 (dV/dQ) |

## 열화

| 약어 | 원어 | 뜻 |
|---|---|---|
| LLI | Loss of Lithium Inventory | 리튬 재고 손실 |
| LAM | Loss of Active Material | 활물질 손실 |

**노화(aging) vs 열화(degradation)**: 노화는 시간에 따른 성능 저하라는
**현상(결과)**, 열화는 그 저하를 일으키는 구체적 **메커니즘(원인)**.

## 소재

| 약어 | 원어 | 뜻 |
|---|---|---|
| NMC | Nickel Manganese Cobalt oxide | 니켈-망간-코발트 양극재 (고용체 반응) |
| LFP | Lithium Iron Phosphate | 리튬인산철 양극재 (상전이 반응, 평탄 OCV) |
| NCA | Nickel Cobalt Aluminum oxide | 니켈-코발트-알루미늄 양극재 |
| Si | Silicon | 실리콘 음극재 (큰 히스테리시스) |

## 상태추정·필터

| 약어 | 원어 | 뜻 |
|---|---|---|
| KF | Kalman Filter | 칼만필터 |
| EKF | Extended Kalman Filter | 확장 칼만필터 (비선형용) |
| UKF | Unscented Kalman Filter | 무향 칼만필터 |
| SPKF | Sigma-Point Kalman Filter | 시그마포인트 칼만필터 (UKF와 유사) |
| AEKF | Adaptive EKF | 적응형 확장 칼만필터 |
| RLS | Recursive Least Squares | 재귀 최소자승법 |
| PE | Persistent Excitation | 지속적 여기 (파라미터 식별에 필요한 입력 다양성) |
| NIS | Normalized Innovation Squared | 정규화 혁신 제곱 (필터 일관성 검정) |
| GPR | Gaussian Process Regression | 가우시안 프로세스 회귀 |
| LM | Levenberg-Marquardt | 비선형 최소자승 알고리즘 |

## 전기화학 모델

| 약어 | 원어 | 뜻 |
|---|---|---|
| P2D | Pseudo-Two-Dimensional | 유사 2차원 모델 |
| DFN | Doyle-Fuller-Newman | P2D의 다른 이름 (제안자 이름) |
| SPM | Single Particle Model | 단일입자모델 |
| SPMe | SPM with electrolyte | 전해질 포함 단일입자모델 |
| ROM | Reduced-Order Model | 축소차수모델 |

## 개발·검증·안전

| 약어 | 원어 | 뜻 |
|---|---|---|
| BMS | Battery Management System | 배터리 관리 시스템 |
| ASIL | Automotive Safety Integrity Level | 자동차 기능안전 등급 (A~D) |
| AUTOSAR | AUTomotive Open System ARchitecture | 자동차 SW 표준 아키텍처 |
| MISRA | Motor Industry Software Reliability Association | 자동차 SW 코딩 표준 |
| MIL/SIL/PIL/HIL | Model/Software/Processor/Hardware-in-the-Loop | 검증 단계 |
| WCET | Worst-Case Execution Time | 최악 실행 시간 |
| MCU | Microcontroller Unit | 마이크로컨트롤러 |
| ADC | Analog-to-Digital Converter | 아날로그-디지털 변환기 |

## 규제·표준 기관

| 약어 | 원어 | 뜻 |
|---|---|---|
| UN GTR | UN Global Technical Regulation | UN 국제기술기준 |
| GB | 国家标准 (Guobiao) | 중국 국가표준 |
| NHTSA | National Highway Traffic Safety Administration | 미국 도로교통안전청 |
| IEC | International Electrotechnical Commission | 국제전기기술위원회 |
| SAE | Society of Automotive Engineers | 미국자동차공학회 |
| USABC | US Advanced Battery Consortium | 미국첨단배터리컨소시엄 (HPPC 출처) |
| DNV | Det Norske Veritas | 노르웨이 선급협회 |

## 주행 사이클

| 약어 | 원어 | 뜻 |
|---|---|---|
| UDDS | Urban Dynamometer Driving Schedule | 도심 주행 (잦은 정차·출발) |
| HWFET | Highway Fuel Economy Test | 고속도로 정상상태 주행 |
| US06 | (EPA 시험 코드) | 급가감속 극한 출력 |
| LA92 | Los Angeles 92 | 중속 가변 혼합 주행 |
| WLTP | Worldwide harmonized Light vehicles Test Procedure | 국제표준 경차량 시험법 |

## 차량·시스템

| 약어 | 원어 | 뜻 |
|---|---|---|
| EV / BEV | (Battery) Electric Vehicle | 전기차 |
| HEV | Hybrid Electric Vehicle | 하이브리드 전기차 |
| xEV | — | 전동화 차량 통칭 (BEV/HEV/PHEV 등) |
| ESS | Energy Storage System | 에너지 저장 시스템 |
| OEM | Original Equipment Manufacturer | 완성차 제조사 |

## 기타

| 약어 | 원어 | 뜻 |
|---|---|---|
| DC / AC | Direct / Alternating Current | 직류 / 교류 |
| FRA | Frequency Response Analyzer | 주파수 응답 분석기 (EIS 장비) |
| CNN / LSTM | Convolutional / Long Short-Term Memory NN | 신경망 구조 |
| PINN | Physics-Informed Neural Network | 물리정보 신경망 |
