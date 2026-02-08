"""
メインエージェント（ProposalAgent）の状態定義
"""

from typing import TypedDict, Annotated
from operator import add


def merge_lists(left: list, right: list) -> list:
    """リストをマージするリデューサー関数"""
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right


def merge_dicts(left: dict, right: dict) -> dict:
    """辞書をマージするリデューサー関数"""
    if left is None:
        left = {}
    if right is None:
        right = {}
    merged = left.copy()
    merged.update(right)
    return merged


class Issue(TypedDict, total=False):
    """課題データ構造"""
    category: str        # 財務/事業/組織/外部環境
    description: str     # 課題の説明
    severity: str        # high/medium/low
    source: str          # 抽出元（財務/有報）
    evidence: str        # 根拠データ


class ProposalAgentState(TypedDict, total=False):
    """
    メインエージェントの状態

    提案書生成の全フローで共有される状態
    """
    # 入力
    company_code: str
    config: dict

    # データ読み込み結果
    company_info: dict
    financial_markdown: str
    securities_markdown: str

    # 課題抽出の出力
    issues: list[Issue]

    # 情報整理エージェントの出力
    required_info: list[str]
    missing_info: list[str]
    search_queries: list[str]

    # Web調査エージェントの出力
    research_results: dict[str, str]
    insights: list[str]

    # 情報十分性判定
    is_info_sufficient: bool
    sufficiency_check_count: int  # 最大3回まで

    # 提案書セクション
    sections: dict[str, str]
    section_char_counts: dict[str, int]

    # プロンプトログ（累積型）
    prompt_logs: Annotated[list[dict], merge_lists]

    # エラー（累積型）
    errors: Annotated[list[str], merge_lists]

    # 出力
    output_path: str
    total_chars: int
