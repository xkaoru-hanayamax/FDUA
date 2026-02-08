"""
出力ノード

提案書をDOCX形式で出力する
"""

from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...proposal.docx_writer import DocxWriter
from ...common.config import Config


def write_docx(state: ProposalAgentState) -> dict[str, Any]:
    """
    提案書をDOCX形式で保存

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[write_docx] 提案書をDOCX形式で出力中...")

    company_code = state["company_code"]
    company_info = state.get("company_info", {})
    sections = state.get("sections", {})
    config_dict = state.get("config", {})

    # Configオブジェクトを作成
    if config_dict.get("data_dir"):
        config = Config(data_dir=config_dict["data_dir"])
    else:
        config = Config()

    writer = DocxWriter(config)

    # DOCX出力
    output_path = writer.save_docx(
        company_code=company_code,
        company_info=company_info,
        sections=sections,
    )

    # 文字数カウント
    total_chars = writer.count_characters(
        company_code=company_code,
        company_info=company_info,
        sections=sections,
    )

    print(f"  - 出力先: {output_path}")
    print(f"  - 総文字数: {total_chars}字")

    return {
        "output_path": output_path,
        "total_chars": total_chars,
    }
