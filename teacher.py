import os
from io import BytesIO
import zipfile

import pandas as pd
import streamlit as st

import app_data as data
from ai import evaluate_unit_report
from report_pdf import build_unit_report_pdf

load_data = data.load_data
load_units_raw = data.load_units_raw
save_units_raw = data.save_units_raw
load_lessons_raw = data.load_lessons_raw
save_lessons_raw = data.save_lessons_raw
get_unit_report_data = data.get_unit_report_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UNITS_FILE = os.path.join(BASE_DIR, "units.csv")
LESSONS_FILE = os.path.join(BASE_DIR, "lessons.csv")
STUDENTS_FILE = os.path.join(BASE_DIR, "students.csv")
REFLECTIONS_FILE = os.path.join(BASE_DIR, "reflections.csv")
RUBRIC_FILE = os.path.join(BASE_DIR, "rubric.csv")

REFLECTION_COLUMNS = getattr(data, "REFLECTION_COLUMNS", [
    "日時", "番号", "名前", "分野名", "単元名", "授業名", "振り返り",
    "AI評価", "AI総合点", "AI総合コメント",
    "AI_学んだこと", "AI_学び方", "AI_次",
    "AI_学んだこと点", "AI_学び方点", "AI_次点",
    "AI_学んだことコメント", "AI_学び方コメント", "AI_次コメント",
])


def format_datetime_display(value):
    text = str(value).strip()
    if text == "":
        return ""
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return text
    return dt.strftime("%Y-%m-%d %H:%M")


def ensure_students_file():
    if not os.path.exists(STUDENTS_FILE):
        df = pd.DataFrame(columns=["student_id", "name"])
        df.to_csv(STUDENTS_FILE, index=False, encoding="utf-8-sig")


def load_students_raw():
    ensure_students_file()
    df = pd.read_csv(STUDENTS_FILE, dtype=str, encoding="utf-8-sig").fillna("")

    rename_map = {}
    if "番号" in df.columns and "student_id" not in df.columns:
        rename_map["番号"] = "student_id"
    if "名前" in df.columns and "name" not in df.columns:
        rename_map["名前"] = "name"
    if "氏名" in df.columns and "name" not in df.columns:
        rename_map["氏名"] = "name"

    if rename_map:
        df = df.rename(columns=rename_map)

    for col in ["student_id", "name"]:
        if col not in df.columns:
            df[col] = ""

    return df[["student_id", "name"]].copy()


def save_students_raw(df):
    df = df.copy()
    for col in ["student_id", "name"]:
        if col not in df.columns:
            df[col] = ""
    df = df[["student_id", "name"]].copy()
    df.to_csv(STUDENTS_FILE, index=False, encoding="utf-8-sig")


def student_template_bytes():
    template_df = pd.DataFrame(
        [
            {"student_id": "1001", "name": "山田 太郎"},
            {"student_id": "1002", "name": "鈴木 花子"},
        ]
    )

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        template_df.to_excel(writer, index=False, sheet_name="students")
    bio.seek(0)
    return bio.getvalue()


