---
name: generate-learning-content
description: Gravit CS 학습 콘텐츠 생성 파이프라인 진입점. 유닛 ID를 받아 1 lesson(OBJECTIVE 4 + SUBJECTIVE 2) 생성·검수·staging 적재까지 수행. /generate-learning-content 호출 시 트리거.
allowed-tools: Read, Write, Edit, Glob, Bash, Task, Skill
---

## generate-learning-content

### 진입 지시

1. **항상 Phase 0부터 시작한다.** `phases/phase-0-recovery.md`를 Read하고 그 파일의 절차를 따른다.
2. Phase 0이 결정한 **resume_phase**에 해당하는 phase 파일을 Read한다.
3. Phase 간 이동은 항상 현재 phase 파일의 "다음 phase" 섹션을 따른다.

### Phase 인덱스

| Phase | 파일 | 한 줄 요약 |
|---|---|---|
| 0 | `phases/phase-0-recovery.md` | 오늘 날짜의 **IN_PROGRESS** pipeline-state가 있으면 재개, 없으면 Phase 1. 복구 시 ID Baseline만 재조회 |
| 1 | `phases/phase-1-planning.md` | 유닛 파싱, pipeline-state 초기화 |
| 2 | `phases/phase-2-fetch.md` | 개념노트·기존 문제 수집, ID Baseline 확정 (기존 문제·ID Baseline은 캐시 안 씀, 개념노트만 재사용) |
| 3 | `phases/phase-3-generate.md` | 유닛별 generator 서브에이전트 병렬 호출 → 1 lesson씩 생성 |
| 4 | `phases/phase-4-review.md` | reviewer 서브에이전트로 R1~R6 채점 및 PASS/REJECT 판정 |
| 5 | `phases/phase-5-feedback-loop.md` | REJECT 재생성 루프 (문제당 최대 3회), 초과 시 manual-review |
| 6 | `phases/phase-6-manual-review.md` | manual-review 태깅 항목을 사용자와 대화로 해소 |
| 7 | `phases/phase-7-staging-load.md` | 유닛별 lesson.sql을 **_staging** 테이블에 psql로 적재 |

**분기 요약**
- Phase 4: 전부 PASS → **Phase 7** (5·6 건너뜀) / 하나라도 REJECT → Phase 5
- Phase 5: Manual Review에 항목 있음 → Phase 6 / 비어 있음 → **Phase 7** (6 건너뜀)
- Phase 6: 해소 완료 → Phase 7
