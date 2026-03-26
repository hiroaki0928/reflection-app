import os
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

STUDENTS_FILE = os.path.join(DATA_DIR, "students.csv")
LESSONS_FILE = os.path.join(DATA_DIR, "lessons.csv")
REFLECTIONS_FILE = os.path.join(DATA_DIR, "reflections.csv")
UNIT_REFLECTION_FILE = os.path.join(DATA_DIR, "unit_reflections.csv")
RUBRIC_FILE = os.path.join(DATA_DIR, "rubric.csv")
UNITS_FILE = os.path.join(DATA_DIR, "units.csv")

REFLECTION_COLUMNS = [
    "日時",
    "番号",
    "名前",
    "分野名",
    "単元名",
    "授業名",
    "振り返り",
    "AI評価",
    "AI総合点",
    "AI総合コメント",
    "AI_学んだこと",
    "AI_学び方",
    "AI_次",
    "AI_学んだこと点",
    "AI_学び方点",
    "AI_次点",
    "AI_学んだことコメント",
    "AI_学び方コメント",
    "AI_次コメント",
]

UNIT_COLUMNS = [
    "field",
    "unit",
    "unit_question",
    "is_active",
]

LESSON_COLUMNS = [
    "field",
    "unit",
    "lesson_name",
    "lesson_question",
    "is_active",
]

UNIT_REFLECTION_COLUMNS = [
    "日時",
    "番号",
    "名前",
    "分野名",
    "単元名",
    "最初の考え",
    "最後の考え",
]


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _ensure_csv(path: str, columns: list) -> None:
    _ensure_data_dir()
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")


def _safe_read_csv(path: str, columns: list) -> pd.DataFrame:
    if (not os.path.exists(path)) or os.path.getsize(path) == 0:
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        df = pd.DataFrame(columns=columns)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df[columns].copy()


# -------------------------
# reflections.csv
# -------------------------
def _ensure_reflections_file() -> None:
    _ensure_csv(REFLECTIONS_FILE, REFLECTION_COLUMNS)

    df = _safe_read_csv(REFLECTIONS_FILE, REFLECTION_COLUMNS)
    changed = False

    for col in REFLECTION_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            changed = True

    if changed:
        df = df[REFLECTION_COLUMNS]
        df.to_csv(REFLECTIONS_FILE, index=False, encoding="utf-8-sig")


def load_data() -> pd.DataFrame:
    _ensure_reflections_file()
    df = _safe_read_csv(REFLECTIONS_FILE, REFLECTION_COLUMNS)

    for col in REFLECTION_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[REFLECTION_COLUMNS].copy()


def _ai_value(ai_result: Optional[Dict], key: str, default=""):
    if not ai_result:
        return default
    return ai_result.get(key, default)


def save_reflection(
    student_id: str,
    student_name: str,
    field_name: str,
    unit_name: str,
    lesson_name: str,
    reflection: str,
    ai_result: Optional[Dict] = None,
) -> None:
    _ensure_reflections_file()
    df = load_data()

    row = {
        "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "番号": str(student_id).strip(),
        "名前": str(student_name).strip(),
        "分野名": str(field_name).strip(),
        "単元名": str(unit_name).strip(),
        "授業名": str(lesson_name).strip(),
        "振り返り": str(reflection).strip(),
        "AI評価": _ai_value(ai_result, "overall_star", "未評価"),
        "AI総合点": str(_ai_value(ai_result, "overall_score", "")),
        "AI総合コメント": _ai_value(ai_result, "overall_comment", ""),
        "AI_学んだこと": _ai_value(ai_result, "answer_star", "☆☆"),
        "AI_学び方": _ai_value(ai_result, "method_star", "☆☆"),
        "AI_次": _ai_value(ai_result, "next_star", "☆☆"),
        "AI_学んだこと点": str(_ai_value(ai_result, "answer_score", "")),
        "AI_学び方点": str(_ai_value(ai_result, "method_score", "")),
        "AI_次点": str(_ai_value(ai_result, "next_score", "")),
        "AI_学んだことコメント": _ai_value(ai_result, "answer_comment", ""),
        "AI_学び方コメント": _ai_value(ai_result, "method_comment", ""),
        "AI_次コメント": _ai_value(ai_result, "next_comment", ""),
    }

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(REFLECTIONS_FILE, index=False, encoding="utf-8-sig")


