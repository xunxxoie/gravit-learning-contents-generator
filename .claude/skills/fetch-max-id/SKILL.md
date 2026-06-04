---
name: fetch-max-id
description: lesson/problem/option/answer/staging_label의 MAX ID를 집계하여 ID Baseline으로 반환한다.
allowed-tools: Bash
---

## fetch-max-id
운영 데이터베이스에서 prod 테이블(`lesson/problem/option/answer`)과 **staging_label**의 MAX ID를 조회하여 반환한다.

### 입력
없음

### 출력
- 표준 출력:
  ```
  last_lesson_id: {int}
  last_problem_id: {int}
  last_option_id: {int}
  last_answer_id: {int}
  last_label_id: {int}
  ```
- 테이블이 비어 있으면 해당 값은 0.

### 참조 파일
- `.claude/spec/generation/id-management.md`
- `.claude/spec/generation/learning-content-sql-schema.md`

### 절차

#### Phase 1. DATABASE_URL 로드
```
set -a && . ./.env && set +a
[ -z "$DATABASE_URL" ] && { echo "DATABASE_URL missing" >&2; exit 1; }
```

#### Phase 2. MAX ID 조회
**option**은 예약어이므로 쌍따옴표로 감싼다.

```
psql "$DATABASE_URL" -tAF'|' -v ON_ERROR_STOP=1 -c "
SELECT
  COALESCE((SELECT MAX(id) FROM lesson), 0),
  COALESCE((SELECT MAX(id) FROM problem), 0),
  COALESCE((SELECT MAX(id) FROM \"option\"), 0),
  COALESCE((SELECT MAX(id) FROM answer), 0),
  COALESCE((SELECT MAX(id) FROM staging_label), 0);
"
```

#### Phase 3. 출력 포맷 변환
```
IFS='|' read -r L P O A LB <<< "$RESULT"
printf 'last_lesson_id: %d\nlast_problem_id: %d\nlast_option_id: %d\nlast_answer_id: %d\nlast_label_id: %d\n' "$L" "$P" "$O" "$A" "$LB"
```

### 실패 처리
- `.env` 또는 **DATABASE_URL** 누락 → 즉시 중단.
- psql 실패 → stderr와 종료 코드를 그대로 노출. 자체 재시도 없음.
