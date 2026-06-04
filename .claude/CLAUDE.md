## Gravit Learning Contents Generator

Gravit CS 학습 콘텐츠(lesson / problem / option / answer) 자동 생성 파이프라인.
**/generate-learning-content** 스킬 1회 호출로 생성 → 검수 → 피드백 루프 → 스테이징 빌드까지 실행된다.

파이프라인의 **오케스트레이션은 skill이 소유**한다. 이 파일은 항상 필요한 최소 정보만 둔다.

---

### Pipeline State

- **위치:** `pipeline-workspace/pipeline-state-{YYYY-MM-DD}-{seq}.md` (**seq**는 같은 날 첫 실행 = **1**, 두 번째 실행 = **2**, ...)
- **스키마:** `.claude/spec/pipeline/pipeline-state-template.md`

**복구 규칙 (compaction / 세션 재시작 시):** 오늘 날짜의 pipeline-state 파일 중 **status: IN_PROGRESS**인 것이 정확히 1개 있으면 그 파일을 Read하고 Checklist에서 미완료인 가장 이른 phase부터 재개한다. 0개면 skill을 새로 시작한다. 2개 이상이면 비정상 상태이므로 사용자에게 확인을 구한다.

---

### Spec 인덱스

각 스펙은 SoT 문서로 `.claude/spec/` 하위에 있다. skill / agent / hook이 **필요 시점에 Read로 로드**한다.

**generation/** — 콘텐츠 생성 규범
- `.claude/spec/generation/learning-content-rules.md` — 콘텐츠 구성 규칙 (INV·EXP 원칙)
- `.claude/spec/generation/learning-content-writing-style.md` — 한국어 표기·CS 용어·일관성 스타일 규칙
- `.claude/spec/generation/learning-content-sql-schema.md` — DB 테이블 스키마 (prod + **_staging**)
- `.claude/spec/generation/learning-content-sql-template.md` — INSERT 쿼리 템플릿·이스케이프 규칙
- `.claude/spec/generation/problem-good-patterns.md` — 모범 예시 (few-shot)
- `.claude/spec/generation/problem-antipatterns.md` — 피해야 할 안티패턴 (생성 회피 + 검수 탐지)
- `.claude/spec/generation/id-management.md` — ID 발번 규칙

**review/** — 채점 기준
- `.claude/spec/review/review-rubric.md` — R1~R6 검수 루브릭 + 검수 출력 템플릿

**pipeline/** — 파이프라인 인프라
- `.claude/spec/pipeline/pipeline-state-template.md` — pipeline-state 파일 스키마
