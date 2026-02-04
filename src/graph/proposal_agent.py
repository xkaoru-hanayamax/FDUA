"""
提案書生成メインエージェント

LangGraphベースのオーケストレーターエージェント
"""

from typing import Any, Optional

from langgraph.graph import StateGraph, START, END

from .states.proposal_state import ProposalAgentState
from .nodes import (
    load_data,
    extract_issues,
    generate_overview,
    generate_issues,
    generate_strategy,
    generate_effects,
    generate_roadmap,
    check_and_truncate,
    write_docx,
)


def create_proposal_agent() -> StateGraph:
    """
    提案書生成エージェントのグラフを構築

    フロー:
    START → load_data → extract_issues → generate_overview → generate_issues
                                                                    │
                                                                    ▼
                                                          generate_strategy
                                                                    │
                                                                    ▼
                                                           generate_effects
                                                                    │
                                                                    ▼
                                                           generate_roadmap
                                                                    │
                                                                    ▼
                                                        check_and_truncate
                                                                    │
                                                                    ▼
                                                              write_docx
                                                                    │
                                                                    ▼
                                                                   END

    Returns:
        構築されたStateGraph
    """
    graph = StateGraph(ProposalAgentState)

    # ノード追加
    graph.add_node("load_data", load_data)
    graph.add_node("extract_issues", extract_issues)
    graph.add_node("generate_overview", generate_overview)
    graph.add_node("generate_issues", generate_issues)
    graph.add_node("generate_strategy", generate_strategy)
    graph.add_node("generate_effects", generate_effects)
    graph.add_node("generate_roadmap", generate_roadmap)
    graph.add_node("check_and_truncate", check_and_truncate)
    graph.add_node("write_docx", write_docx)

    # エッジ追加（直線フロー）
    graph.add_edge(START, "load_data")
    graph.add_edge("load_data", "extract_issues")
    graph.add_edge("extract_issues", "generate_overview")
    graph.add_edge("generate_overview", "generate_issues")
    graph.add_edge("generate_issues", "generate_strategy")
    graph.add_edge("generate_strategy", "generate_effects")
    graph.add_edge("generate_effects", "generate_roadmap")
    graph.add_edge("generate_roadmap", "check_and_truncate")
    graph.add_edge("check_and_truncate", "write_docx")
    graph.add_edge("write_docx", END)

    return graph


def run_proposal_agent(
    company_code: str,
    data_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    提案書生成エージェントを実行

    Args:
        company_code: 企業コード
        data_dir: データディレクトリ（Noneの場合はデフォルト）

    Returns:
        実行結果
        {
            "company_code": 企業コード,
            "company_info": 企業情報,
            "sections": 生成されたセクション,
            "section_char_counts": セクション別文字数,
            "issues": 抽出された課題,
            "prompt_logs": プロンプトログ,
            "output_path": 出力ファイルパス,
            "total_chars": 総文字数,
            "errors": エラーリスト,
        }
    """
    print(f"\n{'='*60}")
    print(f"提案書生成エージェント開始: 企業コード {company_code}")
    print(f"{'='*60}\n")

    graph = create_proposal_agent()
    app = graph.compile()

    # 初期状態
    initial_state: ProposalAgentState = {
        "company_code": company_code,
        "config": {"data_dir": data_dir} if data_dir else {},
        "issues": [],
        "issue_categories": {},
        "required_info": [],
        "missing_info": [],
        "search_queries": [],
        "research_results": {},
        "insights": [],
        "is_info_sufficient": True,  # Web調査を削除したため常にTrue
        "sufficiency_check_count": 0,
        "sections": {},
        "section_char_counts": {},
        "prompt_logs": [],
        "errors": [],
    }

    # グラフ実行
    result = app.invoke(initial_state)

    print(f"\n{'='*60}")
    print("提案書生成エージェント完了")
    print(f"{'='*60}\n")

    return {
        "company_code": result.get("company_code"),
        "company_info": result.get("company_info", {}),
        "sections": result.get("sections", {}),
        "section_char_counts": result.get("section_char_counts", {}),
        "issues": result.get("issues", []),
        "prompt_logs": result.get("prompt_logs", []),
        "output_path": result.get("output_path"),
        "total_chars": result.get("total_chars"),
        "errors": result.get("errors", []),
    }
