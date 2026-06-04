## Phase 4. 콘텐츠 검수

### 목적
Phase 3이 생성한 학습 컨텐츠를 **learning-content-reviewer** 서브에이전트가 **review-rubric** 기준으로 채점하여 PASS/REJECT를 판정한다.

### 선행 조건
- **pipeline-state**의 **Checklist.phase_3**에서 1개 이상의 유닛이 ✅ 상태이다.
- `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` 파일이 존재한다.

### 참조 파일
없음

### 절차
0. (재실행 가드) 유닛별로 `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md` 파일이 존재하는지 확인한다. 존재하는 유닛이 하나 이상이라면, 사용자에게 해당 유닛에 대한 [덮어쓰기/보존 후 skip] 중 선택을 받는다.
   - **덮어쓰기** → 해당 유닛도 검수 대상에 포함한다.
   - **보존 후 skip** → 해당 유닛은 이번 Phase에서 제외하고 **Checklist.phase_4**를 ✅ 로 유지한다.
1. Phase 3 성공 유닛 중 skip되지 않은 유닛별로 **learning-content-reviewer** 서브에이전트를 병렬로 호출한다. 인자는 아래와 같다.
   - **lesson_sql_path** → `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
   - **review_output_path** → `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md`
2. 각 유닛의 `review.md` 생성 여부를 확인한다.
3. **pipeline-state**를 업데이트한다.
   - **current_phase** → 4
   - **Checklist**의 각 유닛의 **phase_4** → ✅(검증 성공) / ❌(검증 실패) / 이전 ✅ 유지(보존하고 skip)
4. **Log**에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_4] reviewed units {성공 유닛 목록}, preserved {skip 유닛 목록}, failed {실패 유닛 목록}**.

### 출력
- `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md` (유닛별)

### 실패 처리
- 서브에이전트 호출 실패 또는 생성해야 할 파일 누락 시, 같은 인자로 최대 3회 재시도한다.
- 재시도 3회를 모두 실패한 유닛은 **pipeline-state**의 **Checklist.phase_4**를 ❌로 기록하고, 나머지 성공 유닛만 다음 Phase를 진행한다.
- 모든 유닛이 실패한 경우, **pipeline-state**의 **status**를 **FAILED**로 업데이트한 뒤 종료한다.

### 다음 phase
- 모든 학습 컨텐츠가 검수 기준에 PASS라면 → Phase 5·6을 건너뛴다. **Checklist의 모든 유닛 phase_5·phase_6을 ⏭로 표기**한 뒤 Phase 7로 이동.
- 하나의 학습 컨텐츠라도 REJECT라면 → Phase 5
