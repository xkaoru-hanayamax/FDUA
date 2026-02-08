"""
文字数制御ノード

全セクションを統合して文字数調整・品質向上を行う
入力: マークダウン形式（sections.pyから）
出力: マークダウン形式（docx_writerでWord要素に変換）
"""

import re
from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm
from ...common.constants import SECTION_CHAR_LIMITS, PROPOSAL_MAX_CHARS
from ...common.debug import debug_log, debug_llm_call


# セクションキーと日本語名の対応
SECTION_NAMES = {
    "overview": "企業概要・分析",
    "issues": "課題の抽出",
    "strategy": "成長戦略・提案",
    "effects": "効果試算",
    "roadmap": "ロードマップ",
}

# セクションキーの順序
SECTION_KEYS = ["overview", "issues", "strategy", "effects", "roadmap"]


def _markdown_to_symbols(text: str) -> str:
    """
    マークダウン形式を■●・形式に変換（最終出力用）

    ### → ・（小見出し）
    ## → ●（中見出し）
    # → ■（大見出し）
    - → ・
    * → ・
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        # ###を先にチェック
        if stripped.startswith("### "):
            result.append("・" + stripped[4:].strip())
        elif stripped.startswith("## "):
            result.append("● " + stripped[3:].strip())
        elif stripped.startswith("# "):
            result.append("■ " + stripped[2:].strip())
        elif stripped.startswith("- "):
            result.append("・" + stripped[2:].strip())
        elif stripped.startswith("* "):
            result.append("・" + stripped[2:].strip())
        else:
            result.append(line)
    return "\n".join(result)


def _merge_sections_as_markdown(sections: dict[str, str]) -> str:
    """
    5セクションをマークダウン形式で統合

    各セクションは「# セクション名」で区切られる
    """
    parts = []
    for key in SECTION_KEYS:
        if key in sections:
            section_name = SECTION_NAMES[key]
            content = sections[key]
            # セクションヘッダーを追加
            parts.append(f"# {section_name}\n\n{content}")
    return "\n\n---\n\n".join(parts)


def _split_sections_from_markdown(merged_text: str) -> dict[str, str]:
    """
    マークダウン形式のテキストからセクションを分割

    「# セクション名」で分割して返す（マークダウン形式のまま）
    """
    sections = {}

    # 各セクション名を順番に探す
    for i, key in enumerate(SECTION_KEYS):
        section_name = SECTION_NAMES[key]
        # このセクションの開始位置を探す
        pattern = rf"#\s*{re.escape(section_name)}"
        match = re.search(pattern, merged_text)

        if match:
            start = match.end()
            # 次のセクションの開始位置を探す
            end = len(merged_text)
            for next_key in SECTION_KEYS[i + 1:]:
                next_name = SECTION_NAMES[next_key]
                next_pattern = rf"#\s*{re.escape(next_name)}"
                next_match = re.search(next_pattern, merged_text[start:])
                if next_match:
                    end = start + next_match.start()
                    break

            # セクション内容を抽出
            content = merged_text[start:end].strip()
            # ---区切りを削除
            content = re.sub(r"^---\s*", "", content)
            content = re.sub(r"\s*---$", "", content)
            content = content.strip()

            # マークダウン形式のまま保持（Word変換はdocx_writerで行う）
            sections[key] = content

    return sections


def _create_integration_prompt(merged_text: str) -> str:
    """
    全体統合処理用のプロンプトを生成
    """
    total_limit = PROPOSAL_MAX_CHARS - 500  # ヘッダー等の余裕

    return f"""【役割】
あなたは建設業界に詳しい経営コンサルタントであり、提案書のエディターです。

【タスク】
以下の5セクションからなる提案書全体を校正・最適化してください。

【出力形式の厳守事項】
1. 総文字数を{total_limit}字以内に収めること（厳守・超過不可）
2. 各セクションの目安文字数:
   - 企業概要・分析: 約{SECTION_CHAR_LIMITS["overview"]}字
   - 課題の抽出: 約{SECTION_CHAR_LIMITS["issues"]}字
   - 成長戦略・提案: 約{SECTION_CHAR_LIMITS["strategy"]}字
   - 効果試算: 約{SECTION_CHAR_LIMITS["effects"]}字
   - ロードマップ: 約{SECTION_CHAR_LIMITS["roadmap"]}字
3. マークダウン形式で出力すること
   - セクション見出し: # セクション名
   - 大見出し: ## 見出し
   - 中見出し: ### 見出し
   - 箇条書き: - 項目
4. 必ず以下の5つのセクション見出しを含めること:
   # 企業概要・分析
   # 課題の抽出
   # 成長戦略・提案
   # 効果試算
   # ロードマップ

