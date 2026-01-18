"""
ベクトルDB構築CLI

使用方法:
    python -m cli.build_vectordb [企業コード]
    python -m cli.build_vectordb --all
    python -m cli.build_vectordb --all --force
"""

import argparse
import sys

from src.common import COMPANY_CODES, Config
from src.vectordb import VectorDBIndexer


def main():
    parser = argparse.ArgumentParser(
        description="有価証券報告書のベクトルDBを構築",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python -m cli.build_vectordb 12044          # 1社のインデックス作成
    python -m cli.build_vectordb --all          # 全10社のインデックス作成
    python -m cli.build_vectordb --all --force  # 既存インデックスを再作成
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
        "--force",
        action="store_true",
        help="既存インデックスを削除して再作成",
    )
    parser.add_argument(
        "--data-dir",
        default="/app/data",
        help="データディレクトリ (default: /app/data)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="チャンクサイズ (default: 500)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=100,
        help="チャンクオーバーラップ (default: 100)",
    )

    args = parser.parse_args()

    # 引数チェック
    if not args.all and not args.company_code:
        parser.error("企業コードを指定するか --all オプションを使用してください")

    config = Config(data_dir=args.data_dir)
    indexer = VectorDBIndexer(config=config)

    codes = COMPANY_CODES if args.all else [args.company_code]

    print("=" * 80)
    print("ベクトルDB構築開始")
    print("=" * 80)

    results = {}
    for code in codes:
        print(f"\n{'=' * 60}")
        print(f"企業コード: {code}")
        print(f"{'=' * 60}")

        try:
            # PDFパス確認
            pdf_path = config.get_pdf_path(code)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDFが見つかりません: {pdf_path}")

            # インデックス作成
            vectorstore = indexer.create_index(
                company_code=code,
                pdf_path=pdf_path,
                force_reindex=args.force,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )

            # チャンク数を表示
            chunks = indexer.get_chunks(code)
            print(f"インデックス化完了: {len(chunks)} チャンク")
            results[code] = "成功"

        except FileNotFoundError as e:
            print(f"エラー: {e}")
            results[code] = f"失敗: ファイル未検出"
        except Exception as e:
            print(f"エラー: {e}")
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
