"""
情報整理エージェント（InfoOrganizer）の状態定義
"""

from typing import TypedDict, Annotated
from .proposal_state import Issue, merge_lists


class InfoOrganizerState(TypedDict, total=False):
    """
    情報整理エージェントの状態

    課題解決に必要な情報を整理し、不足を特定する
    """
    # 入力
    issues: list[Issue]
    company_info: dict
    available_info: dict  # 現在持っている情報

    # 出力
    required_info: list[str]    # 必要な情報リスト
    missing_info: list[str]     # 不足している情報
    search_queries: list[str]   # Web検索用クエリ

    # プロンプトログ（累積型）
    prompt_logs: Annotated[list[dict], merge_lists]
