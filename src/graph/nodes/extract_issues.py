"""
課題抽出ノード

課題抽出エージェントを呼び出して課題を抽出する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ..agents.issue_extractor import run_issue_extractor


def extract_issues(state: ProposalAgentState) -> dict[str, Any]:
    """
    課題抽出エージェントを呼び出す

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[extract_issues] 課題抽出エージェントを実行中...")

    financial_markdown = state.get("financial_markdown", "")
    securities_markdown = state.get("securities_markdown", "")
    company_info = state.get("company_info", {})

    if not financial_markdown or not securities_markdown:
        return {
            "issues": [],
            "issue_categories": {},
            "errors": state.get("errors", []) + ["データが読み込まれていません"],
        }

    result = run_issue_extractor(
        financial_markdown=financial_markdown,
        securities_markdown=securities_markdown,
        company_info=company_info,
    )

    issues = result.get("issues", [])
    issue_categories = result.get("issue_categories", {})
    prompt_logs = result.get("prompt_logs", [])

    print(f"  - 抽出された課題: {len(issues)}件")
    for cat, cat_issues in issue_categories.items():
        print(f"    - {cat}: {len(cat_issues)}件")

    return {
        "issues": issues,
        "issue_categories": issue_categories,
        "prompt_logs": prompt_logs,
    }
