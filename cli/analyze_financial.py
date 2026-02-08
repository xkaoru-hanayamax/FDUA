"""
財務分析CLI

使用方法:
    python -m cli.analyze_financial [企業コード]
    python -m cli.analyze_financial --all
"""

import argparse
import sys

from src.common import COMPANY_CODES, Config
from src.financial import FinancialAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="企業の財務分析を実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python -m cli.analyze_financial 12044          # 1社分析
    python -m cli.analyze_financial --all          # 全10社分析
    python -m cli.analyze_financial --data-dir ./data  # データディレクトリ指定
        """,
    )
    parser.add_argument(
        "company_code",
        nargs="?",
        help="分析対象の企業コード",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全10社を分析",
    )
    parser.add_argument(
        "--data-dir",
        default="/app/data",
        help="データディレクトリ (default: /app/data)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="結果をファイルに保存しない",
    )

    args = parser.parse_args()

    # 引数チェック
    if not args.all and not args.company_code:
        parser.error("企業コードを指定するか --all オプションを使用してください")

    config = Config(data_dir=args.data_dir)
    analyzer = FinancialAnalyzer(config=config)

    if args.all:
        # 全社分析
        print("=" * 80)
        print("全社財務分析開始")
        print("=" * 80)

        results = {}
        for code in COMPANY_CODES:
            try:
                result = analyzer.analyze(code, save_output=not args.no_save)
                results[code] = "成功"
                print(f"\n=== 企業コード {code} 分析結果 ===")
                print(result["summary"])
            except Exception as e:
                results[code] = f"失敗: {e}"
                print(f"エラー（企業コード {code}）: {e}")

        print("\n" + "=" * 80)
        print("処理結果サマリー")
        print("=" * 80)
        for code, status in results.items():
            print(f"  {code}: {status}")

        success_count = sum(1 for s in results.values() if s == "成功")
        print(f"\n完了: {success_count}/{len(COMPANY_CODES)}社")

    else:
        # 1社分析
        try:
            result = analyzer.analyze(args.company_code, save_output=not args.no_save)
            print("\n=== 分析結果 ===")
            print(result["summary"])
        except Exception as e:
            print(f"エラー: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
