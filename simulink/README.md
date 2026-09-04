# simulink — W8 MIL 검증용

W8(제품화)에서 ECM+EKF를 Simulink로 재구현하고, Embedded Coder로
생성한 C 코드를 Python 결과와 대조(SIL에 준하는 검증)합니다.

## 계획 파일 (W8 진행 시 추가)

- `ecm_ekf.slx`: 메인 모델
- `generated_code/`: Embedded Coder 생성 코드 (참고용, 대용량이면 커밋 제외)

현재는 W1-7 완료 전까지 비어 있습니다.
