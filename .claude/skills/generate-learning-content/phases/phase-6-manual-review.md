## Phase 6. manual-review 해소

### 목적
Phase 5까지의 결과에서 **manual-review**로 태깅된 항목을 사용자와 대화로 순회하며 해소한다.

### 선행 조건
- **pipeline-state**의 **Manual Review** 섹션에 하나 이상의 항목이 있다.
- 해당 유닛의 `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`에 **-- manual-review: ...** 주석이 남아 있다.

### 참조 파일
- 현재 실행의 **pipeline-state** 파일 (`pipeline-workspace/pipeline-state-{오늘 날짜}-{seq}.md`) — **Manual Review** 섹션
- `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` — 수정 대상
- `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md` — 마지막 reject 사유·개선 방향 원천
- `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/concept-note.md` — 개념 근거

### 절차
1. **pipeline-state**의 **Manual Review** 항목을 순서대로 수집한다.
2. 각 항목에 대해 아래 인터랙션을 사용자가 **OK**를 응답할 때까지 반복한다.
   - 해당 유닛의 `lesson.sql`과 `review.md`를 읽는다.
   - 태깅된 블록(문제 또는 레슨)과 마지막 **reject_reasons**·**improvement_direction**을 근거로 수정안을 작성한다.
   - 사용자에게 제시한다. 형식은 아래와 같다.
     - **변경 전 → 변경 후**
     - 변경 근거 요약
   - 사용자 응답 분기:
     - **OK**
       - `lesson.sql`에 반영한 후, **manual-review** 주석을 제거한다.
       - **pipeline-state**에서 해당 항목을 제거한다.
     - **그 외**
       - 피드백을 반영해 다시 수정하여 제시한다.
3. 모든 항목이 해소되면 **pipeline-state**를 업데이트한다.
   - **current_phase** → 6
   - **Checklist**의 모든 유닛의 **phase_6** → ✅
   - **Manual Review** → 비움
4. **Log**에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_6] resolved {처리 항목 수} manual-review items**

### 출력
- 수정된 `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` (태깅 주석 제거)

### 실패 처리
- 재시작 시 **Manual Review**에 항목이 남아 있으면 Phase 6부터 재개한다.

### 다음 phase
- Phase 7