def normalize_uploaded_students(df):
    df = df.copy().fillna("")

    rename_map = {}
    if "番号" in df.columns and "student_id" not in df.columns:
        rename_map["番号"] = "student_id"
    if "名前" in df.columns and "name" not in df.columns:
        rename_map["名前"] = "name"
    if "氏名" in df.columns and "name" not in df.columns:
        rename_map["氏名"] = "name"

    if rename_map:
        df = df.rename(columns=rename_map)

    if "student_id" not in df.columns or "name" not in df.columns:
        raise ValueError("Excelに student_id 列 と name 列 が必要です。")

    df["student_id"] = df["student_id"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()

    df = df[(df["student_id"] != "") & (df["name"] != "")].copy()
    df = df.drop_duplicates(subset=["student_id"], keep="first").reset_index(drop=True)

    return df[["student_id", "name"]]


def load_reflections_raw():
    df = load_data().copy()
    if "_row_id" not in df.columns:
        df["_row_id"] = [str(i) for i in range(len(df))]
    return df


def save_reflections_raw(df):
    save_df = df.copy()
    for col in REFLECTION_COLUMNS:
        if col not in save_df.columns:
            save_df[col] = ""
    save_df = save_df[REFLECTION_COLUMNS].copy()
    save_df.to_csv(REFLECTIONS_FILE, index=False, encoding="utf-8-sig")


def ensure_rubric_file():
    if not os.path.exists(RUBRIC_FILE):
        df = pd.DataFrame(
            [
                {
                    "観点": "答え",
                    "key": "answer",
                    "2点の基準": "本時の問いに対する答えになっており内容も具体的に書かれている",
                    "1点の基準": "本時の問いに対する答えは書かれているが具体性が弱い",
                    "0点の基準": "本時の問いに対する答えになっていないまたはほとんど書かれていない",
                },
                {
                    "観点": "学び方",
                    "key": "method",
                    "2点の基準": "比較した・資料を読み取った・話し合った・理由を考えたなど自分がどう学んだかが具体的に書かれている",
                    "1点の基準": "学び方への言及はあるが具体性が弱い",
                    "0点の基準": "教科書を使った・授業を受けたなどだけで自分がどう学んだかが書かれていない",
                },
                {
                    "観点": "次にどうするか",
                    "key": "next",
                    "2点の基準": "次に何を調べたいか・考えたいか・挑戦したいかが具体的に書かれている",
                    "1点の基準": "次にすることへの言及はあるが曖昧",
                    "0点の基準": "今後について書かれていない",
                },
            ]
        )
        df.to_csv(RUBRIC_FILE, index=False, encoding="utf-8-sig")


def load_rubric_raw():
    ensure_rubric_file()
    df = pd.read_csv(RUBRIC_FILE, dtype=str, encoding="utf-8-sig").fillna("")

    for col in ["観点", "key", "2点の基準", "1点の基準", "0点の基準"]:
        if col not in df.columns:
            df[col] = ""

    return df[["観点", "key", "2点の基準", "1点の基準", "0点の基準"]].copy()


def save_rubric_raw(df):
    df = df[["観点", "key", "2点の基準", "1点の基準", "0点の基準"]].copy()
    df.to_csv(RUBRIC_FILE, index=False, encoding="utf-8-sig")


def build_backup_zip():
    memory_file = BytesIO()

    with zipfile.ZipFile(memory_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in [STUDENTS_FILE, UNITS_FILE, LESSONS_FILE, REFLECTIONS_FILE, RUBRIC_FILE]:
            if os.path.exists(path):
                zf.write(path, arcname=os.path.basename(path))

    memory_file.seek(0)
    return memory_file.getvalue()


def build_student_options():
    students_df = load_students_raw()
    options = []
    option_map = {}

    if len(students_df) == 0:
        return options, option_map

    students_df = students_df.sort_values(["student_id", "name"]).reset_index(drop=True)

    for _, row in students_df.iterrows():
        sid = str(row.get("student_id", "")).strip()
        name = str(row.get("name", "")).strip()
        label = f"{sid}｜{name}"
        options.append(label)
        option_map[label] = {
            "student_id": sid,
            "name": name,
        }

    return options, option_map


def build_unit_options():
    units_df = load_units_raw()
    options = []
    option_map = {}

    if len(units_df) == 0:
        return options, option_map

    units_df = units_df.sort_values(["field", "unit"]).reset_index(drop=True)

    for _, row in units_df.iterrows():
        field_name = str(row.get("field", "")).strip()
        unit_name = str(row.get("unit", "")).strip()
        label = f"{field_name}｜{unit_name}"
        options.append(label)
        option_map[label] = {
            "field_name": field_name,
            "unit_name": unit_name,
        }

    return options, option_map


def teacher_view():
    st.subheader("先生ページ")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["授業管理", "生徒情報", "提出一覧", "集計", "単元レポート", "バックアップ", "ルーブリック"]
    )

    with tab1:
        st.markdown("## 授業管理")

        with st.expander("大単元を追加", expanded=True):
            with st.form("add_unit_form"):
                field_name = st.selectbox(
                    "分野名",
                    ["地理的分野", "歴史的分野", "公民的分野"],
                )
                unit_name = st.text_input("大単元名")
                unit_question = st.text_area("大単元の問い", height=100)
                is_active = st.checkbox("生徒に表示する", value=True)
                submitted = st.form_submit_button("大単元を追加")

            if submitted:
                field_name = field_name.strip()
                unit_name = unit_name.strip()
                unit_question = unit_question.strip()

                if field_name == "" or unit_name == "" or unit_question == "":
                    st.error("分野名・大単元名・大単元の問いを全部入れてな")
                else:
                    units_df = load_units_raw()

                    duplicate_df = units_df[
                        (units_df["field"].astype(str).str.strip() == field_name)
                        & (units_df["unit"].astype(str).str.strip() == unit_name)
                    ].copy()

                    if len(duplicate_df) > 0:
                        st.warning("同じ大単元はすでに登録されているで")
                    else:
                        new_row = pd.DataFrame(
                            [
                                {
                                    "field": field_name,
                                    "unit": unit_name,
                                    "unit_question": unit_question,
                                    "is_active": "1" if is_active else "0",
                                }
                            ]
                        )
                        units_df = pd.concat([units_df, new_row], ignore_index=True)
                        save_units_raw(units_df)
                        st.success("大単元を追加したで")
                        st.rerun()

        st.markdown("---")

        with st.expander("登録済み大単元", expanded=True):
            units_df = load_units_raw()

            if len(units_df) == 0:
                st.info("まだ大単元は登録されてへんで")
            else:
                edit_df = units_df.copy()
                edit_df["公開"] = edit_df["is_active"].astype(str).str.strip().isin(["1", "True", "true", "TRUE"])
                edit_df["削除"] = False
                edit_df = edit_df.rename(
                    columns={
                        "field": "分野",
                        "unit": "大単元",
                        "unit_question": "大単元の問い",
                    }
                )

                edited_df = st.data_editor(
                    edit_df[["分野", "大単元", "大単元の問い", "公開", "削除"]],
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "分野": st.column_config.TextColumn("分野", disabled=True),
                        "大単元": st.column_config.TextColumn("大単元", disabled=True),
                        "大単元の問い": st.column_config.TextColumn("大単元の問い", disabled=True, width="large"),
                        "公開": st.column_config.CheckboxColumn("公開"),
                        "削除": st.column_config.CheckboxColumn("削除"),
                    },
                    key="unit_editor",
                )

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("大単元の公開設定を保存"):
                        save_df = edited_df.copy().rename(
                            columns={
                                "分野": "field",
                                "大単元": "unit",
                                "大単元の問い": "unit_question",
                            }
                        )
                        save_df["is_active"] = save_df["公開"].apply(lambda x: "1" if bool(x) else "0")
                        save_units_raw(save_df[["field", "unit", "unit_question", "is_active"]])
                        st.success("大単元の公開設定を保存したで")
                        st.rerun()

                with col_b:
                    if st.button("チェックした大単元を削除"):
                        delete_df = edited_df[edited_df["削除"] == True].copy()
                        if len(delete_df) == 0:
                            st.warning("削除する大単元にチェックを入れてな")
                        else:
                            delete_keys = set(
                                zip(
                                    delete_df["分野"].astype(str).str.strip(),
                                    delete_df["大単元"].astype(str).str.strip(),
                                )
                            )

                            remain_units_df = units_df[
                                ~units_df.apply(
                                    lambda row: (
                                        str(row["field"]).strip(),
                                        str(row["unit"]).strip(),
                                    ) in delete_keys,
                                    axis=1,
                                )
                            ].copy()

                            lessons_df = load_lessons_raw()
                            remain_lessons_df = lessons_df[
                                ~lessons_df.apply(
                                    lambda row: (
                                        str(row["field"]).strip(),
                                        str(row["unit"]).strip(),
                                    ) in delete_keys,
                                    axis=1,
                                )
                            ].copy()

                            save_units_raw(remain_units_df)
                            save_lessons_raw(remain_lessons_df)
                            st.success(f"{len(delete_df)}件の大単元を削除したで（ひもづく授業も一緒に削除）")
                            st.rerun()

                if st.checkbox("大単元を一括削除する（確認用）", key="delete_all_units_confirm"):
                    if st.button("大単元をすべて削除"):
                        save_units_raw(pd.DataFrame(columns=["field", "unit", "unit_question", "is_active"]))
                        save_lessons_raw(pd.DataFrame(columns=["field", "unit", "lesson_name", "lesson_question", "is_active"]))
                        st.success("大単元と授業をすべて削除したで")
                        st.rerun()

        st.markdown("---")

        with st.expander("授業を追加", expanded=True):
            units_df = load_units_raw()
            active_unit_options = []

            if len(units_df) > 0:
                for _, row in units_df.iterrows():
                    active_unit_options.append(f"{row['field']}｜{row['unit']}")

            with st.form("add_lesson_form"):
                selected_unit_label = st.selectbox(
                    "ひも付ける大単元",
                    active_unit_options if len(active_unit_options) > 0 else ["大単元を先に登録してな"],
                    disabled=(len(active_unit_options) == 0),
                )
                lesson_name = st.text_input("授業名")
                is_active = st.checkbox("生徒に表示する", value=True)
                submitted = st.form_submit_button("授業を追加")

            if submitted:
                if len(active_unit_options) == 0:
                    st.error("先に大単元を登録してな")
                else:
                    lesson_name = lesson_name.strip()
                    field_name, unit_name = selected_unit_label.split("｜", 1)

                    if lesson_name == "":
                        st.error("授業名を入れてな")
                    else:
                        lessons_df = load_lessons_raw()

                        duplicate_df = lessons_df[
                            (lessons_df["field"].astype(str).str.strip() == field_name)
                            & (lessons_df["unit"].astype(str).str.strip() == unit_name)
                            & (lessons_df["lesson_name"].astype(str).str.strip() == lesson_name)
                        ].copy()

                        if len(duplicate_df) > 0:
                            st.warning("同じ授業はすでに登録されているで")
                        else:
                            new_row = pd.DataFrame(
                                [
                                    {
                                        "field": field_name,
                                        "unit": unit_name,
                                        "lesson_name": lesson_name,
                                        "lesson_question": "",
                                        "is_active": "1" if is_active else "0",
                                    }
                                ]
                            )
                            lessons_df = pd.concat([lessons_df, new_row], ignore_index=True)
                            save_lessons_raw(lessons_df)
                            st.success("授業を追加したで")
                            st.rerun()

        st.markdown("---")

        with st.expander("登録済み授業", expanded=True):
            lessons_df = load_lessons_raw()

            if len(lessons_df) == 0:
                st.info("まだ授業は登録されてへんで")
            else:
                edit_df = lessons_df.copy()
                edit_df["公開"] = edit_df["is_active"].astype(str).str.strip().isin(["1", "True", "true", "TRUE"])
                edit_df["削除"] = False
                edit_df = edit_df.rename(
                    columns={
                        "field": "分野",
                        "unit": "大単元",
                        "lesson_name": "授業名",
                    }
                )

                edited_df = st.data_editor(
                    edit_df[["分野", "大単元", "授業名", "公開", "削除"]],
                    use_container_width=True,
                    num_rows="fixed",
                    column_config={
                        "分野": st.column_config.TextColumn("分野", disabled=True),
                        "大単元": st.column_config.TextColumn("大単元", disabled=True),
                        "授業名": st.column_config.TextColumn("授業名", disabled=True, width="large"),
                        "公開": st.column_config.CheckboxColumn("公開"),
                        "削除": st.column_config.CheckboxColumn("削除"),
                    },
                    key="lesson_editor",
                )

                col_c, col_d = st.columns(2)

                with col_c:
                    if st.button("授業の公開設定を保存"):
                        save_df = edited_df.copy().rename(
                            columns={
                                "分野": "field",
                                "大単元": "unit",
                                "授業名": "lesson_name",
                            }
                        )
                        save_df["lesson_question"] = ""
                        save_df["is_active"] = save_df["公開"].apply(lambda x: "1" if bool(x) else "0")
                        save_lessons_raw(save_df[["field", "unit", "lesson_name", "lesson_question", "is_active"]])
                        st.success("授業の公開設定を保存したで")
                        st.rerun()

                with col_d:
                    if st.button("チェックした授業を削除"):
                        delete_df = edited_df[edited_df["削除"] == True].copy()
                        if len(delete_df) == 0:
                            st.warning("削除する授業にチェックを入れてな")
                        else:
                            delete_keys = set(
                                zip(
                                    delete_df["分野"].astype(str).str.strip(),
                                    delete_df["大単元"].astype(str).str.strip(),
                                    delete_df["授業名"].astype(str).str.strip(),
                                )
                            )

                            remain_lessons_df = lessons_df[
                                ~lessons_df.apply(
                                    lambda row: (
                                        str(row["field"]).strip(),
                                        str(row["unit"]).strip(),
                                        str(row["lesson_name"]).strip(),
                                    ) in delete_keys,
                                    axis=1,
                                )
                            ].copy()

                            save_lessons_raw(remain_lessons_df)
                            st.success(f"{len(delete_df)}件の授業を削除したで")
                            st.rerun()

                if st.checkbox("授業を一括削除する（確認用）", key="delete_all_lessons_confirm"):
                    if st.button("授業をすべて削除"):
                        save_lessons_raw(pd.DataFrame(columns=["field", "unit", "lesson_name", "lesson_question", "is_active"]))
                        st.success("授業をすべて削除したで")
                        st.rerun()

    with tab2:
        st.markdown("### 生徒を一括登録")

        template_data = student_template_bytes()
        st.download_button(
            "生徒登録テンプレートExcelをダウンロード",
            data=template_data,
            file_name="生徒登録テンプレート.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        uploaded_file = st.file_uploader(
            "テンプレートに入力したExcelをアップロード",
            type=["xlsx"],
            key="student_excel_upload",
        )

        if uploaded_file is not None and st.button("生徒を登録"):
            try:
                upload_df = pd.read_excel(uploaded_file, dtype=str).fillna("")
                normalized_df = normalize_uploaded_students(upload_df)

                if len(normalized_df) == 0:
                    st.error("登録できる生徒データが見つからへんかったで")
                else:
                    save_students_raw(normalized_df)
                    st.success(f"{len(normalized_df)}人の生徒を登録したで")
                    st.rerun()
            except Exception as e:
                st.error("Excelの読み込みに失敗したで")
                st.code(str(e))

        st.markdown("---")
        st.markdown("### 登録済み生徒")

        students_df = load_students_raw()
        if len(students_df) == 0:
            st.info("まだ生徒は登録されてへんで")
        else:
            edit_df = students_df.copy()
            edit_df["削除"] = False
            edit_df = edit_df.rename(columns={"student_id": "番号", "name": "名前"})

            edited_df = st.data_editor(
                edit_df[["番号", "名前", "削除"]],
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "番号": st.column_config.TextColumn("番号", disabled=True),
                    "名前": st.column_config.TextColumn("名前", disabled=True),
                    "削除": st.column_config.CheckboxColumn("削除"),
                },
                key="students_editor",
            )

            if st.button("チェックした生徒を削除"):
                delete_df = edited_df[edited_df["削除"] == True].copy()
                if len(delete_df) == 0:
                    st.warning("削除する生徒にチェックを入れてな")
                else:
                    delete_ids = set(delete_df["番号"].astype(str).str.strip())
                    remain_df = students_df[
                        ~students_df["student_id"].astype(str).str.strip().isin(delete_ids)
                    ].copy()
                    save_students_raw(remain_df)
                    st.success(f"{len(delete_df)}人の生徒を削除したで")
                    st.rerun()

            if st.checkbox("生徒を一括削除する（確認用）", key="delete_all_students_confirm"):
                if st.button("生徒をすべて削除"):
                    save_students_raw(pd.DataFrame(columns=["student_id", "name"]))
                    st.success("生徒をすべて削除したで")
                    st.rerun()

    with tab3:
        st.markdown("### 提出された振り返り一覧")

        df = load_reflections_raw()

        if len(df) == 0:
            st.info("まだ提出はないで")
        else:
            filter_df = df.copy()
            filter_df["_row_id"] = filter_df["_row_id"].astype(str)

            field_options = ["すべて"] + sorted(
                [x for x in filter_df["分野名"].dropna().astype(str).unique() if x.strip() != ""]
            )
            selected_field = st.selectbox("分野で絞り込み", field_options, key="teacher_field_filter")

            if selected_field != "すべて":
                filter_df = filter_df[filter_df["分野名"].astype(str) == selected_field].copy()

            unit_options = ["すべて"] + sorted(
                [x for x in filter_df["単元名"].dropna().astype(str).unique() if x.strip() != ""]
            )
            selected_unit = st.selectbox("大単元で絞り込み", unit_options, key="teacher_unit_filter")

            if selected_unit != "すべて":
                filter_df = filter_df[filter_df["単元名"].astype(str) == selected_unit].copy()

            filter_df = filter_df.sort_values("日時", ascending=False).reset_index(drop=True)
            display_df = filter_df.copy()
            display_df["日時"] = display_df["日時"].apply(format_datetime_display)
            display_df["削除"] = False

            display_df = display_df.rename(
                columns={"分野名": "分野", "単元名": "大単元", "授業名": "授業"}
            )

            edited_df = st.data_editor(
                display_df[["日時", "番号", "名前", "分野", "大単元", "授業", "AI評価", "AI総合点", "振り返り", "削除", "_row_id"]],
                use_container_width=True,
                num_rows="fixed",
                hide_index=True,
                column_config={
                    "日時": st.column_config.TextColumn("日時", disabled=True),
                    "番号": st.column_config.TextColumn("番号", disabled=True),
                    "名前": st.column_config.TextColumn("名前", disabled=True),
                    "分野": st.column_config.TextColumn("分野", disabled=True),
                    "大単元": st.column_config.TextColumn("大単元", disabled=True),
                    "授業": st.column_config.TextColumn("授業", disabled=True),
                    "AI評価": st.column_config.TextColumn("AI評価", disabled=True),
                    "AI総合点": st.column_config.TextColumn("AI総合点", disabled=True),
                    "振り返り": st.column_config.TextColumn("振り返り", disabled=True, width="large"),
                    "削除": st.column_config.CheckboxColumn("削除"),
                    "_row_id": None,
                },
                key="reflections_editor",
            )

            if st.button("チェックした振り返りを削除"):
                delete_df = edited_df[edited_df["削除"] == True].copy()
                if len(delete_df) == 0:
                    st.warning("削除する振り返りにチェックを入れてな")
                else:
                    delete_ids = set(delete_df["_row_id"].astype(str).str.strip())
                    remain_df = df[~df["_row_id"].astype(str).str.strip().isin(delete_ids)].copy()
                    if "_row_id" in remain_df.columns:
                        remain_df = remain_df.drop(columns=["_row_id"])
                    save_reflections_raw(remain_df)
                    st.success(f"{len(delete_df)}件の振り返りを削除したで")
                    st.rerun()

            if st.checkbox("振り返りを一括削除する（確認用）", key="delete_all_reflections_confirm"):
                if st.button("振り返りをすべて削除"):
                    save_reflections_raw(pd.DataFrame(columns=REFLECTION_COLUMNS))
                    st.success("振り返りをすべて削除したで")
                    st.rerun()

    with tab4:
        st.markdown("### 集計")

        df = load_data()

        if len(df) == 0:
            st.info("まだ集計できるデータがないで")
        else:
            total_count = len(df)
            st.metric("提出数", total_count)

            unit_count_df = (
                df.groupby(["分野名", "単元名"], dropna=False)
                .size()
                .reset_index(name="提出数")
                .sort_values(["提出数", "分野名", "単元名"], ascending=[False, True, True])
                .reset_index(drop=True)
            ).rename(columns={"分野名": "分野", "単元名": "大単元"})

            st.markdown("#### 大単元ごとの提出数")
            st.dataframe(unit_count_df, use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("### 単元レポート")
        st.caption("個人用PDFに、単元全体のAIまとめを入れる版やで。")

        student_options, student_map = build_student_options()
        unit_options, unit_map = build_unit_options()

        col1, col2 = st.columns(2)

        with col1:
            selected_student_label = st.selectbox(
                "生徒を選んでな",
                student_options if len(student_options) > 0 else ["生徒が登録されていません"],
                disabled=(len(student_options) == 0),
                key="unit_report_student_select",
            )

        with col2:
            selected_unit_label = st.selectbox(
                "大単元を選んでな",
                unit_options if len(unit_options) > 0 else ["大単元が登録されていません"],
                disabled=(len(unit_options) == 0),
                key="unit_report_unit_select",
            )

        if len(student_options) == 0 or len(unit_options) == 0:
            st.info("生徒登録と大単元登録がそろったら、この画面で使えるで。")
        else:
            student_info = student_map[selected_student_label]
            unit_info = unit_map[selected_unit_label]

            report_data = get_unit_report_data(
                student_id=student_info["student_id"],
                field_name=unit_info["field_name"],
                unit_name=unit_info["unit_name"],
            )

            ai_unit = evaluate_unit_report(
                report_data["unit_question"],
                report_data["first_text"],
                report_data["lessons"],
                report_data["last_text"],
            )

            report_data["unit_star"] = ai_unit.get("unit_star", "未評価")
            report_data["unit_comment"] = ai_unit.get("unit_comment", "AI評価を取得できませんでした。")

            st.markdown("---")
            st.markdown("#### 内容プレビュー")

            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.write(f"**名前**：{report_data['student_name']}")
                st.write(f"**番号**：{report_data['student_id']}")
            with info_col2:
                st.write(f"**分野**：{report_data['field_name']}")
                st.write(f"**大単元**：{report_data['unit_name']}")

            st.markdown("**大単元の問い**")
            st.info(report_data.get("unit_question", "") or "未入力")

            st.markdown("**最初の考え**")
            st.write(report_data.get("first_text", "") or "未入力")

            st.markdown("**最後の考え**")
            st.write(report_data.get("last_text", "") or "未入力")

            lessons_df = report_data.get("lessons", pd.DataFrame())
            if len(lessons_df) > 0:
                st.markdown("**各授業の振り返り**")
                for i, (_, row) in enumerate(lessons_df.iterrows(), start=1):
                    st.write(f"{i}. {row.get('授業名', '')}")
                    st.caption(f"本時の問い：{row.get('本時の問い', '')}")
                    st.write(f"答え：{row.get('それに対する答え', '')}")

            st.markdown("**AIからのまとめ**")
            st.write(f"単元全体の評価：{report_data.get('unit_star', '未評価')}")
            st.write(report_data.get("unit_comment", ""))

            pdf_bytes = build_unit_report_pdf(report_data)

            safe_name = str(report_data.get("student_name", "student")).replace(" ", "_")
            safe_unit = str(report_data.get("unit_name", "unit")).replace(" ", "_")
            file_name = f"単元レポート_{safe_name}_{safe_unit}.pdf"

            st.download_button(
                "この生徒の単元レポートPDFをダウンロード",
                data=pdf_bytes,
                file_name=file_name,
                mime="application/pdf",
                key="download_unit_report_pdf",
            )

    with tab6:
        st.markdown("### バックアップ")

        backup_data = build_backup_zip()
        st.download_button(
            "バックアップZIPをダウンロード",
            data=backup_data,
            file_name="reflection_app_backup.zip",
            mime="application/zip",
        )

    with tab7:
        st.markdown("### ルーブリック編集")

        rubric_df = load_rubric_raw()
        edited_df = st.data_editor(
            rubric_df,
            use_container_width=True,
            num_rows="fixed",
            key="rubric_editor",
        )

        if st.button("ルーブリックを保存"):
            save_rubric_raw(edited_df)
            st.success("ルーブリックを保存したで")
            st.rerun()