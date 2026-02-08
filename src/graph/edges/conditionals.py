"""
条件分岐関数

グラフのエッジで使用する条件分岐ロジック
（Web調査削除後は現在使用されていないが、将来の拡張用に残置）
"""

from typing import Literal

from ..states.proposal_state import ProposalAgentState


def should_regenerate(state: ProposalAgentState) -> Literal["write_docx"]:
    """
    再生成が必要かどうかを判定

    Web調査機能削除後は常にwrite_docxへ遷移

    Args:
        state: 現在の状態

    Returns:
        "write_docx": 出力へ
    """
    return "write_docx"
