## Phase 3. 콘텐츠 생성

### 목적
각 유닛별로 **learning-content-generator** 서브에이전트를 병렬로 호출한다.

한 유닛당 한 레슨을 생성한다.

### 선행 조건
- **pipeline-state**의 **ID Baseline**이 할당되어 있고, **Checklist**의 이전 Phase가 모두 ✅ 상태이다.
- 아래 파일이 유닛별로 존재한다.
  - `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/concept-note.md`
  - `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/existing-problems.sql`

### 참조 파일
- `.claude/spec/generation/id-management.md`

### 절차
1. **재실행 가드.** 유닛별 `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` 파일이 이미 존재하는지 확인한다. 존재하는 유닛이 하나 이상이면, 해당 유닛 목록을 사용자에게 제시하고 `[덮어쓰기 / 보존하고 skip]` 중 선택을 받는다.
   - **덮어쓰기** → 해당 유닛도 생성 대상에 포함한다.
   - **보존하고 skip** → 해당 유닛은 이번 Phase 3에서 제외하고 **Checklist.phase_3 = ✅**를 유지한다.
2. 타겟 유닛별로 ID의 범위를 사전에 할당한다. `id-management.md`의 **Lesson 1개당 ID 소비량**과 **ID Baseline**을 참고하여 각 유닛에 배정한다. **보존하고 skip** 처리된 유닛은 ID 할당에서 제외한다.
3. 타겟 유닛별로 **learning-content-generator** 서브에이전트를 병렬로 호출한다. 인자는 아래와 같다.
   - **mode** → **"initial"**
   - **unit_id** → 타겟 유닛 ID
   - **label** → **pipeline-state.Meta.labels[unit_id]** (Phase 1에서 발급)
   - **concept_note_path** → `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/concept-note.md`
   - **existing_problems_path** → `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/existing-problems.sql`
   - **id_allocation** → 이전 단계에서 분할, 배정한 ID 범위
   - **output_path** → `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
4. 각 서브에이전트가 인자로 넘긴 output_path에 파일을 생성하였는지 확인한다.
5. **pipeline-state**를 업데이트한다.
   - **current_phase** → 3
   - **Checklist**의 각 유닛의 **phase_3** → ✅(검증 성공 시) / ❌(검증 실패) / 이전 ✅ 유지(보존하고 skip)
6. **Log**에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_3] generated lessons for units {성공 유닛 목록}, preserved {skip 유닛 목록}, failed {실패 유닛 목록}**

### 출력
- `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` (유닛별, 성공 시)

### 실패 처리
- 서브에이전트 호출 실패 또는 생성해야 할 파일 누락 시, 같은 인자로 최대 3회 재시도한다.
- 재시도 3회를 모두 실패한 유닛은 **pipeline-state**의 **Checklist.phase_3**를 ❌로 기록하고, 나머지 성공 유닛만 다음 Phase를 진행한다.
- 모든 유닛이 실패한 경우, **pipeline-state**의 **status**를 **FAILED**로 업데이트한 뒤 종료한다. 

### 다음 phase
- Phase 4 (성공 유닛만 대상).
