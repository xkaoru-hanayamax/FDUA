"""
Web調査ノード

Web調査エージェントを呼び出して課題駆動型の調査を実施する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ..agents.web_researcher import run_web_researcher


def web_research(state: ProposalAgentState) -> dict[str, Any]:
    """
    Web調査エージェントを呼び出す（課題駆動型）

    課題抽出エージェントで抽出された課題を元に、
    各課題に対する対策案と裏付け情報を収集する

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[web_research] 課題駆動型Web調査エージェントを実行中...")

    issues = state.get("issues", [])
    company_info = state.get("company_info", {})

    if not issues:
        print("  - 警告: 課題リストが空です。Web調査をスキップします。")
        return {
            "research_results": {},
            "insights": [],
            "prompt_logs": [],
        }

    print(f"  - 入力課題数: {len(issues)}件")

    result = run_web_researcher(
        issues=issues,
        company_info=company_info,
    )

    solutions = result.get("solutions", [])
    research_results = result.get("research_results", {})
    insights = result.get("insights", [])
    prompt_logs = result.get("prompt_logs", [])

    print(f"  - 生成した対策案: {len(solutions)}件")
    print(f"  - 調査結果: {len(research_results)}カテゴリ")
    print(f"  - 抽出した知見: {len(insights)}件")

    return {
        "research_results": research_results,
        "insights": insights,
        "prompt_logs": prompt_logs,
    }
