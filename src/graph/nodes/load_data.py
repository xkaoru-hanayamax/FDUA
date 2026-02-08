"""
データ読み込みノード

財務データと有価証券報告書のMarkdownを読み込む
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...proposal.context_builder import ContextBuilder
from ...common.config import Config
from ...common.debug import debug_log, debug_log_io


def load_data(state: ProposalAgentState) -> dict[str, Any]:
    """
    財務データと有価証券報告書を読み込む

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    company_code = state["company_code"]
    config_dict = state.get("config", {})

    print(f"[load_data] 企業コード {company_code} のデータを読み込み中...")

    # Configオブジェクトを作成
    if config_dict.get("data_dir"):
        config = Config(data_dir=config_dict["data_dir"])
    else:
        config = Config()

    # ContextBuilderを使用してデータ読み込み
    context_builder = ContextBuilder(config)

    try:
        context_builder.load_all(company_code)
    except FileNotFoundError as e:
        return {
            "errors": [str(e)],
        }

    company_info = context_builder.get_company_info() or {}
    financial_markdown = context_builder.get_financial_markdown() or ""
    securities_markdown = context_builder.get_securities_report_markdown() or ""

    print(f"  - 財務Markdown: {len(financial_markdown)}文字")
    print(f"  - 有報Markdown: {len(securities_markdown)}文字")
    print(f"  - 企業情報: {company_info}")

    # デバッグログ出力
    debug_log(
        "load_data",
        f"企業コード {company_code} のデータ読み込み完了",
        f"企業情報:\n{company_info}\n\n財務Markdown（先頭1000文字）:\n{financial_markdown[:1000]}\n\n有報Markdown（先頭1000文字）:\n{securities_markdown[:1000]}"
    )

    return {
        "company_info": company_info,
        "financial_markdown": financial_markdown,
        "securities_markdown": securities_markdown,
        "errors": [],
    }
