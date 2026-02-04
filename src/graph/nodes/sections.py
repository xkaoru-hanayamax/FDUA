"""
セクション生成ノード

提案書の各セクションを生成する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm
from ...common.constants import SECTION_CHAR_LIMITS


def _call_llm_with_log(
    prompt: str,
    section_name: str,
    logs: list[dict],
) -> str:
    """LLMを呼び出してログを記録"""
    response = call_cortex_llm(prompt)
    logs.append({
        "section": section_name,
        "prompt": prompt,
        "response": response,
    })
    return response


def _build_context(state: ProposalAgentState) -> str:
    """コンテキストを構築"""
    parts = []

    # 財務データ
    if state.get("financial_markdown"):
        parts.append(state["financial_markdown"])

    # 有価証券報告書
    if state.get("securities_markdown"):
        # 長すぎる場合は改行位置で切り詰め
        securities = state["securities_markdown"]
        if len(securities) > 30000:
            cut_pos = securities[:30000].rfind("\n")
            if cut_pos > 20000:
                securities = securities[:cut_pos] + "\n\n（以下省略）"
            else:
                securities = securities[:30000]
        parts.append(f"# 有価証券報告書\n\n{securities}")

    # 調査結果
    if state.get("research_results"):
        research_text = "\n\n".join([
            f"## {key}\n{value}"
            for key, value in state["research_results"].items()
        ])
        parts.append(f"# 調査結果\n\n{research_text}")

    # 知見
    if state.get("insights"):
        insights_text = "\n".join([f"- {insight}" for insight in state["insights"]])
        parts.append(f"# 抽出した知見\n\n{insights_text}")

    return "\n\n---\n\n".join(parts)


def generate_overview(state: ProposalAgentState) -> dict[str, Any]:
    """
    セクション1: 企業概要・分析を生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[generate_overview] セクション1: 企業概要・分析を生成中...")

    context = _build_context(state)
    company_info = state.get("company_info", {})
    limit = SECTION_CHAR_LIMITS["overview"]
    logs: list[dict] = []

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「企業概要・分析」セクションを作成してください。

{context}

【作成するセクション】
1. 企業概要・分析
   1.1 企業概要（事業内容、沿革、強み）
   1.2 外部環境分析（業界動向、地域特性）
   1.3 財務情報分析（過去3年の推移と傾向）

【要件】
- 具体的な数値やデータを引用すること
- 地域特性（{company_info.get('location', '')}）を踏まえた分析を含めること
- 業種特性（{company_info.get('industry', '')}）を踏まえた分析を含めること
- 官公庁/民間、元請/下請の販路構成にも言及すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

    response = _call_llm_with_log(prompt, "企業概要・分析", logs)

    sections = state.get("sections", {})
    sections["overview"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["overview"] = len(response)

    print(f"  - 文字数: {len(response)}字 (上限: {limit}字)")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }


def generate_issues(state: ProposalAgentState) -> dict[str, Any]:
    """
    セクション2: 課題の抽出を生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[generate_issues] セクション2: 課題の抽出を生成中...")

    context = _build_context(state)
    company_info = state.get("company_info", {})
    issues = state.get("issues", [])
    limit = SECTION_CHAR_LIMITS["issues"]
    logs: list[dict] = []

    # 課題を文字列に変換
    issues_text = "\n".join([
        f"- [{issue.get('category')}] {issue.get('description')} (重要度: {issue.get('severity')}, 根拠: {issue.get('evidence', '')})"
        for issue in issues
    ])

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「課題の抽出」セクションを作成してください。

{context}

【事前に抽出された課題】
{issues_text}

【作成するセクション】
2. 課題の抽出
   2.1 財務面の課題（収益性、安定性、キャッシュフロー等）
   2.2 事業面の課題（市場環境、競争力、技術等）
   2.3 人材・組織面の課題（人手不足、2024年問題、働き方改革等）

【要件】
- 事前に抽出された課題を整理・統合すること
- 財務データとRAG情報から具体的な根拠を示すこと
- 建設業界共通の課題（GX/DX、人材不足、2024年問題）と照らし合わせること
- 地域特性（{company_info.get('location', '')}）に起因する課題も検討すること
- 各課題の優先度・重要度も示すこと
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

    response = _call_llm_with_log(prompt, "課題の抽出", logs)

    sections = state.get("sections", {})
    sections["issues"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["issues"] = len(response)

    print(f"  - 文字数: {len(response)}字 (上限: {limit}字)")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }


def generate_strategy(state: ProposalAgentState) -> dict[str, Any]:
    """
    セクション3: 成長戦略・提案を生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[generate_strategy] セクション3: 成長戦略・提案を生成中...")

    context = _build_context(state)
    sections = state.get("sections", {})
    issues_section = sections.get("issues", "")
    insights = state.get("insights", [])
    limit = SECTION_CHAR_LIMITS["strategy"]
    logs: list[dict] = []

    insights_text = "\n".join([f"- {insight}" for insight in insights]) if insights else ""

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「成長戦略・提案」セクションを作成してください。

