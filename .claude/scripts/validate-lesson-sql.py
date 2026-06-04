#!/usr/bin/env python3
# 사용법:
#   validate-lesson-sql.py <lesson.sql>
#   validate-lesson-sql.py <lesson.sql> --id-allocation '<JSON 또는 JSON 파일 경로>'
#
# --id-allocation JSON 스키마:
#   {"lesson_start": int, "problem_start": int, "option_start": int, "answer_start": int}
#
# exit: 0 통과 / 1 검증 실패 / 2 인자·파일 오류

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# ------------------------------------------------------------
# SQL 파싱 (validate-lesson-structure.py에 동일 코드. 수정 시 양쪽 동기화 필수.)
# ------------------------------------------------------------

_INSERT_HEAD = re.compile(
    r"INSERT\s+INTO\s+(\w+)\s*\([^)]*\)\s*VALUES\s*",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class _ParsedLesson:
    insert_order: list[str] = field(default_factory=list)
    table_block_counts: dict[str, int] = field(default_factory=dict)
    staging_label_rows: list[list[str]] = field(default_factory=list)
    lesson_rows: list[list[str]] = field(default_factory=list)
    problem_rows: list[list[str]] = field(default_factory=list)
    option_rows: list[list[str]] = field(default_factory=list)
    answer_rows: list[list[str]] = field(default_factory=list)


def _parse_inserts(sql: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(sql):
        m = _INSERT_HEAD.search(sql, pos)
        if not m:
            break
        table = m.group(1).lower()
        i = m.end()
        body_start = i
        in_str = False
        while i < len(sql):
            ch = sql[i]
            if ch == "'":
                if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                    i += 2
                    continue
                in_str = not in_str
            elif ch == ";" and not in_str:
                break
            i += 1
        out.append((table, sql[body_start:i]))
        pos = i + 1
    return out


def _iter_outside_strings(body: str):
    # 문자열 리터럴(이스케이프 '' 포함) 바깥의 (index, char)만 생성.
    i, in_str = 0, False
    while i < len(body):
        ch = body[i]
        if ch == "'":
            if in_str and i + 1 < len(body) and body[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
            i += 1
            continue
        if not in_str:
            yield i, ch
        i += 1


def _split_value_tuples(body: str) -> list[str]:
    tuples, depth, start = [], 0, None
    for i, ch in _iter_outside_strings(body):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                tuples.append(body[start:i])
                start = None
    return tuples


def _split_fields(row: str) -> list[str]:
    if not row:
        return []
    fields_: list[str] = []
    last = 0
    for i, ch in _iter_outside_strings(row):
        if ch == ",":
            fields_.append(row[last:i].strip())
            last = i + 1
    if last < len(row):
        fields_.append(row[last:].strip())
    return fields_


def _unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == "'" and v[-1] == "'":
        return v[1:-1]
    return v


def _to_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


def _parse_lesson_sql(path: str | Path) -> _ParsedLesson:
    sql = Path(path).read_text(encoding="utf-8")
    parsed = _ParsedLesson()
    rows_by_table = {
        "staging_label": parsed.staging_label_rows,
        "lesson_staging": parsed.lesson_rows,
        "problem_staging": parsed.problem_rows,
        "option_staging": parsed.option_rows,
        "answer_staging": parsed.answer_rows,
    }
    for table, body in _parse_inserts(sql):
        parsed.insert_order.append(table)
        parsed.table_block_counts[table] = parsed.table_block_counts.get(table, 0) + 1
        target = rows_by_table.get(table)
        if target is None:
            continue
        for tup in _split_value_tuples(body):
            target.append(_split_fields(tup))
    return parsed


# ------------------------------------------------------------
# SQL 무결성 검증
# ------------------------------------------------------------

EXPECTED_ORDER = ["staging_label", "lesson_staging", "problem_staging", "option_staging", "answer_staging"]
ALLOCATION_KEYS = {"lesson_start", "problem_start", "option_start", "answer_start", "label_start"}
EXPECTED_COUNTS = {"lesson": 1, "problem": 6, "option": 16, "answer": 2, "label": 1}


def load_allocation(spec: str) -> dict:
    p = Path(spec)
    raw = p.read_text(encoding="utf-8") if p.exists() else spec
    data = json.loads(raw)
    missing = ALLOCATION_KEYS - data.keys()
    if missing:
        raise ValueError(f"id-allocation 필수 키 누락: {sorted(missing)}")
    return data


def check_insert_order(parsed: _ParsedLesson, errors: list[str]) -> None:
    seen_first = list(dict.fromkeys(t for t in parsed.insert_order if t in EXPECTED_ORDER))
    expected = [t for t in EXPECTED_ORDER if t in seen_first]
    if seen_first != expected:
        errors.append(f"INSERT 순서 위반: {seen_first} (기대: {' → '.join(EXPECTED_ORDER)})")


def check_option_block_count(parsed: _ParsedLesson, errors: list[str]) -> None:
    n = parsed.table_block_counts.get("option_staging", 0)
    if n > 1:
        errors.append(f"option_staging INSERT 블록이 {n}개. 단일 블록으로 묶어야 함.")


def collect_lesson_id(parsed: _ParsedLesson) -> int | None:
    if not parsed.lesson_rows or not parsed.lesson_rows[0]:
        return None
    return _to_int(parsed.lesson_rows[0][0])


def collect_problems(parsed: _ParsedLesson) -> list[tuple[int | None, int | None, str]]:
    out = []
    for row in parsed.problem_rows:
        if len(row) < 5:
            continue
        out.append((_to_int(row[0]), _to_int(row[1]), _unquote(row[4])))
    return out


def check_problem_fk(
    problems: list[tuple[int | None, int | None, str]],
    lesson_id: int | None,
    errors: list[str],
) -> None:
    if lesson_id is None:
        return
    for pid, plid, _ in problems:
        if plid is not None and plid != lesson_id:
            errors.append(f"problem id={pid} lesson_id={plid} ≠ lesson.id={lesson_id}")


def collect_options_and_check_fk(
    parsed: _ParsedLesson, obj_ids: set[int], errors: list[str]
) -> list[int]:
    ids: list[int] = []
    for row in parsed.option_rows:
        if len(row) < 6:
            continue
        oid = _to_int(row[0])
        pid = _to_int(row[1])
        if oid is not None:
            ids.append(oid)
        if pid is not None and pid not in obj_ids:
            errors.append(f"option id={oid} problem_id={pid} → OBJECTIVE 문제가 아님")
    return ids


def collect_answers_and_check_fk(
    parsed: _ParsedLesson, subj_ids: set[int], errors: list[str]
) -> list[int]:
    ids: list[int] = []
    for row in parsed.answer_rows:
        if len(row) < 5:
            continue
        aid = _to_int(row[0])
        pid = _to_int(row[1])
        if aid is not None:
            ids.append(aid)
        if pid is not None and pid not in subj_ids:
            errors.append(f"answer id={aid} problem_id={pid} → SUBJECTIVE 문제가 아님")
    return ids


def check_label_consistency(parsed: _ParsedLesson, errors: list[str]) -> None:
    if len(parsed.staging_label_rows) != 1:
        errors.append(
            f"staging_label INSERT row 개수: expected 1, got {len(parsed.staging_label_rows)}"
        )
        return
    head = parsed.staging_label_rows[0]
    if len(head) < 4:
        errors.append("staging_label row 필드 부족 (<4)")
        return
    label_value = _unquote(head[1])

    def _label_at(rows: list[list[str]], idx: int) -> list[str]:
        out: list[str] = []
        for r in rows:
            if len(r) > idx:
                out.append(_unquote(r[idx]))
        return out

    mismatches: list[str] = []
    for tbl, rows, idx in (
        ("lesson_staging", parsed.lesson_rows, 3),
        ("problem_staging", parsed.problem_rows, 5),
        ("option_staging", parsed.option_rows, 5),
        ("answer_staging", parsed.answer_rows, 4),
    ):
        for v in _label_at(rows, idx):
            if v != label_value:
                mismatches.append(f"{tbl}.label='{v}' ≠ staging_label.label='{label_value}'")
    for m in mismatches[:5]:
        errors.append(f"label 불일치: {m}")
    if len(mismatches) > 5:
        errors.append(f"label 불일치 추가 {len(mismatches) - 5}건 생략")


def check_continuity(errors: list[str], label: str, actual: list[int], start: int) -> None:
    count = EXPECTED_COUNTS[label]
    expected = set(range(start, start + count))
    actual_set = set(actual)
    if len(actual) != len(actual_set):
        dups = [v for v, c in Counter(actual).items() if c > 1]
        errors.append(f"{label} ID 중복: {sorted(dups)}")
    if actual_set != expected:
        missing = sorted(expected - actual_set)
        extra = sorted(actual_set - expected)
        msg = f"{label} ID 연속성 위반 (기대 {start}~{start + count - 1})"
        if missing:
            msg += f" / 누락 {missing}"
        if extra:
            msg += f" / 범위 밖 {extra}"
        errors.append(msg)


def check_quote_balance(sql: str, errors: list[str]) -> None:
    # 파일 전체에서 작은따옴표 짝이 맞는지 확인 (이스케이프 '' 고려).
    # 짝이 안 맞으면 이스케이프되지 않은 ' 가 있을 가능성 → psql 적재가 통째로 실패.
    i, in_str, n = 0, False, len(sql)
    while i < n:
        if sql[i] == "'":
            if in_str and i + 1 < n and sql[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        i += 1
    if in_str:
        errors.append(
            "작은따옴표 짝이 맞지 않음 — 이스케이프되지 않은 ' 가능성. "
            "본문·해설의 작은따옴표를 '' 로 이스케이프했는지 확인."
        )


def run_checks(parsed: _ParsedLesson, allocation: dict | None) -> list[str]:
    errors: list[str] = []

    check_insert_order(parsed, errors)
    check_option_block_count(parsed, errors)
    check_label_consistency(parsed, errors)

    lesson_id = collect_lesson_id(parsed)
    problems = collect_problems(parsed)
    check_problem_fk(problems, lesson_id, errors)

    obj_ids = {pid for pid, _, t in problems if t == "OBJECTIVE" and pid is not None}
    subj_ids = {pid for pid, _, t in problems if t == "SUBJECTIVE" and pid is not None}
    option_ids = collect_options_and_check_fk(parsed, obj_ids, errors)
    answer_ids = collect_answers_and_check_fk(parsed, subj_ids, errors)

    if allocation is not None:
        label_id = None
        if parsed.staging_label_rows and parsed.staging_label_rows[0]:
            label_id = _to_int(parsed.staging_label_rows[0][0])
        check_continuity(
            errors, "label",
            [label_id] if label_id is not None else [],
            allocation["label_start"],
        )
        check_continuity(
            errors, "lesson",
            [lesson_id] if lesson_id is not None else [],
            allocation["lesson_start"],
        )
        check_continuity(
            errors, "problem",
            [pid for pid, _, _ in problems if pid is not None],
            allocation["problem_start"],
        )
        check_continuity(errors, "option", option_ids, allocation["option_start"])
        check_continuity(errors, "answer", answer_ids, allocation["answer_start"])

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="lesson.sql SQL 무결성 검증")
    parser.add_argument("sql_path")
    parser.add_argument("--id-allocation", help="ID 연속성 검증용 할당. JSON 문자열 또는 JSON 파일 경로.")
    args = parser.parse_args()

    try:
        parsed = _parse_lesson_sql(args.sql_path)
    except OSError as e:
        print(f"cannot read {args.sql_path}: {e}", file=sys.stderr)
        return 2

    allocation = None
    if args.id_allocation:
        try:
            allocation = load_allocation(args.id_allocation)
        except (ValueError, OSError) as e:
            print(f"--id-allocation 파싱 실패: {e}", file=sys.stderr)
            return 2

    errors = run_checks(parsed, allocation)
    try:
        check_quote_balance(Path(args.sql_path).read_text(encoding="utf-8"), errors)
    except OSError:
        pass
    if errors:
        print("[FAIL] validate-lesson-sql", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("[OK] validate-lesson-sql")
    return 0


if __name__ == "__main__":
    sys.exit(main())