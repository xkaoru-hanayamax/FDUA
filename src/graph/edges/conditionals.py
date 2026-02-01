"""
条件分岐関数

グラフのエッジで使用する条件分岐ロジック
"""

from typing import Literal

from ..states.proposal_state import ProposalAgentState


def should_research(state: ProposalAgentState) -> Literal["web_research", "generate_overview"]:
    """
    Web調査が必要かどうかを判定

    Args:
        state: 現在の状態

    Returns:
        "web_research": 調査が必要
        "generate_overview": 調査不要、セクション生成へ
    """
    is_sufficient = state.get("is_info_sufficient", False)

    if is_sufficient:
        return "generate_overview"
    else:
        return "web_research"


def should_regenerate(state: ProposalAgentState) -> Literal["organize_info", "write_docx"]:
    """
    再生成が必要かどうかを判定

    文字数超過等で情報不足と判断された場合は再調査

    Args:
        state: 現在の状態

    Returns:
        "organize_info": 再調査が必要
        "write_docx": 出力へ
    """
    is_sufficient = state.get("is_info_sufficient", True)
    check_count = state.get("sufficiency_check_count", 0)

    # 最大3回までチェック
    if check_count >= 3:
        return "write_docx"

    if is_sufficient:
        return "write_docx"
    else:
        return "organize_info"