# -------------------------
# units.csv
# -------------------------
def ensure_units_file() -> None:
    _ensure_csv(UNITS_FILE, UNIT_COLUMNS)

    df = _safe_read_csv(UNITS_FILE, UNIT_COLUMNS)
    changed = False

    for col in UNIT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            changed = True

    if changed:
        df = df[UNIT_COLUMNS]
        df.to_csv(UNITS_FILE, index=False, encoding="utf-8-sig")


def load_units_raw() -> pd.DataFrame:
    ensure_units_file()
    df = _safe_read_csv(UNITS_FILE, UNIT_COLUMNS)

    for col in UNIT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[UNIT_COLUMNS].copy()


def save_units_raw(df: pd.DataFrame) -> None:
    save_df = df.copy()

    for col in UNIT_COLUMNS:
        if col not in save_df.columns:
            save_df[col] = ""

    save_df = save_df[UNIT_COLUMNS].copy()
    save_df.to_csv(UNITS_FILE, index=False, encoding="utf-8-sig")


def get_active_units() -> pd.DataFrame:
    df = load_units_raw()

    if "is_active" in df.columns:
        active_mask = df["is_active"].astype(str).str.strip().isin(["1", "True", "true", "TRUE"])
        df = df[active_mask].copy()

    return df[["field", "unit", "unit_question"]].drop_duplicates().reset_index(drop=True)


def get_unit_question(field_name: str, unit_name: str) -> str:
    df = load_units_raw()

    matched = df[
        (df["field"].astype(str).str.strip() == str(field_name).strip())
        & (df["unit"].astype(str).str.strip() == str(unit_name).strip())
    ].copy()

    if len(matched) == 0:
        return ""

    return str(matched.iloc[0]["unit_question"]).strip()


# -------------------------
# lessons.csv
# -------------------------
def _normalize_lessons_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().fillna("")

    rename_map = {
        "分野名": "field",
        "単元名": "unit",
        "授業名": "lesson_name",
        "本時の問い": "lesson_question",
    }
    df = df.rename(columns=rename_map)

    for col in LESSON_COLUMNS:
        if col not in df.columns:
            if col == "is_active":
                df[col] = "1"
            else:
                df[col] = ""

    return df[LESSON_COLUMNS].copy()


def ensure_lessons_file() -> None:
    _ensure_csv(LESSONS_FILE, LESSON_COLUMNS)

    df = _safe_read_csv(LESSONS_FILE, LESSON_COLUMNS)
    df = _normalize_lessons_df(df)
    df.to_csv(LESSONS_FILE, index=False, encoding="utf-8-sig")


def load_lessons_raw() -> pd.DataFrame:
    ensure_lessons_file()
    df = _safe_read_csv(LESSONS_FILE, LESSON_COLUMNS)
    return _normalize_lessons_df(df)


def save_lessons_raw(df: pd.DataFrame) -> None:
    save_df = _normalize_lessons_df(df)
    save_df.to_csv(LESSONS_FILE, index=False, encoding="utf-8-sig")


def get_active_lessons() -> pd.DataFrame:
    df = load_lessons_raw()

    if "is_active" in df.columns:
        active_mask = df["is_active"].astype(str).str.strip().isin(["1", "True", "true", "TRUE"])
        df = df[active_mask].copy()

    return df[["field", "unit", "lesson_name"]].drop_duplicates().reset_index(drop=True)


