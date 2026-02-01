"""
Web調査ノード

Web調査エージェントを呼び出して不足情報を補完する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ..agents.web_researcher import run_web_researcher


def web_research(state: ProposalAgentState) -> dict[str, Any]:
    """
    Web調査エージェントを呼び出す

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[web_research] Web調査エージェントを実行中...")

    search_queries = state.get("search_queries", [])
    company_info = state.get("company_info", {})

    if not search_queries:
        # デフォルトクエリを生成
        location = company_info.get("location", "")
        industry = company_info.get("industry", "建設業")
        search_queries = [
            f"{location} 建設業 市場動向 2024",
            f"{industry} 業界 課題 トレンド",
            "建設業 DX 省力化 事例",
            "建設業 GX カーボンニュートラル",
        ]

    result = run_web_researcher(
        search_queries=search_queries,
        company_info=company_info,
    )

    research_results = result.get("research_results", {})
    insights = result.get("insights", [])
    prompt_logs = result.get("prompt_logs", [])

    print(f"  - 調査結果: {len(research_results)}カテゴリ")
    print(f"  - 抽出した知見: {len(insights)}件")

    return {
        "research_results": research_results,
        "insights": insights,
        "prompt_logs": prompt_logs,
    }
