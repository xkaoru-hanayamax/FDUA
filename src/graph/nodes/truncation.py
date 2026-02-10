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
from ...common.constants import (
    SECTION_CHAR_LIMITS,
    PROPOSAL_MAX_CHARS,
    SECTION_HEADING_TEMPLATES,
)
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
   - セクション内の大見出し: ## 見出し
   - セクション内の中見出し: ### 見出し
   - #### 以下の見出しは使用しないこと
   - 見出しに番号（1. 2. 等）は付けないこと
   - 箇条書き: - 項目
4. 必ず以下の5つのセクション見出しを含めること:
   # 企業概要・分析
   # 課題の抽出
   # 成長戦略・提案
   # 効果試算
   # ロードマップ
5. 各セクション内の ## / ### 見出し構成は以下のテンプレートに統一すること:

--- 企業概要・分析 ---
{SECTION_HEADING_TEMPLATES["overview"]}

--- 課題の抽出 ---
{SECTION_HEADING_TEMPLATES["issues"]}

--- 成長戦略・提案 ---
{SECTION_HEADING_TEMPLATES["strategy"]}

--- 効果試算 ---
{SECTION_HEADING_TEMPLATES["effects"]}

--- ロードマップ ---
{SECTION_HEADING_TEMPLATES["roadmap"]}

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

5. 提案の具体性確保
   - 「検討する」「推進する」等の抽象表現を具体的な施策内容に置き換え
   - 可能な限り数値目標（KPI）を含めること

【重要】
- 各セクションの主要な論点と具体的数値は維持すること
- 5つのセクション見出し「# セクション名」は必ず出力すること
- 「【総文字数: ...】」等の文字数カウントやメタ情報は一切含めないこと。提案書の本文のみを出力すること

【統合対象テキスト】
{merged_text}
"""


def _create_compression_prompt(merged_text: str, current_chars: int, target_chars: int) -> str:
    """
    文字数削減に特化した圧縮プロンプトを生成
    """
    reduction = current_chars - target_chars
    return f"""【タスク】
以下の提案書を圧縮してください。

【現在の文字数】{current_chars}字
【目標文字数】{target_chars}字以内（現在より約{reduction}字の削減が必要）

【圧縮ルール】
- セクション見出し（# / ## / ###）はすべて維持し、削除・変更しないこと
- 具体的な数値データ（売上高、利益率、金額等）は維持すること
- 冗長な修飾語・繰り返し表現・抽象的な前置きを優先的に削除すること
- 箇条書きの項目数を減らすよりも、各項目の記述を簡潔にすること
- 文章が途中で切れないようにすること。すべての文を完結させること
- マークダウン形式を維持すること
- 「【総文字数: ...】」等の文字数カウントやメタ情報は一切含めないこと。提案書の本文のみを出力すること

【対象テキスト】
{merged_text}"""


def check_and_truncate(state: ProposalAgentState) -> dict[str, Any]:
    """
    全セクションを統合して品質向上・文字数調整を行う

    処理フロー:
    1. Phase 1: 5セクション統合 + LLMで全体最適化（品質向上+文字数調整）
    2. Phase 2: 文字数超過時、専用圧縮パスで削減（最大2回）

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

    # === Phase 1: 統合パス（品質向上 + 初回圧縮の試み）===
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

    # マークダウンヘッダーでセクション分割
    new_sections = _split_sections_from_markdown(response)

    # 分割できなかったセクションは元のセクションを使用
    for key in SECTION_KEYS:
        if key not in new_sections or not new_sections[key]:
            if key in original_sections:
                print(f"  ⚠ {SECTION_NAMES[key]}の分割に失敗。元のテキストを使用。")
                new_sections[key] = original_sections[key]

    phase1_total = sum(len(s) for s in new_sections.values())
    print(f"  - Phase 1後合計: {phase1_total}字 (上限: {PROPOSAL_MAX_CHARS}字)")

    # === Phase 2: 専用圧縮パス（文字数超過時のみ）===
    for attempt in range(2):
        total_chars = sum(len(s) for s in new_sections.values())
        if total_chars <= PROPOSAL_MAX_CHARS:
            break

        print(f"  ⚠ {total_chars}字で上限{PROPOSAL_MAX_CHARS}字を超過。圧縮パス({attempt + 1}/2)...")
        merged = _merge_sections_as_markdown(new_sections)
        target = PROPOSAL_MAX_CHARS - 500
        compress_prompt = _create_compression_prompt(merged, total_chars, target)
        compressed_response = call_cortex_llm(compress_prompt, max_tokens=32000)
        debug_llm_call(f"圧縮パス{attempt + 1}", compress_prompt, compressed_response)

        logs.append({
            "section": f"圧縮パス({attempt + 1}/2)",
            "prompt": compress_prompt,
            "response": compressed_response,
        })

        compressed_sections = _split_sections_from_markdown(compressed_response)
        # 分割成功したセクションのみ更新
        for key in SECTION_KEYS:
            if key in compressed_sections and compressed_sections[key]:
                new_sections[key] = compressed_sections[key]

        new_total = sum(len(s) for s in new_sections.values())
        print(f"    → {total_chars}字 → {new_total}字")

    # 文字数の再計算
    section_char_counts = {key: len(text) for key, text in new_sections.items()}
    total_chars = sum(section_char_counts.values())

    print(f"  - 最終合計: {total_chars}字 (上限: {PROPOSAL_MAX_CHARS}字)")
    for key in SECTION_KEYS:
        if key in section_char_counts:
            count = section_char_counts[key]
            limit = SECTION_CHAR_LIMITS.get(key, 0)
            print(f"    - {SECTION_NAMES[key]}: {count}字 (目安: {limit}字)")

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
