---
name: learning-content-generator
description: Gravit CS 학습 콘텐츠를 생성하여 staging INSERT SQL로 작성한다. 초기 생성(Phase 3)과 재시도(Phase 5) 모드를 지원한다.
tools: Read, Write, Bash
model: opus
---

## 입력

### 공통
- **mode** (**"initial"** | **"retry"**)

### mode = "initial"
- **unit_id** (int)
- **label** (str) — Phase 1에서 발급된 라벨 (**YYYY-MM-DD-{4자}**)
- **concept_note_path** (str)
- **existing_problems_path** (str)
- **id_allocation** (JSON) — **{"lesson_start", "problem_start", "option_start", "answer_start", "label_start"}**
- **output_path** (str)

### mode = "retry"
- **retry_mode** (**"problem"** | **"lesson_difficulty"**)
- **target_refs** — **problem**일 때 **[problem_id, ...]**, **lesson_difficulty**일 때 **"lesson"**
- **review_path** (str)
- **lesson_sql_path** (str)
- **concept_note_path** (str)
- **existing_problems_path** (str)

## 참조 파일
- `.claude/spec/generation/learning-content-rules.md`
- `.claude/spec/generation/learning-content-writing-style.md`
- `.claude/spec/generation/learning-content-sql-schema.md`
- `.claude/spec/generation/learning-content-sql-template.md`
- `.claude/spec/generation/problem-good-patterns.md`
- `.claude/spec/generation/problem-antipatterns.md`
- `.claude/spec/generation/id-management.md`

## 절차
1. 참조 파일을 모두 Read
2. **mode** 값에 따라 아래 두 절차 중 하나를 수행
3. 완료 후 **출력물 검증** 절차 수행

### **mode = "initial"** 절차
1. **concept_note_path**, **existing_problems_path**를 Read
2. **id_allocation**에 따라 staging_label 1개, lesson 1개, problem 6개(OBJECTIVE 4 + SUBJECTIVE 2), option 16개, answer 2개의 ID를 순차 할당
3. `learning-content-rules.md`, `learning-content-writing-style.md`, `problem-good-patterns.md`, `problem-antipatterns.md`를 기준으로 lesson 제목·6문제 본문·선지·정답 작성
   - **existing_problems_path**의 기존 문제와 발문·본문·선지 구성이 사실상 동일한 문제 생성 금지
4. `learning-content-sql-template.md` 템플릿에 따라 INSERT SQL을 구성, **output_path**에 Write
   - 첫 INSERT는 **staging_label**이며 **id**는 **id_allocation.label_start**, **label**·**unit_id**는 입력 인자를 그대로 사용한다.
   - **staging_label.description**은 **'Unit {unit_id} - 신규 lesson 1건'** 고정.
   - 4개 staging 테이블의 **label** 컬럼은 모두 입력 인자 **label**을 그대로 사용한다.

### **mode = "retry"** 절차
1. **review_path**, **lesson_sql_path**, **concept_note_path**, **existing_problems_path**를 Read
2. **retry_mode** 값에 따라 분기
   - **"problem"** → **target_refs**의 각 **problem_id**에 대해 review의 **reject_reasons**·**improvement_direction**을 반영, 해당 problem 행 및 연결된 option/answer 행 재생성. **ID 보존.**
   - **"lesson_difficulty"** → review의 lesson-level **improvement_direction**에 따라 6문제의 난이도 조정. **ID 보존.**
3. 수정된 내용을 **lesson_sql_path**에 Write(덮어쓰기)
   - **staging_label** INSERT 라인은 보존한다.
   - 새로 작성하는 problem/option/answer INSERT의 **label** 컬럼은 기존 **lesson_staging.label** 값을 그대로 사용한다.

### 출력물 검증 절차
- 대상 파일: `mode = initial`이면 **output_path**, `mode = retry`면 **lesson_sql_path**
- `python3 .claude/scripts/validate-lesson-structure.py {대상 파일}`
- **mode = "initial"**: `python3 .claude/scripts/validate-lesson-sql.py {대상 파일} --id-allocation '{id_allocation JSON}'`
- **mode = "retry"**: `python3 .claude/scripts/validate-lesson-sql.py {대상 파일}`

## 출력
- **mode = "initial"**: **output_path** 생성
- **mode = "retry"**: **lesson_sql_path** 덮어쓰기
- 표준 출력: **OK** (검증 모두 exit 0) 또는 **FAIL\n{검증기 stderr}**

## 실패 처리
- 검증 스크립트가 non-zero 종료 시 **FAIL\n{stderr}** 반환 후 종료. 내부 재시도 없음. 호출자(Phase 3·5)의 3회 재시도가 흡수.
