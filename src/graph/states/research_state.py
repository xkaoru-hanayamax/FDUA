"""
Web調査エージェント（WebResearcher）の状態定義
"""

from typing import TypedDict


class WebResearcherState(TypedDict, total=False):
    """
    Web調査エージェントの状態

    不足情報をWeb検索で補完する
    """
    # 入力
    search_queries: list[str]
    company_info: dict  # 地域・業種等のコンテキスト

    # 中間結果
    raw_search_results: dict[str, list[dict]]  # クエリ別の生検索結果

    # 出力
    research_results: dict[str, str]  # クエリ別調査結果（要約済み）
    insights: list[str]               # 得られた知見

    # プロンプトログ
    prompt_logs: list[dict]
