---
description: pipeline-state 파일의 고정 스키마(메타·ID Baseline·Checklist·로그)와 상태 기호·복구 판단 기준.
---

## pipeline-state 파일 스키마

`pipeline-workspace/pipeline-state-{YYYY-MM-DD}-{seq}.md`는 아래 고정 구조를 따른다 (**seq**는 같은 날 1부터 증가).

### 템플릿

````markdown
---
date: YYYY-MM-DD
status: IN_PROGRESS | COMPLETED | FAILED
current_phase: 0
---

## Meta
- target_units: [unit_id, ...]
- max_retry_per_problem: 3
- labels:
  - {unit_id}: {YYYY-MM-DD}-{4자}
  - ...

## ID Baseline
- last_lesson_id: {n}
- last_problem_id: {n}
- last_option_id: {n}
- last_answer_id: {n}
- last_label_id: {n}

## Checklist
| unit_id | phase_2 | phase_3 | phase_4 | phase_5 | phase_6 | phase_7 |
|---------|---------|---------|---------|---------|---------|---------|
| {id}    | ⏳      | ⏳      | ⏳       | ⏳      | ⏳      | ⏳      |

## Manual Review
- {unit_id}/{problem_ref}: 재시도 3회 초과 — {마지막 감점 요약}

## Log
- {ISO8601} [phase_{n}] {event}
````

---

### 상태 기호
- ✅ 완료
- ⏳ 진행 중 / 예정
- ❌ 실패
- ⏭ 건너뜀 (전부 PASS로 Phase 5·6 생략, Manual Review 없이 Phase 6 생략 등)

### 복구 판단
- **status: COMPLETED**이면 같은 날짜로 재시작하지 말고 사용자에게 확인을 구한다.
- **current_phase**는 사람이 읽는 진행 표시용이다. 복구의 권위 있는 신호는 **Checklist**(가장 이른 ⏳/❌ phase)이며, current_phase로 재개 지점을 정하지 않는다.
