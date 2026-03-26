import os
import re
from typing import Dict, Optional

from openai import OpenAI


def _get_client() -> Optional[OpenAI]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key == "":
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def _star_from_score_2(score: int) -> str:
    score = max(0, min(2, int(score)))
    if score == 2:
        return "★★"
    if score == 1:
        return "★☆"
    return "☆☆"


def _star_from_score_6(score: int) -> str:
    score = max(0, min(6, int(score)))
    if score >= 6:
        return "★★★"
    if score >= 4:
        return "★★☆"
    return "★☆☆"


def _extract_between(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*[:：]\s*(.*)"
    m = re.search(pattern, text)
    if not m:
        return ""
    return m.group(1).strip()


def _extract_block(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*[:：]\s*(.*?)(?:\n[A-Za-zぁ-んァ-ン一-龥]+[:：]|\Z)"
    m = re.search(pattern, text, flags=re.DOTALL)
    if not m:
        return ""
    return m.group(1).strip()


def _fallback_reflection_eval(answer_text: str, method_text: str, next_text: str) -> Dict:
    answer_text = str(answer_text).strip()
    method_text = str(method_text).strip()
    next_text = str(next_text).strip()

    def score_answer(text: str) -> int:
        if len(text) >= 40:
            return 2
        if len(text) >= 10:
            return 1
        return 0

    def score_method(text: str) -> int:
        method_keywords = ["比べ", "資料", "読み取", "話し合", "考え", "発表", "地図", "グラフ", "教科書", "ノート"]
        hit = any(k in text for k in method_keywords)
        if len(text) >= 30 and hit:
            return 2
        if len(text) >= 8:
            return 1
        return 0

    def score_next(text: str) -> int:
        next_keywords = ["次", "もっと", "調べ", "考え", "知り", "深め", "比べ", "挑戦"]
        hit = any(k in text for k in next_keywords)
        if len(text) >= 20 and hit:
            return 2
        if len(text) >= 8:
            return 1
        return 0

    answer_score = score_answer(answer_text)
    method_score = score_method(method_text)
    next_score = score_next(next_text)

    overall_score = answer_score + method_score + next_score

    return {
        "ok": False,
        "overall_star": _star_from_score_6(overall_score),
        "overall_score": overall_score,
        "overall_comment": "AI評価を取得できなかったため、簡易評価を表示しています。",
        "answer_star": _star_from_score_2(answer_score),
        "answer_score": answer_score,
        "answer_comment": "答えの内容をもう少し具体的にすると、さらに伝わりやすくなるよ。" if answer_score < 2 else "本時の問いに対する答えが具体的に書けているね。",
        "method_star": _star_from_score_2(method_score),
        "method_score": method_score,
        "method_comment": "どのように学んだかをもう少し具体的に書けるといいね。" if method_score < 2 else "自分がどう学んだかが具体的に書けているね。",
        "next_star": _star_from_score_2(next_score),
        "next_score": next_score,
        "next_comment": "次に何をしたいかを具体的に書けるとさらに良くなるよ。" if next_score < 2 else "次にどうするかが具体的に書けているね。",
        "error": "fallback",
    }


def evaluate_reflection(
    question_text: str,
    answer_text: str,
    method_text: str,
    next_text: str,
) -> Dict:
    client = _get_client()
    if client is None:
        return _fallback_reflection_eval(answer_text, method_text, next_text)

    prompt = f"""
あなたは中学校社会科の教師です。
次の生徒の振り返りを、以下の3観点について0点〜2点で評価してください。

観点
1. 答え
- 2点: 本時の問いに対する答えになっており、内容も具体的
- 1点: 答えはあるが具体性が弱い
- 0点: 答えになっていない、またはほとんど書かれていない

2. 学び方
- 2点: 比較した・資料を読み取った・話し合った・理由を考えたなど、自分がどう学んだかが具体的
- 1点: 学び方への言及はあるが具体性が弱い
- 0点: 教科書を使った、授業を受けた等だけで、自分の学び方が書かれていない

3. 次にどうするか
- 2点: 次に何を調べたいか・考えたいか・挑戦したいかが具体的
- 1点: 今後への言及はあるが曖昧
- 0点: 今後について書かれていない

生徒の記述
【本時にたてた問い】
{question_text}

【それに対する答え】
{answer_text}

【自分の学び方について】
{method_text}

【次にどうするか】
{next_text}

次の形式で、必ず日本語で簡潔に出力してください。

answer_score: 0〜2の整数
answer_comment: 一言コメント
method_score: 0〜2の整数
method_comment: 一言コメント
next_score: 0〜2の整数
next_comment: 一言コメント
overall_comment: 80字以内で、話し言葉の全体コメント
""".strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()

        def extract_int(label: str, default: int = 0) -> int:
            m = re.search(rf"{label}\s*:\s*([0-2])", text)
            if m:
                return int(m.group(1))
            return default

        def extract_text(label: str, default: str = "") -> str:
            m = re.search(rf"{label}\s*:\s*(.*)", text)
            if m:
                return m.group(1).strip()
            return default

        answer_score = extract_int("answer_score", 0)
        method_score = extract_int("method_score", 0)
        next_score = extract_int("next_score", 0)

        overall_score = answer_score + method_score + next_score

        return {
            "ok": True,
            "overall_star": _star_from_score_6(overall_score),
            "overall_score": overall_score,
            "overall_comment": extract_text("overall_comment", "よく振り返れているよ。"),
            "answer_star": _star_from_score_2(answer_score),
            "answer_score": answer_score,
            "answer_comment": extract_text("answer_comment", ""),
            "method_star": _star_from_score_2(method_score),
            "method_score": method_score,
            "method_comment": extract_text("method_comment", ""),
            "next_star": _star_from_score_2(next_score),
            "next_score": next_score,
            "next_comment": extract_text("next_comment", ""),
        }

    except Exception as e:
        result = _fallback_reflection_eval(answer_text, method_text, next_text)
        result["error"] = str(e)
        return result


def _fallback_unit_eval(unit_question: str, first_text: str, lessons_df, last_text: str) -> Dict:
    lesson_count = 0 if lessons_df is None else len(lessons_df)

    growth_hint = ""
    if str(first_text).strip() and str(last_text).strip():
        if len(str(last_text).strip()) > len(str(first_text).strip()):
            growth_hint = "学ぶ前よりも学んだ後の考えが具体的になっていて、学びの深まりが感じられます。"
        else:
            growth_hint = "最初と最後の考えを比べながら、自分の変化をふり返れているのがよいです。"
    else:
        growth_hint = "単元を通した学びの様子が見えてきています。"

    if lesson_count >= 4:
        star = "★★★"
    elif lesson_count >= 2:
        star = "★★☆"
    else:
        star = "★☆☆"

    comment = (
        f"この単元では、授業ごとの学びを積み重ねながら考えを深めようとしていました。"
        f"{growth_hint} 次の単元では、自分がどう学んだかも今より具体的に書けるとさらによくなるよ。"
    )

    return {
        "unit_star": star,
        "unit_comment": comment,
        "ok": False,
        "error": "fallback",
    }


def evaluate_unit_report(unit_question: str, first_text: str, lessons_df, last_text: str) -> Dict:
    client = _get_client()
    if client is None:
        return _fallback_unit_eval(unit_question, first_text, lessons_df, last_text)

    lessons_text = ""
    if lessons_df is not None and len(lessons_df) > 0:
        for i, (_, row) in enumerate(lessons_df.iterrows(), start=1):
            lessons_text += f"""
授業{i}
授業名：{row.get("授業名", "")}
本時の問い：{row.get("本時の問い", "")}
それに対する答え：{row.get("それに対する答え", "")}
""".strip() + "\n\n"

    prompt = f"""
あなたは中学校社会科の教師です。
次の単元レポート資料を読み、生徒に返すための「単元全体のまとめ評価」を作成してください。

評価観点
1. 最初の考えと最後の考えを比べて、考えが深まっているか
2. 各授業の答えに積み重ねがあるか
3. 最後の考えが単元全体のまとめになっているか

評価基準
★★★：考えの変化が大きく、積み重ねもあり、最後の考えが具体的
★★☆：ある程度の変化や積み重ねはあるが、最後の考えがやや抽象的
★☆☆：変化や積み重ねがあまり見えない

【大単元の問い】
{unit_question}

【学ぶ前の考え】
{first_text}

【各授業の振り返り】
{lessons_text}

【学んだ後の考え】
{last_text}

必ず次の形式で出力してください。

unit_star: ★★★ / ★★☆ / ★☆☆ のいずれか
unit_comment: 140字以内。中学生に返す話し言葉で、良かった点と次の課題をやさしく書く
""".strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content.strip()

        star_match = re.search(r"unit_star\s*:\s*(★★★|★★☆|★☆☆)", text)
        comment_match = re.search(r"unit_comment\s*:\s*(.*)", text, flags=re.DOTALL)

        unit_star = star_match.group(1).strip() if star_match else "★★☆"
        unit_comment = comment_match.group(1).strip() if comment_match else text.strip()

        return {
            "unit_star": unit_star,
            "unit_comment": unit_comment,
            "ok": True,
        }

    except Exception as e:
        result = _fallback_unit_eval(unit_question, first_text, lessons_df, last_text)
        result["error"] = str(e)
        return result