"""
Web調査エージェント（WebResearcher）の状態定義

課題駆動型Web調査: 課題ごとに対策案を生成し、裏付け情報を収集する
"""

from typing import TypedDict, Annotated
from .proposal_state import Issue, merge_lists, merge_dicts


class SolutionItem(TypedDict, total=False):
    """課題→対策→調査結果を紐づける構造"""
    issue: Issue              # 元の課題
    solution: str             # 対策案
    search_query: str         # 検索クエリ
    evidence: str             # 調査結果（裏付け情報）


class WebResearcherState(TypedDict, total=False):
    """
    Web調査エージェントの状態

    課題駆動型: 課題ごとに対策案を生成し、裏付け情報を収集する
    """
    # 入力
    issues: list[Issue]           # 課題リスト（課題抽出エージェントから）
    company_info: dict            # 地域・業種等のコンテキスト

    # 中間・出力
    solutions: Annotated[list[SolutionItem], merge_lists]  # 課題→対策→調査結果
    insights: list[str]           # 統合された知見

    # 旧形式との互換性のため残す
    research_results: Annotated[dict[str, str], merge_dicts]

    # プロンプトログ（累積型）
    prompt_logs: Annotated[list[dict], merge_lists]
