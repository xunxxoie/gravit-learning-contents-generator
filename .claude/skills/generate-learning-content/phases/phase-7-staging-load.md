## Phase 7. staging 적재

### 목적
각 유닛의 `lesson.sql`을 운영 데이터베이스의 **_staging** 테이블에 적재한다.

### 선행 조건
- **pipeline-state**의 **Checklist.phase_6**가 모두 ✅ 또는 ⏭ 이다 (Phase 6 실행 또는 건너뜀).
- **pipeline-state**의 **Manual Review**가 비어있다.
- 프로젝트 루트의 `.env`에 **DATABASE_URL**이 설정되어 있다.

### 참조 파일
- `.claude/spec/generation/learning-content-sql-schema.md` — **_staging** 테이블 정의
- `pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql` — 적재 입력

### 절차
1. **Checklist**에서 **phase_6**가 ✅ 또는 ⏭인 유닛을 모두 수집한다.
2. `.env`를 로드한다. **DATABASE_URL**이 비어있으면 즉시 중단하고 사용자에게 보고한다.
3. 각 유닛에 대해 아래를 실행한다.
   - `psql "$DATABASE_URL" --single-transaction -v ON_ERROR_STOP=1 -f pipeline-workspace/generation-output/{오늘 날짜}/{unit_id}/lesson.sql`
4. **pipeline-state**를 업데이트한다.
   - **current_phase** → 7
   - **Checklist[unit].phase_7** → ✅ (성공시) / ❌ 실패시
   - **status** → **COMPLETED**(모든 유닛 처리 성공 시) / **FAILED**(일부 유닛 실패 시)
5. **Log**에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_7] loaded to staging for units {성공 유닛 목록}, failed {실패 유닛 목록}**

### 출력
없음

### 실패 처리
- `.env` 또는 **DATABASE_URL** 누락 시 즉시 중단, 사용자에게 보고.

### 다음 phase
- 없음. 파이프라인 종료.

