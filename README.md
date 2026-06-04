## 📌 목적

**Gravit** 서비스의 CS 학습 콘텐츠(**문제**·**정답**·**선지**) 생성을 자동화하는 인프라다. 사람이 반복하던 **문제 생성 → 검수 → DB 적재** 워크플로우를, **Claude Code**의 Subagent·Skill·Hook을 엮어 한 번의 스킬 호출(`/generate-learning-content`)로 끝까지 실행한다.

단발성 LLM 호출이 아니라, 상태 추적·정량 검수 루브릭·피드백 루프·compaction 복구까지 갖춰 **수백 유닛을 일관된 품질로 돌리는 하네스 엔지니어링(Harness engineering)** 아키텍처를 지향한다.

---

## 📌 설계 원칙

"LLM을 한 번 잘 호출한다"가 아니라 "LLM이 포함된 파이프라인이 수백 유닛에 걸쳐 일관된 품질로 돌아가게 만든다"를 목표로 한다. 프롬프트에 기대는 대신, 파이프라인의 뼈대(절차·규범·상태·검증)를 파일과 코드 인프라로 분리한다.

- **절차는 Skill이 소유한다.** 오케스트레이션은 스킬에 두고, 세부 절차는 필요 시점에만 읽어 메인 세션의 컨텍스트를 얇게 유지한다.
- **규범은 SoT 스펙으로 분리한다.** 모든 규칙과 기준을 스펙 문서 한 곳에 두어, 한 곳을 고치면 생성기와 검수기가 같은 기준으로 재동작한다.
- **작업은 서브에이전트로 격리·병렬화한다.** 유닛 간 교차 오염 없이 병렬로 생성하고, 검수는 read-only로 정답을 직접 풀어 본 뒤 독립적으로 채점한다.
- **검수는 정량 기준 + 피드백 루프로 고정한다.** 점수화된 합격/재시도 루프로 품질을 수렴시키고, 한계를 넘는 항목은 사람과 합의해 마무리한다.
- **상태와 산출물은 디스크에 고정한다.** 세션이 끊겨도 미완료 지점부터 재개하고, 에이전트 사이에는 텍스트가 아니라 파일 경로가 오간다.
- **검증을 통과한 뒤 staging에만 적재한다.** 구조와 무결성을 강제로 검증한 다음, 운영과 분리된 staging 영역에만 쓴다.

---

## 📌 파이프라인 구조

```
[/generate-learning-content {unit_ids} 호출]
    │
    ├─ Phase 0. 복구 확인 (메인 세션)
    │   ├─ pipeline-state-{날짜}.md 없음 → Phase 1
    │   └─ 있음 → Checklist에서 미완료 가장 이른 phase를 resume_phase로 결정
    │       └─ resume_phase > 2 → fetch-max-id만 재호출해 ID Baseline 갱신
    │          (concept-note / existing-problems 캐시는 재사용)
    │
    ├─ Phase 1. 계획 수립 (메인 세션)
    │   ├─ 유닛 ID 파싱
    │   └─ pipeline-state-{날짜}.md 생성 (Meta + Checklist 초기화)
    │
    ├─ Phase 2. 데이터 수집 (메인 세션)
    │   ├─ /fetch-cs-note → concept-note.md
    │   ├─ /fetch-existing-learning-contents → existing-problems.sql
    │   ├─ fetch-max-id → ID Baseline 확정
    │   └─ pipeline-state 업데이트
    │
    ├─ Phase 3. 콘텐츠 생성 (서브에이전트 병렬, context: fork)
    │   ├─ [재실행 가드] 기존 lesson.sql 존재 시 [덮어쓰기 / 보존 후 skip] 확인
    │   ├─ [Unit A] learning-content-generator → lesson.sql (1 lesson, 6문제)
    │   ├─ [Unit B] learning-content-generator → lesson.sql
    │   └─ ...
    │
    ├─ Phase 4. 콘텐츠 검수 (서브에이전트 병렬, context: fork, read-only)
    │   ├─ [재실행 가드] 기존 review.md 존재 시 [덮어쓰기 / 보존 후 skip] 확인
    │   ├─ learning-content-reviewer → 각 문제 직접 풀이
    │   ├─ R1~R6 항목별 1~5점 채점 → PASS/REJECT 판정 → review.md
    │   ├─ 모두 PASS → ☞ Phase 7 (5·6 건너뜀)
    │   └─ 하나라도 REJECT → Phase 5
    │
    ├─ Phase 5. 피드백 루프 (문제당 최대 3회)
    │   ├─ REJECT 문제 + 감점항목 + 개선방향 → generator 재호출 → reviewer 재채점
    │   ├─ 3회 초과 시 lesson.sql에 -- manual-review 주석 태깅
    │   │                + pipeline-state의 Manual Review에 요약 기록
    │   ├─ Manual Review 항목 있음 → Phase 6
    │   └─ Manual Review 비어있음 → ☞ Phase 7 (6 건너뜀)
    │
    ├─ Phase 6. manual-review 해소 (사용자 대화)
    │   ├─ 태깅된 항목별 수정안 제시 → OK 응답 시 lesson.sql 반영
    │   └─ 모두 해소되면 Manual Review 비움
    │
    ├─ Phase 7. staging 적재
    │   ├─ .env의 DATABASE_URL 로드
    │   ├─ psql --single-transaction -f lesson.sql → _staging 테이블
    │   └─ pipeline-state 최종 상태: COMPLETED
    │
    └─ [Hook: notify-complete] Webhook 알림
```

