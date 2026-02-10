"""
web_research ノード単体テスト CLI

load_data → web_research までを実行し、
検索クエリ・取得結果・整形後マークダウンを全てファイルに出力する。

使い方:
  python -m cli.test_web_research --code 12044
  python -m cli.test_web_research --code 12044 --data-dir /app/data
  python -m cli.test_web_research --code 12044 --output /tmp/result.txt

出力先:
  デフォルト: data/output/{企業コード}_web_research.txt
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.graph.nodes.load_data import load_data
from src.graph.nodes.web_research import web_research
from src.graph.states.proposal_state import ProposalAgentState
from src.common.constants import COMPANY_CODES
from src.common.config import Config


def _write_report(
    out: Path,
    company_code: str,
    company_info: dict,
    research_result: dict,
) -> None:
    """結果を全てファイルに書き出す。"""

    queries = research_result.get("search_queries", [])
    insights = research_result.get("insights", [])
    research_results = research_result.get("research_results", {})
    prompt_logs = research_result.get("prompt_logs", [])
    is_sufficient = research_result.get("is_info_sufficient")
    total_chars = sum(len(v) for v in research_results.values())

    lines: list[str] = []

    def section(title: str) -> None:
        lines.append("")
        lines.append("=" * 70)
        lines.append(title)
        lines.append("=" * 70)

    # ---- ヘッダー ----
    lines.append("web_research テスト結果")
    lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"企業コード: {company_code}")

    # ---- 企業情報 ----
    section("企業情報")
    for k, v in company_info.items():
        lines.append(f"  {k}: {v}")

    # ---- LLMが生成したクエリ ----
    query_gen_logs = [l for l in prompt_logs if l.get("step") == "web_research_query_generation"]
    if query_gen_logs:
        section("LLMクエリ生成")
        log = query_gen_logs[0]
        lines.append(f"  プロンプト長: {len(log.get('prompt', ''))}文字")
        lines.append(f"  レスポンス長: {len(log.get('response', ''))}文字")
        lines.append("")
        lines.append("  --- LLMレスポンス ---")
        lines.append(log.get("response", "（なし）"))

    # ---- 検索クエリ ----
    section(f"検索クエリ ({len(queries)}件)")
    for i, q in enumerate(queries, 1):
        lines.append(f"  {i}. {q}")

    # ---- insights ----
    section(f"insights ({len(insights)}件)")
    for i, ins in enumerate(insights, 1):
        lines.append(f"  {i}. {ins}")

    # ---- 情報十分性 ----
    section("is_info_sufficient")
    lines.append(f"  {is_sufficient}")

    # ---- research_results（カテゴリ別・全文） ----
    section(f"research_results ({len(research_results)}カテゴリ / 合計 {total_chars}文字)")
    for category, content in research_results.items():
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"[{category}] ({len(content)}文字)")
        lines.append("-" * 70)
        lines.append(content)

    # ---- _build_context() 相当のセクション（全文） ----
    section("_build_context() に含まれる調査結果セクション（全文）")
    if research_results:
        research_text = "\n\n".join([
            f"## {key}\n{value}"
            for key, value in research_results.items()
        ])
        context_section = f"# 調査結果\n\n{research_text}"
        lines.append(context_section)
    else:
        lines.append("（調査結果なし）")

    # ---- 書き込み ----
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="web_research ノードの出力を確認するテストスクリプト"
    )
    parser.add_argument(
        "--code",
        type=str,
        required=True,
        help="企業コード（例: 12044）",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="データディレクトリパス",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="出力ファイルパス（デフォルト: data/output/{code}_web_research.txt）",
    )
    args = parser.parse_args()

    company_code = args.code
    if company_code not in COMPANY_CODES:
        print(f"WARNING: {company_code} は定義済み企業コード一覧に含まれていません")

    config = Config(data_dir=args.data_dir) if args.data_dir else Config()

    # 出力先
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = config.output_dir / f"{company_code}_web_research.txt"

    # ---- 初期状態 ----
    state: ProposalAgentState = {
        "company_code": company_code,
        "config": {"data_dir": args.data_dir} if args.data_dir else {},
        "issues": [],
        "required_info": [],
        "missing_info": [],
        "search_queries": [],
        "research_results": {},
        "insights": [],
        "is_info_sufficient": False,
        "sufficiency_check_count": 0,
        "sections": {},
        "section_char_counts": {},
        "prompt_logs": [],
        "errors": [],
    }

    # ---- Step 1: load_data ----
    print(f"[1/2] load_data (企業コード: {company_code}) ...")

    load_result = load_data(state)

    if load_result.get("errors"):
        print(f"ERROR: {load_result['errors']}")
        sys.exit(1)

    state.update(load_result)

    company_info = state.get("company_info", {})
    print(f"  企業情報: {company_info}")

    # ---- Step 2: web_research ----
    print(f"[2/2] web_research ...")

    research_result = web_research(state)

    # ---- レポート出力 ----
    _write_report(output_path, company_code, company_info, research_result)

    # ---- マークダウンファイルパス ----
    md_path = config.output_dir / f"{company_code}_web_research.md"

    total_chars = sum(len(v) for v in research_result.get("research_results", {}).values())
    print()
    print(f"完了:")
    print(f"  レポート: {output_path}")
    print(f"  マークダウン: {md_path}")
    print(f"  カテゴリ数: {len(research_result.get('research_results', {}))}")
    print(f"  合計文字数: {total_chars}")


if __name__ == "__main__":
    main()
