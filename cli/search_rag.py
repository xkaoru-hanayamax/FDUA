"""
RAG検索CLI

使用方法:
    python -m cli.search_rag [企業コード]
    python -m cli.search_rag --all
"""

import argparse
import sys

from src.common import COMPANY_CODES, Config
from src.rag import RAGSummarizer


def main():
    parser = argparse.ArgumentParser(
        description="有価証券報告書をRAGで要約",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python -m cli.search_rag 12044          # 1社のRAG要約
    python -m cli.search_rag --all          # 全10社のRAG要約
    python -m cli.search_rag 12044 --query "経営戦略"  # カスタムクエリ
        """,
    )
    parser.add_argument(
        "company_code",
        nargs="?",
        help="対象の企業コード",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全10社を処理",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="カスタム検索クエリ（指定時はこのクエリのみ実行）",
    )
    parser.add_argument(
        "--data-dir",
        default="/app/data",
        help="データディレクトリ (default: /app/data)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="使用するチャンク数 (default: 10)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="結果をファイルに保存しない",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="インデックスを再作成",
    )

    args = parser.parse_args()

    # 引数チェック
    if not args.all and not args.company_code:
        parser.error("企業コードを指定するか --all オプションを使用してください")

    config = Config(data_dir=args.data_dir)

    codes = COMPANY_CODES if args.all else [args.company_code]

    print("=" * 80)
    print("RAG要約開始")
    print("=" * 80)

    results = {}
    for code in codes:
        print(f"\n{'=' * 60}")
        print(f"有価証券報告書RAG要約 - 企業コード: {code}")
        print(f"{'=' * 60}")

        try:
            summarizer = RAGSummarizer(config=config)

            # インデックス読み込み（必要に応じて再作成）
            summarizer.searcher.load_index(code, force_reindex=args.force_reindex)

            if args.query:
                # カスタムクエリで単一要約
                print(f"\n要約中: {args.query}")
                summary = summarizer.summarize(code, args.query, args.top_k)
                print(f"\n【{args.query}】")
                print("-" * 40)
                print(summary)
                summaries = {args.query: summary}
            else:
                # デフォルトクエリで一括要約
                summaries = summarizer.summarize_all(
                    code,
                    top_k=args.top_k,
                    save_output=not args.no_save,
                )

            results[code] = "成功"

        except FileNotFoundError as e:
            print(f"エラー: {e}")
            results[code] = f"失敗: ファイル未検出"
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
            results[code] = f"失敗: {e}"

    # サマリー
    print("\n" + "=" * 80)
    print("処理結果サマリー")
    print("=" * 80)
    for code, status in results.items():
        print(f"  {code}: {status}")

    success_count = sum(1 for s in results.values() if s == "成功")
    print(f"\n完了: {success_count}/{len(codes)}社")


if __name__ == "__main__":
    main()
