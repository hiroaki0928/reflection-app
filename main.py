import streamlit as st
import pandas as pd

import app_data as data
import ai
import teacher

save_unit_reflection = data.save_unit_reflection
load_unit_reflections = data.load_unit_reflections
save_reflection = data.save_reflection
load_data = data.load_data
authenticate_student = data.authenticate_student
get_active_units = data.get_active_units
get_unit_question = data.get_unit_question
get_active_lessons_by_unit = data.get_active_lessons_by_unit

evaluate_reflection = ai.evaluate_reflection
teacher_view = teacher.teacher_view

st.set_page_config(page_title="社会科 振り返りアプリ", layout="wide")
st.title("社会科 振り返りアプリ")

TEACHER_PASSWORD = "1234"

mode = st.radio("モードを選択", ["生徒用", "先生用"])

if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False

if "logged_in_student_id" not in st.session_state:
    st.session_state.logged_in_student_id = ""

if "logged_in_student_name" not in st.session_state:
    st.session_state.logged_in_student_name = ""

if "teacher_authenticated" not in st.session_state:
    st.session_state.teacher_authenticated = False


def lesson_label_from_row(row):
    return f"{row['分野名']}｜{row['単元名']}｜{row['授業名']}"


def format_datetime_display(value):
    text = str(value).strip()
    if text == "":
        return ""
    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return text
    return dt.strftime("%Y-%m-%d %H:%M")


def safe_int(value, default=0):
    try:
        return int(str(value).strip())
    except Exception:
        return default


def row_ai_view(row):
    overall_star = str(row.get("AI評価", "")).strip() or "未評価"
    overall_score = safe_int(row.get("AI総合点", ""), 0)

    answer_star = str(row.get("AI_学んだこと", "")).strip() or "☆☆"
    method_star = str(row.get("AI_学び方", "")).strip() or "☆☆"
    next_star = str(row.get("AI_次", "")).strip() or "☆☆"

    answer_comment = str(row.get("AI_学んだことコメント", "")).strip()
    method_comment = str(row.get("AI_学び方コメント", "")).strip()
    next_comment = str(row.get("AI_次コメント", "")).strip()
    overall_comment = str(row.get("AI総合コメント", "")).strip()

    parts = []
    if answer_comment:
        parts.append(f"答え：{answer_comment}")
    if method_comment:
        parts.append(f"学び方：{method_comment}")
    if next_comment:
        parts.append(f"次：{next_comment}")

    good_point = " / ".join(parts)
    advice = overall_comment if overall_comment else "アドバイスはありません。"

    return {
        "overall_star": overall_star,
        "overall_score": overall_score,
        "answer_star": answer_star,
        "method_star": method_star,
        "next_star": next_star,
        "good_point": good_point,
        "advice": advice,
    }


def build_reflection_text(question_text, answer_text, method_text, next_text):
    return (
        f"【本時にたてた問い】\n{question_text.strip()}\n\n"
        f"【それに対する答え】\n{answer_text.strip()}\n\n"
        f"【自分の学び方について】\n{method_text.strip()}\n\n"
        f"【次にどうするか】\n{next_text.strip()}"
    )