def get_active_lessons_by_unit(field_name: str, unit_name: str) -> pd.DataFrame:
    df = get_active_lessons()

    df = df[
        (df["field"].astype(str).str.strip() == str(field_name).strip())
        & (df["unit"].astype(str).str.strip() == str(unit_name).strip())
    ].copy()

    return df.reset_index(drop=True)


# -------------------------
# students.csv
# -------------------------
def authenticate_student(student_id: str, student_name: str) -> Tuple[bool, str, Optional[Dict]]:
    if not os.path.exists(STUDENTS_FILE):
        return False, "students.csv が見つかりません。", None

    df = pd.read_csv(STUDENTS_FILE, dtype=str, encoding="utf-8-sig").fillna("")

    id_col = None
    name_col = None

    for candidate in ["student_id", "番号", "id", "出席番号"]:
        if candidate in df.columns:
            id_col = candidate
            break

    for candidate in ["name", "名前", "氏名"]:
        if candidate in df.columns:
            name_col = candidate
            break

    if id_col is None or name_col is None:
        return False, "students.csv の列名が合っていません。", None

    sid = str(student_id).strip()
    sname = str(student_name).strip()

    matched = df[
        (df[id_col].astype(str).str.strip() == sid)
        & (df[name_col].astype(str).str.strip() == sname)
    ].copy()

    if len(matched) == 0:
        return False, "番号または名前が違います。", None

    return True, "ログイン成功", {"student_id": sid, "name": sname}


# -------------------------
# unit_reflections.csv
# -------------------------
def ensure_unit_reflection_file() -> None:
    if (not os.path.exists(UNIT_REFLECTION_FILE)) or os.path.getsize(UNIT_REFLECTION_FILE) == 0:
        _ensure_data_dir()
        df = pd.DataFrame(columns=UNIT_REFLECTION_COLUMNS)
        df.to_csv(UNIT_REFLECTION_FILE, index=False, encoding="utf-8-sig")
        return

    df = _safe_read_csv(UNIT_REFLECTION_FILE, UNIT_REFLECTION_COLUMNS)
    changed = False

    for col in UNIT_REFLECTION_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            changed = True

    if changed:
        df = df[UNIT_REFLECTION_COLUMNS]
        df.to_csv(UNIT_REFLECTION_FILE, index=False, encoding="utf-8-sig")


def load_unit_reflections() -> pd.DataFrame:
    ensure_unit_reflection_file()
    df = _safe_read_csv(UNIT_REFLECTION_FILE, UNIT_REFLECTION_COLUMNS)

    for col in UNIT_REFLECTION_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[UNIT_REFLECTION_COLUMNS].copy()


def save_unit_reflection(
    student_id: str,
    student_name: str,
    field_name: str,
    unit_name: str,
    first_text: str,
    last_text: str,
) -> None:
    ensure_unit_reflection_file()
    df = load_unit_reflections()

    row = {
        "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "番号": str(student_id).strip(),
        "名前": str(student_name).strip(),
        "分野名": str(field_name).strip(),
        "単元名": str(unit_name).strip(),
        "最初の考え": str(first_text).strip(),
        "最後の考え": str(last_text).strip(),
    }

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(UNIT_REFLECTION_FILE, index=False, encoding="utf-8-sig")


# -------------------------
# 単元レポート用
# -------------------------
SECTION_LABELS = {
    "question": "本時にたてた問い",
    "answer": "それに対する答え",
    "method": "自分の学び方について",
    "next": "次にどうするか",
}


def parse_reflection_text(reflection_text: str) -> Dict[str, str]:
    text = str(reflection_text).replace("\r\n", "\n").strip()

    result = {
        "question": "",
        "answer": "",
        "method": "",
        "next": "",
    }

    if text == "":
        return result

    pattern = re.compile(
        r"【(本時にたてた問い|それに対する答え|自分の学び方について|次にどうするか)】\n?",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))

    if len(matches) == 0:
        result["answer"] = text.strip()
        return result

    label_to_key = {
        "本時にたてた問い": "question",
        "それに対する答え": "answer",
        "自分の学び方について": "method",
        "次にどうするか": "next",
    }

    for i, match in enumerate(matches):
        label = match.group(1)
        key = label_to_key.get(label, "")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[start:end].strip()

        if key:
            result[key] = value

    return result