{context}

【抽出された課題】
{issues_section}

【調査から得られた知見】
{insights_text}

【作成するセクション】
3. 成長戦略・提案
   3.1 短期施策（1年以内）：即効性のある改善策
   3.2 中期施策（1-3年）：競争力強化策
   3.3 長期施策（3-5年）：持続的成長に向けた投資

【要件】
- 抽出した課題に対応する具体的な施策を提案すること
- GX（環境技術、脱炭素）への対応策を含めること
- DX（ICT施工、BIM/CIM、省力化）への対応策を含めること
- 人材確保・育成策（2024年問題対応、外国人材活用等）を含めること
- 地域特性を活かした戦略を提案すること
- 調査で得られた知見を活用すること
- 実現可能性の高い具体的な施策とすること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

    response = _call_llm_with_log(prompt, "成長戦略・提案", logs)

    sections["strategy"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["strategy"] = len(response)

    print(f"  - 文字数: {len(response)}字 (上限: {limit}字)")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }


def generate_effects(state: ProposalAgentState) -> dict[str, Any]:
    """
    セクション4: 効果試算を生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[generate_effects] セクション4: 効果試算を生成中...")

    context = _build_context(state)
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    limit = SECTION_CHAR_LIMITS["effects"]
    logs: list[dict] = []

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「効果試算」セクションを作成してください。

{context}

【提案した成長戦略】
{strategy_section}

【作成するセクション】
4. 効果試算
   4.1 売上・利益への影響（定量効果）
   4.2 定性的効果（ブランド、人材、技術力等）

【要件】
- 提案した施策の効果を具体的な数値で試算すること
- 現在の財務データを基準に、改善率や成長率で示すこと
- 短期・中期・長期それぞれの期待効果を区分すること
- 投資対効果（ROI）の観点も含めること
- 定性的効果も具体的に記述すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

    response = _call_llm_with_log(prompt, "効果試算", logs)

    sections["effects"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["effects"] = len(response)

    print(f"  - 文字数: {len(response)}字 (上限: {limit}字)")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }


def generate_roadmap(state: ProposalAgentState) -> dict[str, Any]:
    """
    セクション5: ロードマップを生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[generate_roadmap] セクション5: ロードマップを生成中...")

    context = _build_context(state)
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    limit = SECTION_CHAR_LIMITS["roadmap"]
    logs: list[dict] = []

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「ロードマップ」セクションを作成してください。

{context}

【提案した成長戦略】
{strategy_section}

【作成するセクション】
5. ロードマップ
   5.1 実行計画（フェーズ別の取り組み内容）
   5.2 マイルストーン（重要な節目と達成目標）

【要件】
- 5年間の実行計画を示すこと
- 年度ごとの主要施策とKPIを明確にすること
- 優先順位と依存関係を考慮した実行順序を示すこと
- 推進体制や必要なリソースにも言及すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

    response = _call_llm_with_log(prompt, "ロードマップ", logs)

    sections["roadmap"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["roadmap"] = len(response)

    print(f"  - 文字数: {len(response)}字 (上限: {limit}字)")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }
