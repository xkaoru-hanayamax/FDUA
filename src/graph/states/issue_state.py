"""
課題抽出エージェント（IssueExtractor）の状態定義
"""

from typing import TypedDict
from .proposal_state import Issue


class IssueExtractorState(TypedDict, total=False):
    """
    課題抽出エージェントの状態

    財務データと有価証券報告書から課題を抽出する
    """
    # 入力
    financial_markdown: str
    securities_markdown: str
    company_info: dict

    # 中間結果
    financial_issues: list[Issue]
    securities_issues: list[Issue]

    # 出力
    integrated_issues: list[Issue]
    issue_categories: dict[str, list[Issue]]

    # プロンプトログ
    prompt_logs: list[dict]