def get_latest_unit_reflection(student_id: str, field_name: str, unit_name: str) -> Dict[str, str]:
    df = load_unit_reflections()

    matched = df[
        (df["番号"].astype(str).str.strip() == str(student_id).strip())
        & (df["分野名"].astype(str).str.strip() == str(field_name).strip())
        & (df["単元名"].astype(str).str.strip() == str(unit_name).strip())
    ].copy()

    if len(matched) == 0:
        return {
            "日時": "",
            "最初の考え": "",
            "最後の考え": "",
        }

    matched["__dt"] = pd.to_datetime(matched["日時"], errors="coerce")
    matched = matched.sort_values(["__dt", "日時"], ascending=[False, False]).reset_index(drop=True)
    row = matched.iloc[0]

    return {
        "日時": str(row.get("日時", "")).strip(),
        "最初の考え": str(row.get("最初の考え", "")).strip(),
        "最後の考え": str(row.get("最後の考え", "")).strip(),
    }


def get_unit_reflection_records(student_id: str, field_name: str, unit_name: str) -> pd.DataFrame:
    df = load_data()

    matched = df[
        (df["番号"].astype(str).str.strip() == str(student_id).strip())
        & (df["分野名"].astype(str).str.strip() == str(field_name).strip())
        & (df["単元名"].astype(str).str.strip() == str(unit_name).strip())
    ].copy()

    if len(matched) == 0:
        return pd.DataFrame(
            columns=[
                "日時",
                "授業名",
                "本時の問い",
                "それに対する答え",
                "自分の学び方について",
                "次にどうするか",
            ]
        )

    matched["__dt"] = pd.to_datetime(matched["日時"], errors="coerce")
    matched = matched.sort_values(["__dt", "日時"], ascending=[True, True]).reset_index(drop=True)

    rows: List[Dict[str, str]] = []
    for _, row in matched.iterrows():
        parsed = parse_reflection_text(row.get("振り返り", ""))

        rows.append(
            {
                "日時": str(row.get("日時", "")).strip(),
                "授業名": str(row.get("授業名", "")).strip(),
                "本時の問い": parsed.get("question", "").strip(),
                "それに対する答え": parsed.get("answer", "").strip(),
                "自分の学び方について": parsed.get("method", "").strip(),
                "次にどうするか": parsed.get("next", "").strip(),
            }
        )

    return pd.DataFrame(rows)


def get_unit_report_data(student_id: str, field_name: str, unit_name: str) -> Dict:
    student_id = str(student_id).strip()
    field_name = str(field_name).strip()
    unit_name = str(unit_name).strip()

    all_data = load_data()
    matched_student = all_data[all_data["番号"].astype(str).str.strip() == student_id].copy()

    student_name = ""
    if len(matched_student) > 0:
        student_name = str(matched_student.iloc[0].get("名前", "")).strip()

    unit_question = get_unit_question(field_name, unit_name)
    unit_thoughts = get_latest_unit_reflection(student_id, field_name, unit_name)
    lesson_records = get_unit_reflection_records(student_id, field_name, unit_name)

    return {
        "student_id": student_id,
        "student_name": student_name,
        "field_name": field_name,
        "unit_name": unit_name,
        "unit_question": unit_question,
        "first_text": unit_thoughts.get("最初の考え", ""),
        "last_text": unit_thoughts.get("最後の考え", ""),
        "unit_reflection_saved_at": unit_thoughts.get("日時", ""),
        "lessons": lesson_records,
    }