if mode == "生徒用":
    st.subheader("生徒ページ")

    if not st.session_state.student_logged_in:
        st.markdown("### ログイン")

        with st.form("student_login_form"):
            login_student_id = st.text_input("4桁番号").strip()
            login_student_name = st.text_input("名前").strip()
            login_submitted = st.form_submit_button("ログイン")

        if login_submitted:
            success, message, student_info = authenticate_student(
                login_student_id,
                login_student_name
            )

            if success:
                st.session_state.student_logged_in = True
                st.session_state.logged_in_student_id = student_info["student_id"]
                st.session_state.logged_in_student_name = student_info["name"]
                st.rerun()
            else:
                st.error(message)

        st.info("自分の4桁番号と名前でログインしてな")

    else:
        student_id = st.session_state.logged_in_student_id
        student_name = st.session_state.logged_in_student_name

        col1, col2 = st.columns([4, 1])

        with col1:
            st.success(f"ログイン中：{student_name}（{student_id}）")

        with col2:
            if st.button("ログアウト"):
                st.session_state.student_logged_in = False
                st.session_state.logged_in_student_id = ""
                st.session_state.logged_in_student_name = ""
                st.rerun()

        with st.expander("💡 振り返りの書き方のポイント"):
            st.markdown(
                """
- 大単元の問いを意識しながら学ぼう
- 本時にたてた問いを書く
- それに対する自分の答えを書く
- どう学んだかを具体的に書く
- 次にどうするかまで書く
                """
            )

        st.markdown("---")
        st.subheader("振り返り入力")

        active_units_df = get_active_units()

        unit_options = []
        unit_map = {}

        if len(active_units_df) > 0:
            for _, row in active_units_df.iterrows():
                label = f"{row['field']}｜{row['unit']}"
                unit_options.append(label)
                unit_map[label] = {
                    "field": row["field"],
                    "unit": row["unit"],
                    "unit_question": row.get("unit_question", ""),
                }

        st.text_input("4桁番号", value=student_id, disabled=True)
        st.text_input("名前", value=student_name, disabled=True)

        if len(unit_options) == 0:
            st.warning("今は選べる大単元がまだないで。先生に大単元を作ってもらってな")
            selected_unit_label = ""
            lesson_options = []
            lesson_map = {}
            selected_lesson_label = ""
            selected_unit_info = None
        else:
            selected_unit_label = st.selectbox("大単元を選んでな", unit_options)
            selected_unit_info = unit_map[selected_unit_label]

            st.markdown("### 大単元の問い")
            unit_question = get_unit_question(
                selected_unit_info["field"],
                selected_unit_info["unit"]
            )
            if unit_question.strip():
                st.info(unit_question)
            else:
                st.info("この大単元には、まだ問いが設定されていません。")

            show_unit_reflection = st.checkbox(
                "大単元の最初と最後の考えを表示する",
                value=False,
                key=f"show_unit_reflection_{selected_unit_info['field']}_{selected_unit_info['unit']}"
            )

            if show_unit_reflection:
                st.markdown("### 大単元の最初と最後の考え")

                unit_reflections_df = load_unit_reflections()
                my_unit_reflections = unit_reflections_df[
                    (unit_reflections_df["番号"].astype(str) == str(student_id))
                    & (unit_reflections_df["分野名"].astype(str) == str(selected_unit_info["field"]))
                    & (unit_reflections_df["単元名"].astype(str) == str(selected_unit_info["unit"]))
                ].copy()

                if len(my_unit_reflections) > 0:
                    latest_unit_reflection = my_unit_reflections.sort_values("日時", ascending=False).iloc[0]
                    default_first_text = str(latest_unit_reflection.get("最初の考え", ""))
                    default_last_text = str(latest_unit_reflection.get("最後の考え", ""))
                    saved_at_text = format_datetime_display(latest_unit_reflection.get("日時", ""))
                    if saved_at_text:
                        st.caption(f"前回保存：{saved_at_text}")
                else:
                    default_first_text = ""
                    default_last_text = ""

                first_unit_text = st.text_area(
                    "この大単元を学ぶ前の考え",
                    value=default_first_text,
                    height=100,
                    key=f"first_unit_{selected_unit_info['field']}_{selected_unit_info['unit']}"
                )

                last_unit_text = st.text_area(
                    "この大単元を学んだ後の考え",
                    value=default_last_text,
                    height=100,
                    key=f"last_unit_{selected_unit_info['field']}_{selected_unit_info['unit']}"
                )

                if st.button("大単元の考えを保存"):
                    save_unit_reflection(
                        student_id=student_id,
                        student_name=student_name,
                        field_name=selected_unit_info["field"],
                        unit_name=selected_unit_info["unit"],
                        first_text=first_unit_text,
                        last_text=last_unit_text,
                    )
                    st.success("大単元の考えを保存したで")
                    st.rerun()

            lessons_df = get_active_lessons_by_unit(
                selected_unit_info["field"],
                selected_unit_info["unit"]
            )

            lesson_options = []
            lesson_map = {}

            if len(lessons_df) > 0:
                for _, row in lessons_df.iterrows():
                    label = f"{row['lesson_name']}"
                    lesson_options.append(label)
                    lesson_map[label] = {
                        "field": row["field"],
                        "unit": row["unit"],
                        "lesson_name": row["lesson_name"],
                    }

            if len(lesson_options) == 0:
                st.warning("この大単元には、まだ選べる授業がないで。先生に授業を作ってもらってな")
                selected_lesson_label = ""
            else:
                selected_lesson_label = st.selectbox("授業を選んでな", lesson_options)

        question_text = st.text_area("本時にたてた問い", height=90)
        answer_text = st.text_area("それに対する答え", height=120)
        method_text = st.text_area("自分の学び方について", height=100)
        next_text = st.text_area("次にどうするか", height=100)

        if st.button("送信"):
            if len(unit_options) == 0 or selected_unit_label == "":
                st.error("選べる大単元がまだないで。先生に確認してな")
            elif len(lesson_options) == 0 or selected_lesson_label == "":
                st.error("選べる授業がまだないで。先生に確認してな")
            elif answer_text.strip() == "":
                st.error("少なくとも『それに対する答え』は書いてな")
            else:
                lesson_info = lesson_map[selected_lesson_label]

                result = evaluate_reflection(
                    question_text=question_text,
                    answer_text=answer_text,
                    method_text=method_text,
                    next_text=next_text,
                )

                reflection_text = build_reflection_text(
                    question_text, answer_text, method_text, next_text
                )

                save_reflection(
                    student_id,
                    student_name,
                    lesson_info["field"],
                    lesson_info["unit"],
                    lesson_info["lesson_name"],
                    reflection_text,
                    ai_result=result,
                )

                st.success("送信できた！")
                st.write(f"分野：{lesson_info['field']}")
                st.write(f"大単元：{lesson_info['unit']}")
                st.write(f"授業：{lesson_info['lesson_name']}")

                st.subheader("AI評価")
                st.write(
                    f"総合評価：{result.get('overall_star', '未評価')}（{result.get('overall_score', 0)}/6）"
                )

                st.subheader("評価の内訳")
                st.caption("※ 各項目は最大★★です")
                st.write(f"答え：{result.get('answer_star', '☆☆')}")
                st.write(f"自分の学び方：{result.get('method_star', '☆☆')}")
                st.write(f"次にどうするか：{result.get('next_star', '☆☆')}")

                st.markdown("**コメント**")
                st.write(result.get("overall_comment", "コメントはありません。"))

                if result.get("answer_comment", ""):
                    st.write(f"・答え：{result.get('answer_comment')}")
                if result.get("method_comment", ""):
                    st.write(f"・学び方：{result.get('method_comment')}")
                if result.get("next_comment", ""):
                    st.write(f"・次：{result.get('next_comment')}")

                if not result.get("ok", False):
                    st.warning(result.get("error", "AI評価でエラーが起きました。"))

        all_data = load_data()
        my_data = all_data[all_data["番号"].astype(str) == str(student_id)].copy()

        st.markdown("---")
        st.subheader("参考になる振り返り")

        if len(my_data) == 0:
            st.info("まずは自分の振り返りを送ってみてな")
        else:
            my_lessons = my_data[["分野名", "単元名", "授業名"]].drop_duplicates().reset_index(drop=True)

            submitted_lesson_options = []
            submitted_lesson_map = {}

            for _, row in my_lessons.iterrows():
                label = lesson_label_from_row(row)
                submitted_lesson_options.append(label)
                submitted_lesson_map[label] = {
                    "分野名": row["分野名"],
                    "単元名": row["単元名"],
                    "授業名": row["授業名"],
                }

            selected_submitted_lesson = st.selectbox(
                "自分が提出した授業から選んでな",
                submitted_lesson_options,
                key="submitted_lesson_select"
            )

            selected_info = submitted_lesson_map[selected_submitted_lesson]

            same_lesson_df = all_data[
                (all_data["分野名"].astype(str) == str(selected_info["分野名"]))
                & (all_data["単元名"].astype(str) == str(selected_info["単元名"]))
                & (all_data["授業名"].astype(str) == str(selected_info["授業名"]))
            ].copy()

            same_lesson_df["AI総合点_num"] = pd.to_numeric(
                same_lesson_df["AI総合点"], errors="coerce"
            ).fillna(0)

            same_lesson_df = same_lesson_df.sort_values(
                ["AI総合点_num", "日時"],
                ascending=[False, False]
            ).reset_index(drop=True)

            same_lesson_df = same_lesson_df[
                same_lesson_df["番号"].astype(str) != str(student_id)
            ].copy()

            if len(same_lesson_df) == 0:
                st.info("まだ参考にできる他の人の振り返りはないで")
            else:
                top_df = same_lesson_df.head(5).copy()

                for i, (_, row) in enumerate(top_df.iterrows(), start=1):
                    ai_view = row_ai_view(row)

                    with st.container():
                        st.markdown(f"#### {i}件目")
                        st.write(f"評価：{ai_view['overall_star']}（{ai_view['overall_score']}/6）")
                        st.write(f"答え：{ai_view['answer_star']}")
                        st.write(f"学び方：{ai_view['method_star']}")
                        st.write(f"次：{ai_view['next_star']}")
                        st.write("振り返り内容")
                        st.info(str(row.get("振り返り", "")).strip())

                        if ai_view["good_point"]:
                            st.write(f"良いところ：{ai_view['good_point']}")
                        if ai_view["advice"]:
                            st.write(f"コメント：{ai_view['advice']}")

                        st.markdown("---")

        st.subheader("自分の記録")

        if len(my_data) == 0:
            st.info("まだ提出した振り返りはないで")
        else:
            my_data = my_data.sort_values("日時", ascending=False).reset_index(drop=True)
            my_data["日時表示"] = my_data["日時"].apply(format_datetime_display)

            display_records = []
            for _, row in my_data.iterrows():
                ai_view = row_ai_view(row)
                display_records.append(
                    {
                        "日時": row["日時表示"],
                        "分野": row["分野名"],
                        "大単元": row["単元名"],
                        "授業": row["授業名"],
                        "総合": f"{ai_view['overall_star']}（{ai_view['overall_score']}/6）",
                        "答え": ai_view["answer_star"],
                        "学び方": ai_view["method_star"],
                        "次": ai_view["next_star"],
                        "振り返り": row["振り返り"],
                        "コメント": ai_view["advice"],
                    }
                )

            display_df = pd.DataFrame(display_records)

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

else:
    st.subheader("先生ページ")

    if not st.session_state.teacher_authenticated:
        with st.form("teacher_login_form"):
            password = st.text_input("先生用パスワード", type="password")
            submitted = st.form_submit_button("ログイン")

        if submitted:
            if password == TEACHER_PASSWORD:
                st.session_state.teacher_authenticated = True
                st.rerun()
            else:
                st.error("パスワードが違うで")
    else:
        col1, col2 = st.columns([4, 1])

        with col1:
            st.success("先生としてログイン中")

        with col2:
            if st.button("先生ログアウト"):
                st.session_state.teacher_authenticated = False
                st.rerun()

        teacher_view()