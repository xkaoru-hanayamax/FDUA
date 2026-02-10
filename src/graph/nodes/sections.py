"""
セクション生成ノード

提案書の各セクションを生成する（マークダウン形式）
各セクションはマークダウンファイルとして保存される
"""

from pathlib import Path
from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm
from ...common.constants import (
    EVALUATION_CRITERIA,
    SECTION_CHAR_LIMITS,
    SECTION_HEADING_TEMPLATES,
    HEADING_RULES,
)
from ...common.debug import debug_llm_call, debug_log
from ...common.config import Config


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


def _save_section_markdown(
    company_code: str,
    section_key: str,
    content: str,
    config_dict: dict,
) -> Path:
    """
    セクションをマークダウンファイルとして保存

    Args:
        company_code: 企業コード
        section_key: セクションキー
        content: セクション内容
        config_dict: 設定辞書

    Returns:
        保存したファイルパス
    """
    if config_dict.get("data_dir"):
        config = Config(data_dir=config_dict["data_dir"])
    else:
        config = Config()

    file_path = config.get_section_path(company_code, section_key)
    file_path.write_text(content, encoding="utf-8")
    print(f"  - 保存: {file_path}")
    return file_path


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
    company_code = state["company_code"]
    company_info = state.get("company_info", {})
    config_dict = state.get("config", {})
    logs: list[dict] = []

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式】
マークダウン形式で出力してください。箇条書きは - を使用してください。
{HEADING_RULES}

{SECTION_HEADING_TEMPLATES["overview"]}

上記テンプレートの [角括弧] 部分を企業固有の内容に置き換えて記述してください。
## の見出しテキストはテンプレート通りの文言を使用し、変更しないでください。
### の見出しは企業固有の内容に置き換えてよいですが、構造（数・配置）はテンプレートに準拠してください。

【文字数の目安】
約{SECTION_CHAR_LIMITS["overview"]}字を目安に出力してください。

【内容要件】
- 具体的な数値やデータを引用すること
- 地域特性（{company_info.get('location', '')}）を踏まえた分析を含めること
- 業種特性（{company_info.get('industry', '')}）を踏まえた分析を含めること
- 官公庁/民間、元請/下請の販路構成にも言及すること
- 売上構成（完成工事高、不動産事業、商品売上等）の内訳にも言及すること
- Web調査結果から得られた地域の最新動向（人口動態、公共事業計画、産業構造の変化）も分析に組み込むこと
- 後続セクション（課題抽出・成長戦略）との論理的接続を意識し、分析の要点を明確にすること

