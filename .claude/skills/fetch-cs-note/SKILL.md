---
name: fetch-cs-note
description: 지정된 유닛의 개념노트를 Gravit API에서 markdown으로 조회하여 표준 출력으로 반환한다.
allowed-tools: Bash
---

## fetch-cs-note

### 입력
- **unit_id** (int, 필수)

### 출력
- 표준 출력: API가 반환한 markdown 본문.

### 절차

#### Phase 1. API 호출
```
curl -fsS -X GET "${GRAVIT_API_BASE_URL}/cs-notes/{unit_id}" \
  -H 'accept: text/markdown'
```

### 실패 처리
- `.env` 또는 **GRAVIT_API_BASE_URL** 누락 시 즉시 중단.
- curl 실패 시 stderr·종료 코드를 그대로 노출. 자체 재시도 없음.