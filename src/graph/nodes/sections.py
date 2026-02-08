"""
セクション生成ノード

提案書の各セクションを生成する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm
from ...common.constants import SECTION_CHAR_LIMITS, EVALUATION_CRITERIA
from ...common.debug import debug_llm_call, debug_log


def _call_llm_with_log(
    prompt: str,
    section_name: str,
    logs: list[dict],
) -> str:
    """LLMを呼び出してログを記録"""
    debug_log(f"LLM呼び出し開始: {section_name}", f"プロンプト長: {len(prompt)}文字")

    response = call_cortex_llm(prompt)

    # デバッグログ出力
    debug_llm_call(section_name, prompt, response)

    logs.append({
        "section": section_name,
        "prompt": prompt,
        "response": response,
    })
    return response


def _build_context(state: ProposalAgentState) -> str:
    """コンテキストを構築（全文を含める）"""
    parts = []

    # 財務データ
    if state.get("financial_markdown"):
        parts.append(state["financial_markdown"])

    # 有価証券報告書（全文）
    if state.get("securities_markdown"):
        parts.append(f"# 有価証券報告書\n\n{state['securities_markdown']}")

    # 調査結果
    if state.get("research_results"):
        research_text = "\n\n".join([
            f"## {key}\n{value}"
            for key, value in state["research_results"].items()
        ])
        parts.append(f"# 調査結果\n\n{research_text}")

    return "\n\n---\n\n".join(parts)


def _format_issues_for_prompt(issues: list[dict], include_evidence: bool = True) -> str:
    """
    課題JSONをプロンプト用にフォーマット

    Args:
        issues: 課題リスト
        include_evidence: 根拠を含めるか

    Returns:
        フォーマットされた課題テキスト
    """
    if not issues:
        return "（課題データなし）"

    # 重要度でソート
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_issues = sorted(
        issues,
        key=lambda x: severity_order.get(x.get("severity", "low"), 2)
    )

    lines = []
    for issue in sorted_issues:
        severity = issue.get("severity", "medium")
        severity_mark = {"high": "【重要】", "medium": "", "low": ""}
        category = issue.get("category", "その他")
        description = issue.get("description", "")

        line = f"- {severity_mark.get(severity, '')}{category}: {description}"
        if include_evidence and issue.get("evidence"):
            line += f"（根拠: {issue.get('evidence')}）"
        lines.append(line)

    return "\n".join(lines)


def _format_issues_by_priority(issues: list[dict]) -> dict[str, list[str]]:
    """
    課題を重要度別に分類

    Returns:
        {"high": [...], "medium": [...], "low": [...]}
    """
    result = {"high": [], "medium": [], "low": []}
    for issue in issues:
        severity = issue.get("severity", "medium")
        description = f"{issue.get('category', '')}: {issue.get('description', '')}"
        if severity in result:
            result[severity].append(description)
        else:
            result["medium"].append(description)
    return result


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

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
1. 必ず{limit}字以内で作成すること（厳守・超過不可）
2. マークダウン記法（#, ##, *, -など）は絶対に使用しないこと
3. 見出しは以下の記号で階層化すること：
   - 大見出し: ■
   - 中見出し: ●
   - 小見出し: ・

【作成するセクション】
1. 企業概要・分析
   1.1 企業概要（事業内容、沿革、強み）
   1.2 外部環境分析（業界動向、地域特性）
   1.3 財務情報分析（過去3年の推移と傾向）

【内容要件】
- 具体的な数値やデータを引用すること
- 地域特性（{company_info.get('location', '')}）を踏まえた分析を含めること
- 業種特性（{company_info.get('industry', '')}）を踏まえた分析を含めること
- 官公庁/民間、元請/下請の販路構成にも言及すること
- 後続セクション（課題抽出・成長戦略）との論理的接続を意識し、分析の要点を明確にすること

【参考情報】
{context}
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
    sections = state.get("sections", {})
    overview_section = sections.get("overview", "")
    limit = SECTION_CHAR_LIMITS["issues"]
    logs: list[dict] = []

    # 課題を構造化してフォーマット
    issues_text = _format_issues_for_prompt(issues, include_evidence=True)
    issues_by_priority = _format_issues_by_priority(issues)

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
1. 必ず{limit}字以内で作成すること（厳守・超過不可）
2. マークダウン記法（#, ##, *, -など）は絶対に使用しないこと
3. 見出しは以下の記号で階層化すること：
   - 大見出し: ■
   - 中見出し: ●
   - 小見出し: ・

【作成するセクション】
2. 課題の抽出
   2.1 財務面の課題（収益性、安定性、キャッシュフロー等）
   2.2 事業面の課題（市場環境、競争力、技術等）
   2.3 人材・組織面の課題（人手不足、2024年問題、働き方改革等）

【企業概要・分析（前セクション）】
{overview_section}

【重要】
上記の企業概要・分析で示された財務状況と外部環境を踏まえ、
論理的に導かれる課題を抽出すること。過去の分析と課題の因果関係を明確にすること。

【事前に抽出された課題（重要度順）】
{issues_text}

【重要度別の課題数】
- 重要（high）: {len(issues_by_priority['high'])}件
- 中（medium）: {len(issues_by_priority['medium'])}件
- 低（low）: {len(issues_by_priority['low'])}件

【内容要件】
- 事前に抽出された課題を整理・統合すること
- 財務データから具体的な根拠を示すこと
- 建設業界共通の課題（GX/DX、人材不足、2024年問題）と照らし合わせること
- 地域特性（{company_info.get('location', '')}）に起因する課題も検討すること
- 各課題の優先度・重要度も示すこと

【参考情報】
{context}
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

    # 後半セクションでは有価証券報告書を短めに
    context = _build_context(state)
    company_info = state.get("company_info", {})
    sections = state.get("sections", {})
    issues_section = sections.get("issues", "")
    issues = state.get("issues", [])
    insights = state.get("insights", [])
    limit = SECTION_CHAR_LIMITS["strategy"]
    logs: list[dict] = []

    # 構造化された課題データを活用
    issues_by_priority = _format_issues_by_priority(issues)
    high_priority_issues = "\n".join([f"・{i}" for i in issues_by_priority["high"]]) or "（なし）"

    # 知見がある場合のみ含める
    insights_section = ""
    if insights:
        insights_text = "\n".join([f"・{insight}" for insight in insights])
        insights_section = f"""