【参考情報】
{context}
"""

    response = _call_llm_with_log(prompt, "企業概要・分析", logs)

    # マークダウンファイルとして保存
    _save_section_markdown(company_code, "overview", response, config_dict)

    sections = state.get("sections", {})
    sections["overview"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["overview"] = len(response)

    print(f"  - 文字数: {len(response)}字")

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
    company_code = state["company_code"]
    company_info = state.get("company_info", {})
    config_dict = state.get("config", {})
    issues = state.get("issues", [])
    sections = state.get("sections", {})
    overview_section = sections.get("overview", "")
    logs: list[dict] = []

    # 課題を構造化してフォーマット
    issues_text = _format_issues_for_prompt(issues, include_evidence=True)
    issues_by_priority = _format_issues_by_priority(issues)

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式】
マークダウン形式で出力してください。箇条書きは - を使用してください。
{HEADING_RULES}

{SECTION_HEADING_TEMPLATES["issues"]}

上記テンプレートの [角括弧] 部分を企業固有の内容に置き換えて記述してください。
## の見出しテキストはテンプレート通りの文言を使用し、変更しないでください。
### の見出しは企業固有の内容に置き換えてよいですが、構造（数・配置）はテンプレートに準拠してください。
各カテゴリ（財務面・事業面・人材組織面）内の ### 課題数は2-4個としてください。
課題タイトルに【重要】を付与してよいですが、番号は付けないでください。

【文字数の目安】
約{SECTION_CHAR_LIMITS["issues"]}字を目安に出力してください。

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
- Web調査結果から判明した外部環境の変化（地域需要、業界トレンド、GX/DX動向）を課題の根拠として活用すること
- 各課題の優先度・重要度も示すこと

【参考情報】
{context}
"""

    response = _call_llm_with_log(prompt, "課題の抽出", logs)

    # マークダウンファイルとして保存
    _save_section_markdown(company_code, "issues", response, config_dict)

    sections = state.get("sections", {})
    sections["issues"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["issues"] = len(response)

    print(f"  - 文字数: {len(response)}字")

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
    company_code = state["company_code"]
    company_info = state.get("company_info", {})
    config_dict = state.get("config", {})
    sections = state.get("sections", {})
    issues_section = sections.get("issues", "")
    issues = state.get("issues", [])
    logs: list[dict] = []

    # 構造化された課題データを活用
    issues_by_priority = _format_issues_by_priority(issues)
    high_priority_issues = "\n".join([f"- {i}" for i in issues_by_priority["high"]]) or "（なし）"

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式】
マークダウン形式で出力してください。箇条書きは - を使用してください。
{HEADING_RULES}

{SECTION_HEADING_TEMPLATES["strategy"]}

上記テンプレートの [角括弧] 部分を企業固有の内容に置き換えて記述してください。
## の見出しテキストはテンプレート通りの文言を使用し、変更しないでください。
### の見出しは企業固有の内容に置き換えてよいですが、構造（数・配置）はテンプレートに準拠してください。
各時間軸内の ### 施策数は2-4個としてください。

【文字数の目安】
約{SECTION_CHAR_LIMITS["strategy"]}字を目安に出力してください。

【最優先で対応すべき課題（重要度: high）】
{high_priority_issues}

【課題の抽出結果（前セクション）】
{issues_section}

【重要】
上記の課題から論理的に導かれる成長戦略を提案すること。
課題と戦略の因果関係を明確にし、「過去分析→課題→未来提案」の一貫性を確保すること。
参考情報に含まれるWeb調査結果（地域動向・GX/DX・人材市場等のAI要約）を戦略立案の根拠として活用すること。

【内容要件】
- 最優先課題に対応する具体的な施策を提案すること
- GX（環境技術、脱炭素）への対応策を含めること
- DX（ICT施工、BIM/CIM、省力化）への対応策を含めること
- 人材確保・育成策（2024年問題対応、外国人材活用等）を含めること
- 地域特性（{company_info.get('location', '')}）を活かした戦略を提案すること
- 参考情報に含まれるWeb調査結果（地域動向・GX/DX・人材市場等）を戦略立案の根拠として活用すること
- 各施策には想定投資額の目安と期待される効果を簡潔に付記すること
- 実現可能性の高い具体的な施策とすること

【参考情報】
{context}
"""

    response = _call_llm_with_log(prompt, "成長戦略・提案", logs)

    # マークダウンファイルとして保存
    _save_section_markdown(company_code, "strategy", response, config_dict)

    sections["strategy"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["strategy"] = len(response)

    print(f"  - 文字数: {len(response)}字")

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
    company_code = state["company_code"]
    config_dict = state.get("config", {})
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    overview_section = sections.get("overview", "")
    issues = state.get("issues", [])
    logs: list[dict] = []

    # 課題の数を把握（効果試算の根拠に使用）
    issues_by_priority = _format_issues_by_priority(issues)

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式】
マークダウン形式で出力してください。箇条書きは - を使用してください。
{HEADING_RULES}

{SECTION_HEADING_TEMPLATES["effects"]}

上記テンプレートの [角括弧] 部分を企業固有の内容に置き換えて記述してください。
## の見出しテキストはテンプレート通りの文言を使用し、変更しないでください。
### の見出しは企業固有の内容に置き換えてよいですが、構造（数・配置）はテンプレートに準拠してください。
「## 総合効果サマリー」は必ず含めてください。

【文字数の目安】
約{SECTION_CHAR_LIMITS["effects"]}字を目安に出力してください。

【企業概要・財務分析（効果試算のベースライン）】
{overview_section}

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

    # マークダウンファイルとして保存
    _save_section_markdown(company_code, "effects", response, config_dict)

    sections["effects"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["effects"] = len(response)

    print(f"  - 文字数: {len(response)}字")

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
    company_code = state["company_code"]
    config_dict = state.get("config", {})
    sections = state.get("sections", {})
    strategy_section = sections.get("strategy", "")
    issues = state.get("issues", [])
    logs: list[dict] = []

    # 重要課題を施策の優先順位付けに活用
    issues_by_priority = _format_issues_by_priority(issues)
    high_priority_summary = ", ".join(issues_by_priority["high"][:5]) if issues_by_priority["high"] else "（なし）"
    medium_priority_summary = ", ".join(issues_by_priority["medium"][:3]) if issues_by_priority["medium"] else ""

    # 中程度の課題セクション（存在する場合のみ）
    medium_section = ""
    if medium_priority_summary:
        medium_section = f"""
【中程度の優先課題（フェーズ2以降で対応）】
{medium_priority_summary}
"""

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタントです。

{EVALUATION_CRITERIA}

【出力形式】
マークダウン形式で出力してください。箇条書きは - を使用してください。
{HEADING_RULES}

{SECTION_HEADING_TEMPLATES["roadmap"]}

上記テンプレートの [角括弧] 部分を企業固有の内容に置き換えて記述してください。
## の見出しテキストはテンプレート通りの文言を使用し、変更しないでください。
### の見出しは企業固有の内容に置き換えてよいですが、構造（数・配置）はテンプレートに準拠してください。
フェーズは必ず3つとしてください。「## マイルストーン」と「## 推進体制」は必ず含めてください。

【文字数の目安】
約{SECTION_CHAR_LIMITS["roadmap"]}字を目安に出力してください。

【提案した成長戦略】
{strategy_section}

【最優先で対応すべき課題（ロードマップの優先順位付けに活用）】
{high_priority_summary}
{medium_section}
【内容要件】
- 5年間の実行計画を示すこと
- 年度ごとの主要施策とKPIを明確にすること
- 最優先課題に対応する施策を初期フェーズに配置すること
- 中程度の課題はフェーズ2以降に配置すること
- 優先順位と依存関係を考慮した実行順序を示すこと
- 推進体制や必要なリソースにも言及すること

【参考情報】
{context}
"""

    response = _call_llm_with_log(prompt, "ロードマップ", logs)

    # マークダウンファイルとして保存
    _save_section_markdown(company_code, "roadmap", response, config_dict)

    sections["roadmap"] = response

    section_char_counts = state.get("section_char_counts", {})
    section_char_counts["roadmap"] = len(response)

    print(f"  - 文字数: {len(response)}字")

    return {
        "sections": sections,
        "section_char_counts": section_char_counts,
        "prompt_logs": logs,
    }
