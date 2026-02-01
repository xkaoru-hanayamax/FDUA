"""
Web調査エージェント

不足情報をWeb検索で補完する

Note:
    Snowflake環境ではWeb検索APIが利用できない場合があるため、
    LLMの事前学習知識をベースにした情報生成にフォールバックする
"""

import json
from typing import Any, Optional

from langgraph.graph import StateGraph, START, END

from ..states.research_state import WebResearcherState
from ...llm import call_cortex_llm


def _call_llm_with_log(
    prompt: str,
    step_name: str,
    logs: list[dict],
) -> str:
    """LLMを呼び出してログを記録"""
    response = call_cortex_llm(prompt)
    logs.append({
        "step": step_name,
        "prompt": prompt,
        "response": response,
    })
    return response


def search_industry_trends(state: WebResearcherState) -> dict[str, Any]:
    """
    業界動向を調査

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    company_info = state.get("company_info", {})
    search_queries = state.get("search_queries", [])

    # 業界関連のクエリをフィルタ
    industry_queries = [
        q for q in search_queries
        if any(kw in q for kw in ["業界", "トレンド", "動向", "市場"])
    ]

    if not industry_queries:
        industry_queries = [f"{company_info.get('industry', '建設業')} 業界 動向 2024"]

    prompt = f"""あなたは建設業界に詳しいリサーチャーです。
以下の検索クエリに基づき、建設業界の最新動向について知見を提供してください。

【検索クエリ】
{chr(10).join([f"- {q}" for q in industry_queries[:3]])}

【企業情報】
- 業種: {company_info.get('industry', '建設業')}

以下の観点で情報を整理してください：
1. 建設業界全体のトレンド（2024-2025年）
2. {company_info.get('industry', '建設業')}セグメントの特徴
3. 主要な課題と対応策の動向
4. 今後の見通し

具体的な数値や事例を含めて、500字程度で説明してください。
"""

    response = _call_llm_with_log(prompt, "業界動向調査", logs)

    research_results = state.get("research_results", {})
    research_results["industry_trends"] = response

    return {
        "research_results": research_results,
        "prompt_logs": logs,
    }


def search_regional_info(state: WebResearcherState) -> dict[str, Any]:
    """
    地域特性を調査

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    company_info = state.get("company_info", {})
    location = company_info.get('location', '')

    prompt = f"""あなたは地域経済に詳しいリサーチャーです。
{location}における建設業界の状況と地域特性について情報を提供してください。

【対象地域】
{location}

以下の観点で情報を整理してください：
1. {location}の人口動態と経済状況
2. 公共事業・インフラ整備の動向
3. 民間建設需要の特徴
4. 地域特有の課題（災害対策、老朽化対応など）
5. 地方自治体の建設関連施策

具体的な数値や事例を含めて、500字程度で説明してください。
"""

    response = _call_llm_with_log(prompt, "地域情報調査", logs)

    research_results = state.get("research_results", {})
    research_results["regional_info"] = response

    return {
        "research_results": research_results,
        "prompt_logs": logs,
    }


def search_tech_trends(state: WebResearcherState) -> dict[str, Any]:
    """
    GX/DX技術動向を調査

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    company_info = state.get("company_info", {})

    prompt = f"""あなたは建設テクノロジーに詳しいリサーチャーです。
建設業界におけるGX（グリーントランスフォーメーション）とDX（デジタルトランスフォーメーション）の最新動向について情報を提供してください。

【企業業種】
{company_info.get('industry', '建設業')}

以下の観点で情報を整理してください：

【GX（環境対応）】
1. カーボンニュートラル対応の動向
2. 低コスト工法・環境技術の事例
3. 省エネ建築・ZEB/ZEHの動向

【DX（デジタル化）】
1. BIM/CIM活用の現状と事例
2. ICT施工・省力化技術
3. AI/IoT活用の事例
4. 2024年問題への技術的対応

具体的な導入事例や数値を含めて、600字程度で説明してください。
"""

    response = _call_llm_with_log(prompt, "技術動向調査", logs)

    research_results = state.get("research_results", {})
    research_results["tech_trends"] = response

    return {
        "research_results": research_results,
        "prompt_logs": logs,
    }


def summarize_insights(state: WebResearcherState) -> dict[str, Any]:
    """
    調査結果から知見を抽出

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    research_results = state.get("research_results", {})
    company_info = state.get("company_info", {})

    # 調査結果を結合
    all_results = "\n\n".join([
        f"【{key}】\n{value}"
        for key, value in research_results.items()
    ])

    prompt = f"""あなたは経営コンサルタントです。
以下の調査結果から、{company_info.get('industry', '建設業')}企業への提案に活用できる重要な知見を抽出してください。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}

【調査結果】
{all_results}

以下の形式で、提案に活用できる具体的な知見を5〜8個抽出してください。
各知見は1〜2文で簡潔に記述し、具体的な数値や事例を含めてください。

出力形式（JSON）：
[
  "知見1: 具体的な内容",
  "知見2: 具体的な内容",
  ...
]
"""

    response = _call_llm_with_log(prompt, "知見抽出", logs)

    # 知見をパース
    insights = []
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            insights = json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        # パース失敗時は調査結果のサマリーを使用
        insights = [
            f"業界動向: {research_results.get('industry_trends', '')[:100]}...",
            f"地域特性: {research_results.get('regional_info', '')[:100]}...",
            f"技術動向: {research_results.get('tech_trends', '')[:100]}...",
        ]

    return {
        "insights": insights,
        "prompt_logs": logs,
    }


def create_web_researcher() -> StateGraph:
    """
    Web調査エージェントのグラフを構築

    Returns:
        構築されたStateGraph
    """
    graph = StateGraph(WebResearcherState)

    # ノード追加
    graph.add_node("search_industry_trends", search_industry_trends)
    graph.add_node("search_regional_info", search_regional_info)
    graph.add_node("search_tech_trends", search_tech_trends)
    graph.add_node("summarize_insights", summarize_insights)

    # エッジ追加（並列調査→統合）
    graph.add_edge(START, "search_industry_trends")
    graph.add_edge(START, "search_regional_info")
    graph.add_edge(START, "search_tech_trends")
    graph.add_edge("search_industry_trends", "summarize_insights")
    graph.add_edge("search_regional_info", "summarize_insights")
    graph.add_edge("search_tech_trends", "summarize_insights")
    graph.add_edge("summarize_insights", END)

    return graph


def run_web_researcher(
    search_queries: list[str],
    company_info: dict,
) -> dict[str, Any]:
    """
    Web調査エージェントを実行

    Args:
        search_queries: 検索クエリリスト
        company_info: 企業基本情報

    Returns:
        調査結果（research_results, insights, prompt_logs）
    """
    graph = create_web_researcher()
    app = graph.compile()

    initial_state: WebResearcherState = {
        "search_queries": search_queries,
        "company_info": company_info,
        "prompt_logs": [],
    }

    result = app.invoke(initial_state)

    return {
        "research_results": result.get("research_results", {}),
        "insights": result.get("insights", []),
        "prompt_logs": result.get("prompt_logs", []),
    }
