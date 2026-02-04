"""
文字数制御ノード

各セクションの文字数をチェックし、超過時は短縮する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm
from ...common.constants import SECTION_CHAR_LIMITS, PROPOSAL_MAX_CHARS


def _truncate_at_sentence(text: str, limit: int) -> str:
    """
    文の区切りで切り詰めて上限以内に収める

    Args:
        text: 切り詰め対象テキスト
        limit: 文字数上限

    Returns:
        上限以内に収まるテキスト
    """
    if len(text) <= limit:
        return text

    # 上限位置までのテキスト
    cut_text = text[:limit]

    # 句点（。）で切る
    last_period = cut_text.rfind("。")
    if last_period > limit * 0.5:
        return cut_text[:last_period + 1]

    # 改行で切る
    last_newline = cut_text.rfind("\n")
    if last_newline > limit * 0.5:
        return cut_text[:last_newline]

    # 読点（、）で切る
    last_comma = cut_text.rfind("、")
    if last_comma > limit * 0.5:
        return cut_text[:last_comma + 1]

    # どの区切りもない場合は上限で切る（最終手段）
    return cut_text


def _truncate_section(
    text: str,
    section_name: str,
    limit: int,
    logs: list[dict],
) -> str:
    """
    超過したセクションをLLMで短縮

    Args:
        text: 元のセクションテキスト
        section_name: セクション名（ログ用）
        limit: 文字数上限
        logs: プロンプトログ

    Returns:
        短縮されたテキスト
    """
    current_len = len(text)
    if current_len <= limit:
        return text

    print(f"  ⚠ {section_name}が{current_len}字で上限{limit}字を超過。短縮中...")

    prompt = f"""以下のテキストを{limit}字以内に短縮してください。

【重要な要件】
- 必ず{limit}字以内に収めること（厳守）
- 主要な論点と具体的な数値は維持すること
- 冗長な表現や繰り返しを削除すること
- 構造（見出し「■」「●」「・」）は維持すること
- 内容の質を落とさずに簡潔化すること

【短縮対象テキスト】
{text}
"""

    shortened = call_cortex_llm(prompt)

    logs.append({
        "section": f"{section_name}（短縮）",
        "prompt": prompt,
        "response": shortened,
    })

    # 短縮後も超過していたら強制切り詰め（文の区切りで切る）
    new_len = len(shortened)
    if new_len > limit:
        print(f"  ⚠ 短縮後も{new_len}字で超過。文の区切りで切り詰め...")
        shortened = _truncate_at_sentence(shortened, limit)

    print(f"  → {current_len}字 → {len(shortened)}字に短縮完了")
    return shortened


def check_and_truncate(state: ProposalAgentState) -> dict[str, Any]:
    """
    全セクションの文字数をチェックし、超過時は短縮する

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[check_and_truncate] 文字数チェック・短縮中...")

    sections = state.get("sections", {})
    section_char_counts = state.get("section_char_counts", {})
    logs: list[dict] = []

    section_names = {
        "overview": "企業概要・分析",
        "issues": "課題の抽出",
        "strategy": "成長戦略・提案",
        "effects": "効果試算",
        "roadmap": "ロードマップ",
    }

    truncated = False

    for key, name in section_names.items():
        if key not in sections:
            continue

        limit = SECTION_CHAR_LIMITS.get(key, 3000)
        text = sections[key]
        char_count = len(text)

        if char_count > limit:
            truncated = True
            sections[key] = _truncate_section(text, name, limit, logs)
            section_char_counts[key] = len(sections[key])
        else:
            section_char_counts[key] = char_count

    # 合計文字数を確認
    total_chars = sum(len(s) for s in sections.values())
    print(f"  - 全セクション合計: {total_chars}字 (上限: {PROPOSAL_MAX_CHARS}字)")

    # is_info_sufficientをFalseにして再調査が必要かどうか判定
    # 大幅な短縮が必要だった場合は、情報不足の可能性
    needs_more_info = truncated and total_chars > PROPOSAL_MAX_CHARS * 0.9

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "is_info_sufficient": not needs_more_info,
        "prompt_logs": logs,
    }