【品質向上の要件】
1. 用語・文体の統一
   - 企業名、業界用語の表記揺れを統一
   - 敬体（です・ます調）で統一
   - 専門用語の使い方を一貫させる

2. 冗長表現の削除
   - 同じ意味の繰り返しを削除
   - 不要な修飾語を削減
   - 簡潔な表現に置き換え

3. セクション間の論理的つながり改善
   - 分析→課題→戦略→効果→ロードマップの因果関係を明確化
   - 前後のセクションを参照する接続表現を追加
   - 一貫したストーリーラインを構築

4. 重複内容の排除
   - 同じ情報が複数セクションに記載されている場合は統合
   - 各セクションの役割に応じて適切な場所に配置

【重要】
- 各セクションの主要な論点と具体的数値は維持すること
- 5つのセクション見出し「# セクション名」は必ず出力すること
- 「【総文字数: ...】」等の文字数カウントやメタ情報は一切含めないこと。提案書の本文のみを出力すること

【統合対象テキスト】
{merged_text}
"""


def check_and_truncate(state: ProposalAgentState) -> dict[str, Any]:
    """
    全セクションを統合して品質向上・文字数調整を行う

    処理フロー:
    1. 5セクション（マークダウン形式）を統合
    2. LLMで全体最適化（品質向上+文字数調整）
    3. マークダウンヘッダーでセクションに分割
    4. ■●・形式に変換して返却

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[check_and_truncate] 全体統合処理（品質向上・文字数調整）中...")

    sections = state.get("sections", {})
    logs: list[dict] = []

    # 元のセクションを保存
    original_sections = dict(sections)

    # 現在の合計文字数を確認
    current_total = sum(len(s) for s in sections.values())
    print(f"  - 処理前合計: {current_total}字")

    # Phase 1: マークダウン形式で統合
    merged_text = _merge_sections_as_markdown(sections)
    prompt = _create_integration_prompt(merged_text)

    # LLM呼び出し
    response = call_cortex_llm(prompt, max_tokens=32000)
    debug_llm_call("全体統合処理", prompt, response)

    logs.append({
        "section": "全体統合処理（品質向上・文字数調整）",
        "prompt": prompt,
        "response": response,
    })

    # Phase 2: マークダウンヘッダーでセクション分割（■●・形式に変換）
    new_sections = _split_sections_from_markdown(response)

    # 分割できなかったセクションは元のセクションを使用
    for key in SECTION_KEYS:
        if key not in new_sections or not new_sections[key]:
            if key in original_sections:
                print(f"  ⚠ {SECTION_NAMES[key]}の分割に失敗。元のテキストを使用。")
                new_sections[key] = original_sections[key]

    # 超過セクションの個別圧縮（最大2回リトライ）
    for key in SECTION_KEYS:
        limit = SECTION_CHAR_LIMITS.get(key, 99999)
        for attempt in range(2):
            if key in new_sections and len(new_sections[key]) > limit:
                current_len = len(new_sections[key])
                print(f"  ⚠ {SECTION_NAMES[key]}が{current_len}字で上限{limit}字を超過。圧縮リトライ({attempt+1}/2)...")
                compress_prompt = f"""以下の文章を{limit}字以内に圧縮してください。
内容の要点と具体的数値は維持し、冗長な表現や重複を削って自然な文章のまま短縮すること。
マークダウン形式を維持すること。文字数カウント等のメタ情報は含めないこと。

{new_sections[key]}"""
                compressed = call_cortex_llm(compress_prompt)
                if compressed and len(compressed) < current_len:
                    new_sections[key] = compressed
                    print(f"    → {len(compressed)}字に圧縮")
                else:
                    break
            else:
                break

    # 文字数の再計算
    section_char_counts = {key: len(text) for key, text in new_sections.items()}
    total_chars = sum(section_char_counts.values())

    print(f"  - 処理後合計: {total_chars}字 (上限: {PROPOSAL_MAX_CHARS}字)")
    for key in SECTION_KEYS:
        if key in section_char_counts:
            count = section_char_counts[key]
            limit = SECTION_CHAR_LIMITS.get(key, 0)
            status = "OK" if count <= limit else "超過"
            print(f"    - {SECTION_NAMES[key]}: {count}字 / {limit}字 [{status}]")

    debug_log(
        "truncation",
        f"全体統合処理: {current_total}字 → {total_chars}字",
    )

    return {
        "sections": new_sections,
        "section_char_counts": section_char_counts,
        "is_info_sufficient": True,
        "prompt_logs": logs,
    }
