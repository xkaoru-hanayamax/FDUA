"""
課題抽出エージェント（IssueExtractor）の状態定義
"""

from typing import TypedDict, Annotated
from .proposal_state import Issue, merge_lists


class IssueExtractorState(TypedDict, total=False):
    """
    課題抽出エージェントの状態

    財務データと有価証券報告書から課題を抽出する
    """
    # 入力
    financial_markdown: str
    securities_markdown: str
    company_info: dict

    # 中間結果（並列実行で別々に更新される）
    financial_issues: list[Issue]
    securities_issues: list[Issue]

    # 出力
    integrated_issues: list[Issue]
    issue_categories: dict[str, list[Issue]]

    # プロンプトログ（累積型：並列ノードからマージ）
    prompt_logs: Annotated[list[dict], merge_lists]
