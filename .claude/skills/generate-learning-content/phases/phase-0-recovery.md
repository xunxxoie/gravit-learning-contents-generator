## Phase 0. 복구 확인 및 연결 점검

### 목적
DB 연결 가능 여부를 확인한 뒤, 오늘 중단된 파이프라인이 있으면 그 지점부터 재개하고, 없으면 새로 시작한다.

### 선행 조건
- 프로젝트 루트의 `.env`에 **DATABASE_URL**이 설정되어 있다.
- 원격 DB로 접근 가능한 SSH 터널이 열려 있다 (예: **ssh -L 5433:localhost:5432 ...**).

### 참조 파일
- `.claude/spec/generation/id-management.md`

### 절차
1. **DB 연결 체크.** `.env`를 로드하고 **psql "$DATABASE_URL" -c "SELECT 1"**로 연결을 확인한다.
   ```
   set -a && . ./.env && set +a
   [ -z "$DATABASE_URL" ] && { echo ".env에 DATABASE_URL이 없습니다" >&2; exit 1; }
   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT 1" >/dev/null
   ```
   실패 시 즉시 중단하고 사용자에게 **SSH 터널(5433)이 떠있는지 보고한다.
2. `pipeline-workspace/pipeline-state-{오늘 날짜}-*.md` 패턴 파일들 중 frontmatter **status: IN_PROGRESS**인 파일을 추린다.
   - 0개 → Phase 1로 이동.
   - 1개 → 그 파일을 **active_state**로 지정하고 단계 3으로 진행.
   - 2개 이상 → 사용자에게 파일 목록을 보여주고 어느 파일로 재개할지 확인을 구한 뒤 **active_state**를 결정한다.
3. **active_state** 파일을 읽고, **Checklist**에서 ⏳ 또는 ❌ 로 표기된 가장 이른 Phase 번호를 찾아 이를 **resume_phase**로 기록한다.
4. **resume_phase > 2**인 경우 **ID Baseline만 갱신**한다.
   - **fetch-max-id**를 호출하여 **last_lesson_id**, **last_problem_id**, **last_option_id**, **last_answer_id**, **last_label_id**를 재조회한다.
   - **active_state**의 **ID Baseline**을 갱신한다.
   - **Log**에 **- {ISO8601} [phase_0] id baseline refreshed on resume**를 작성한다.
   - 아래 파일은 재사용한다.
     - `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/concept-note.md`
     - `pipeline-workspace/fetch-cache/{오늘 날짜}/{unit_id}/existing-problems.sql`
5. **resume_phase**로 설정된 Phase로 이동한다.

### 출력
없음

### 실패 처리
없음

### 다음 phase
- **active_state**가 결정된 경우 → Phase **resume_phase**로 이동한다.
- **IN_PROGRESS** 파일이 0개인 경우 → Phase 1로 이동한다.