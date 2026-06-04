## Phase 5. 피드백 루프

### 목적
Phase 4에서 REJECT 판정된 학습 컨텐츠에 대해 **learning-content-generator**를 재호출하고, **learning-content-reviewer**를 호출해 재검수한다.

3회의 재시도 안에 PASS로 전환되지 않으면, 해당 항목을 **manual-review**로 태깅한다.

### 선행 조건
- Phase 4가 완료된 후, 하나 이상의 유닛의 `review.md`에 REJECT가 존재한다.
- 작업 유닛에 대해 아래 두 파일이 존재한다.
  - `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
  - `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md`

### 참조 파일
- `.claude/spec/review/review-rubric.md` — REJECT 처리 정책

### 절차
1. REJECT 항목을 수집한다. 각 유닛의 `review.md`을 읽고 **lesson.verdict == REJECT**(레슨 난이도 조정), **problems[].verdict == REJECT**(문제 재생성)를 취합한다.
2. 재시도 로그를 생성한다. 아래 **재시도 로그 양식**에 따라 유닛별로, 레슨 블록과 문제 블록을 세션에 유지한다.
   - 문제 단위와 레슨 단위 카운터는 독립된다.
   - 파일로 저장하지 않으며, compaction 및 재시작 시, Phase 5 전체를 재실행한다.
3. 각 REJECT 항목별 피드백 루프
   - 시도 번호 ≤ 3
     - 문제, 레슨 단위별 인자를 확인한 후, **learning-content-generator**를 재호출한다.
       - 문제 단위:
         - **retry_mode** → **"problem"**
         - **target_refs** → **["p1", "p3", "p6"]** (검수가 내보낸 **problem_ref**, p1~p6)
       - 레슨 단위:
         - **retry_mode** → **"lesson_difficulty"**
         - **target_refs** → **"lesson"**
       - 공통
         - **mode** → **"retry"**
         - **review_path** → `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md`
         - **lesson_sql_path** → `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
         - **concept_note_path** → `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/concept-note.md`
         - **existing_problems_path** → `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/existing-problems.sql`
     - **learning-content-generator** 작업 종료 후, **learning-content-reviewer**를 아래 인자로 재호출하여 `review.md`를 업데이트한다.
       - **lesson_sql_path** → `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
       - **review_output_path** → `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md`
     - `review.md` 업데이트 결과에 따라 재시도 로그를 업데이트한다.
     - 모든 항목이 PASS라면 루프를 종료하고, 하나라도 REJECT라면 재시도한다.
   - 시도 번호 > 3
     - 3번의 재시도 후에도 REJECT인 항목은 **manual-review**를 태깅한다.(`lesson.sql` 상에서 주석으로 태깅)
     - 태깅 시, 재시도 로그 블록의 마지막 행을 **pipeline-state**의 **Manual Review**에 요약으로 작성한다. 양식은 아래와 같다.
       - 문제 단위: `- {unit_id}/{problem_ref}: 재시도 3회 초과 — {마지막 행 reject_reasons 요약}`
       - 레슨 단위: `- {unit_id}/lesson: 난이도 조정 3회 초과 — {마지막 행 improvement_direction 요약}`
4. **pipeline-state**를 업데이트한다.
   - **current_phase** → 5
   - **Checklist**의 모든 유닛의 **phase_5** → ✅
5. **Log**에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_5] resolved {통과 항목 수}, manual-review {미해소 항목 수}**

### 출력
- 갱신된 `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
- 갱신된 `pipeline-workspace/review-output/{오늘 날짜}/{unit_id}/review.md`

### 실패 처리
- Phase 5 진입 시 REJECT가 없으면 즉시 종료하고 Phase 7로 이동(manual-review 항목이 없으므로 Phase 6 건너뜀).

### 다음 phase
- **pipeline-state**의 **Manual Review**에 항목이 **하나 이상** 있으면 → Phase 6
- **Manual Review**가 **비어 있으면**(3회 재시도 내 전부 PASS 전환) → Phase 6을 건너뛴다. **Checklist의 모든 유닛 phase_6을 ⏭로 표기**한 뒤 Phase 7로 이동.

### 재시도 로그 양식 (세션 보유)

```markdown
#### 레슨 블록 — `{unit_id}`

| 시도 번호 | 시점 | reject_reasons | improvement_direction | verdict |
|---|---|---|---|---|
| 1 | `<ISO8601>` | `R6: <사유>` | `<방향>` | REJECT |
| 2 | ... | ... | ... | PASS |

#### 문제 블록 — `{unit_id}` / `{problem_ref}`

| 시도 번호 | 시점 | reject_reasons | improvement_direction | verdict |
|---|---|---|---|---|
| 1 | `<ISO8601>` | `R1: <사유>`, `R3: <사유>` | `R1: <방향>`, `R3: <방향>` | REJECT |

- 시도 번호는 1부터, 최대 3.
- `reject_reasons`·`improvement_direction` 셀은 `R코드: 요약`을 쉼표로 연결. 합산 사유는 `avg: <요약>`.
- 마지막 행 verdict가 PASS면 해당 항목 종료. 시도 3 후에도 REJECT면 manual-review.
```