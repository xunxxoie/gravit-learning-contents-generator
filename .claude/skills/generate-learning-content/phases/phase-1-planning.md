## Phase 1. 계획 수립

### 목적
작업할 유닛을 확정하고, **pipeline-state** 파일을 초기화한다.

### 선행 조건
Phase 0에서 당일 **IN_PROGRESS** 상태의 **pipeline-state**가 존재하지 않음을 판정받았으며, 사용자로부터 유닛 아이디를 전달받았다.

### 참조 파일
- `.claude/spec/pipeline/pipeline-state-template.md`

### 절차
1. 스킬 호출 인자를 통해 작업할 유닛의 아이디를 확정한다. 인자가 없는 경우 사용자에게 요청한다.
2. 오늘 실행의 **seq**를 결정한다. `pipeline-workspace/pipeline-state-{오늘 날짜}-*.md` 패턴 파일 개수 + 1 = **seq** (Bash 예: `ls pipeline-workspace/pipeline-state-{오늘 날짜}-*.md 2>/dev/null | wc -l`로 기존 개수 확인).
3. `.claude/spec/pipeline/pipeline-state-template.md` 탬플릿을 복사하여, `pipeline-workspace/pipeline-state-{오늘 날짜}-{seq}.md`를 추가한다.
4. 각 타겟 유닛별로 라벨을 발급한다. 포맷은 **{오늘 날짜}-{4자 16진수 랜덤}** (예: **2026-04-25-a3f9**).
   - 발급: **python3 -c "import secrets; print('\n'.join(secrets.token_hex(2) for _ in range({N})))"** 출력 N줄을 유닛 순서대로 매핑한다.
   - 발급 후 N개 라벨이 모두 distinct한지 확인한다. 중복이 있으면 그 위치만 다시 발급하여 N개가 모두 unique해질 때까지 반복한다.
5. 추가한 **pipeline-state** 파일을 초기화한다.
   - **date** → {오늘 날짜}
   - **status** → IN_PROGRESS
   - **current_phase** → 1
   - **target_units** → Phase 1에서 전달 받은 유닛의 아이디
   - **labels** → 단계 4에서 발급한 **{unit_id}: {label}** 매핑
   - **ID Baseline** → Phase 2에서 확정
   - **Checklist** → 유닛 1개당 1행, 모든 컬럼 ⏳로 초기화
6. **Log** 에 다음과 같이 작성한다.
   - **- {ISO8601} [phase_1] initialized for units {작업할 유닛의 아이디들}, labels {유닛별 라벨 목록}**

### 출력
- `pipeline-workspace/pipeline-state-{오늘 날짜}-{seq}.md` 생성

### 실패 처리
- 작업할 유닛의 아이디를 전달받지 못한 경우, 사용자에게 요청한 후 재개한다.

### 다음 phase
- Phase 2