【調査から得られた知見】
{insights_text}
"""

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
1. 必ず{limit}字以内で作成すること（厳守・超過不可）
2. マークダウン記法（#, ##, *, -など）は絶対に使用しないこと
3. 見出しは以下の記号で階層化すること：
   - 大見出し: ■
   - 中見出し: ●
   - 小見出し: ・

【作成するセクション】
3. 成長戦略・提案
   3.1 短期施策（1年以内）：即効性のある改善策
   3.2 中期施策（1-3年）：競争力強化策
   3.3 長期施策（3-5年）：持続的成長に向けた投資

【最優先で対応すべき課題（重要度: high）】
{high_priority_issues}

【課題の抽出結果（前セクション）】
{issues_section}
{insights_section}
【重要】
上記の課題から論理的に導かれる成長戦略を提案すること。
課題と戦略の因果関係を明確にし、「過去分析→課題→未来提案」の一貫性を確保すること。

【内容要件】
- 最優先課題に対応する具体的な施策を提案すること
- GX（環境技術、脱炭素）への対応策を含めること
- DX（ICT施工、BIM/CIM、省力化）への対応策を含めること
- 人材確保・育成策（2024年問題対応、外国人材活用等）を含めること
- 地域特性（{company_info.get('location', '')}）を活かした戦略を提案すること
- 実現可能性の高い具体的な施策とすること

【参考情報】
{context}
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

    # 効果試算では財務データが重要、有価証券報告書は短く
    context = _build_context(state)
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    issues = state.get("issues", [])
    limit = SECTION_CHAR_LIMITS["effects"]
    logs: list[dict] = []

    # 課題の数を把握（効果試算の根拠に使用）
    issues_by_priority = _format_issues_by_priority(issues)

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
1. 必ず{limit}字以内で作成すること（厳守・超過不可）
2. マークダウン記法（#, ##, *, -など）は絶対に使用しないこと
3. 見出しは以下の記号で階層化すること：
   - 大見出し: ■
   - 中見出し: ●
   - 小見出し: ・

【作成するセクション】
4. 効果試算
   4.1 売上・利益への影響（定量効果）
   4.2 定性的効果（ブランド、人材、技術力等）

【提案した成長戦略】
{strategy_section}

【対応する課題数】
- 重要課題: {len(issues_by_priority['high'])}件
- 中程度の課題: {len(issues_by_priority['medium'])}件

【内容要件】
- 提案した施策の効果を具体的な数値で試算すること
- 参考情報の財務データを基準に、改善率や成長率で示すこと
- 短期・中期・長期それぞれの期待効果を区分すること
- 投資対効果（ROI）の観点も含めること
- 定性的効果も具体的に記述すること

【参考情報（財務データを効果試算の基準として使用）】
{context}
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

    # ロードマップでは有価証券報告書は最小限
    context = _build_context(state)
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    issues = state.get("issues", [])
    limit = SECTION_CHAR_LIMITS["roadmap"]
    logs: list[dict] = []

    # 重要課題を施策の優先順位付けに活用
    issues_by_priority = _format_issues_by_priority(issues)
    high_priority_summary = ", ".join(issues_by_priority["high"][:3]) if issues_by_priority["high"] else "（なし）"

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
1. 必ず{limit}字以内で作成すること（厳守・超過不可）
2. マークダウン記法（#, ##, *, -など）は絶対に使用しないこと
3. 見出しは以下の記号で階層化すること：
   - 大見出し: ■
   - 中見出し: ●
   - 小見出し: ・

【作成するセクション】
5. ロードマップ
   5.1 実行計画（フェーズ別の取り組み内容）
   5.2 マイルストーン（重要な節目と達成目標）

【提案した成長戦略】
{strategy_section}

【最優先で対応すべき課題（ロードマップの優先順位付けに活用）】
{high_priority_summary}

【内容要件】
- 5年間の実行計画を示すこと
- 年度ごとの主要施策とKPIを明確にすること
- 最優先課題に対応する施策を初期フェーズに配置すること
- 優先順位と依存関係を考慮した実行順序を示すこと
- 推進体制や必要なリソースにも言及すること

【参考情報】
{context}
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