---

## 📌 파일 디렉토리 구조

```
프로젝트 루트/
├── .claude/
│   ├── CLAUDE.md                              ← 항상 로드되는 최소 지침 (pipeline-state 경로, spec 인덱스)
│   ├── agents/
│   │   ├── learning-content-generator.md      ← 콘텐츠 생성 서브에이전트 (context: fork)
│   │   └── learning-content-reviewer.md       ← 콘텐츠 검수 서브에이전트 (context: fork, read-only)
│   ├── skills/
│   │   ├── generate-learning-content/
│   │   │   ├── SKILL.md                       ← 진입점 스킬 (Phase 0~7 오케스트레이션)
│   │   │   └── phases/                        ← phase별 절차 runbook
│   │   │       ├── phase-0-recovery.md
│   │   │       ├── phase-1-planning.md
│   │   │       ├── phase-2-fetch.md
│   │   │       ├── phase-3-generate.md
│   │   │       ├── phase-4-review.md
│   │   │       ├── phase-5-feedback-loop.md
│   │   │       ├── phase-6-manual-review.md
│   │   │       └── phase-7-staging-load.md
│   │   ├── fetch-cs-note/
│   │   │   └── SKILL.md                       ← 유닛 개념노트 조회
│   │   ├── fetch-existing-learning-contents/
│   │   │   └── SKILL.md                       ← 유닛의 기존 문제 SQL 수집 (중복 방지용)
│   │   └── fetch-max-id/
│   │       └── SKILL.md                       ← lesson/problem/option/answer MAX ID 조회
│   ├── hooks/
│   │   ├── notify-complete.sh                 ← Stop 이벤트: 완료 Webhook 알림
│   │   └── notify-permission.sh               ← Notification 이벤트: 권한 요청 알림
│   ├── scripts/
│   │   ├── validate-lesson-structure.py       ← 레슨 구조(문제 수·선지 수·정답 수) 검증
│   │   └── validate-lesson-sql.py             ← INSERT 쿼리 무결성·ID 연속성·따옴표 검증
│   ├── spec/                                  ← SoT spec 문서 (skill/agent가 필요 시점에 Read)
│   │   ├── generation/                        ← 콘텐츠 생성에 쓰이는 규범
│   │   │   ├── learning-content-rules.md      ← 콘텐츠 구성 규칙 (INV·EXP 원칙 포함)
│   │   │   ├── learning-content-writing-style.md  ← 한국어 표기·CS 용어·일관성 스타일 규칙
│   │   │   ├── learning-content-sql-schema.md ← DB 테이블 스키마 (prod + _staging)
│   │   │   ├── learning-content-sql-template.md   ← INSERT 쿼리 템플릿·이스케이프 규칙
│   │   │   ├── problem-good-patterns.md       ← 따라 만들 모범 예시 (few-shot)
│   │   │   ├── problem-antipatterns.md        ← 피해야 할 안티패턴 (생성 회피 + 검수 탐지)
│   │   │   └── id-management.md               ← ID 발번 규칙
│   │   ├── review/                            ← 채점에 쓰이는 기준
│   │   │   ├── review-rubric.md               ← 검수 루브릭 (R1~R6 채점 기준)
│   │   │   └── review-template.md             ← 검수 출력 템플릿
│   │   └── pipeline/
│   │       └── pipeline-state-template.md     ← pipeline-state 파일 스키마
│   └── settings.local.json
│
└── pipeline-workspace/
    ├── pipeline-state-{YYYY-MM-DD}.md         ← 파이프라인 상태 추적 파일
    ├── fetch-cache/{YYYY-MM-DD}/{unit_id}/
    │   ├── concept-note.md                    ← Phase 2: fetch-cs-note 산출물
    │   └── existing-problems.sql              ← Phase 2: fetch-existing-learning-contents 산출물
    ├── generation-output/{YYYY-MM-DD}/{unit_id}/
    │   └── lesson.sql                         ← Phase 3/5/6: generator + manual-review 최종 SQL
    ├── review-output/{YYYY-MM-DD}/{unit_id}/
    │   └── review.md                          ← Phase 4/5: reviewer 채점 결과
    └── problem-seed/                          ← 초기 시드 문제 SQL (유닛별 레퍼런스)
```
