"""
情報整理ノード

情報整理エージェントを呼び出して必要情報を整理する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ..agents.info_organizer import run_info_organizer


def organize_info(state: ProposalAgentState) -> dict[str, Any]:
    """
    情報整理エージェントを呼び出す

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[organize_info] 情報整理エージェントを実行中...")

    issues = state.get("issues", [])
    company_info = state.get("company_info", {})

    if not issues:
        return {
            "required_info": [],
            "missing_info": [],
            "search_queries": [],
            "errors": state.get("errors", []) + ["課題が抽出されていません"],
        }

    # 現在利用可能な情報を整理
    available_info = {
        "財務データ": state.get("financial_markdown", "")[:500],
        "有価証券報告書": state.get("securities_markdown", "")[:500],
        "企業基本情報": str(company_info),
    }

    # 既に調査結果がある場合は追加
    if state.get("research_results"):
        for key, value in state["research_results"].items():
            available_info[f"調査結果_{key}"] = value[:300]

    result = run_info_organizer(
        issues=issues,
        company_info=company_info,
        available_info=available_info,
    )

    required_info = result.get("required_info", [])
    missing_info = result.get("missing_info", [])
    search_queries = result.get("search_queries", [])
    prompt_logs = result.get("prompt_logs", [])

    print(f"  - 必要な情報: {len(required_info)}件")
    print(f"  - 不足情報: {len(missing_info)}件")
    print(f"  - 検索クエリ: {len(search_queries)}件")

    return {
        "required_info": required_info,
        "missing_info": missing_info,
        "search_queries": search_queries,
        "prompt_logs": prompt_logs,
    }
