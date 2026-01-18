"""
提案書生成CLI

使用方法:
    python -m cli.generate_proposal [企業コード]
    python -m cli.generate_proposal --all
"""

import argparse
import sys

from src.common import COMPANY_CODES, Config
from src.proposal import ContextBuilder, SectionGenerator, DocxWriter


def process_company(company_code: str, config: Config) -> bool:
    """
    1社の提案書を生成

    Args:
        company_code: 企業コード
        config: 設定オブジェクト

    Returns:
        成功時True
    """
    print(f"\n{'=' * 60}")
    print(f"提案書生成開始 - 企業コード: {company_code}")
    print(f"{'=' * 60}")

    # コンテキスト構築
    print("\n[1/7] データを読み込み中...")
    context_builder = ContextBuilder(config=config)

    print("  財務データを読み込み中...")
    context_builder.load_financial_data(company_code)

    print("  RAG要約を読み込み中...")
    context_builder.load_rag_summaries(company_code)

    # セクション生成
    print("\n[2/7] 各セクションを生成中...")
    section_generator = SectionGenerator(context_builder)
    sections = section_generator.generate_all()

    # DOCX出力
    print("\n[7/7] DOCXを出力中...")
    docx_writer = DocxWriter(config=config)

    company_info = context_builder.get_company_info() or {}

    # 文字数チェック
    char_count = docx_writer.count_characters(company_code, company_info, sections)
    print(f"\n提案書文字数: {char_count:,}字")
    if char_count > 15000:
        print(f"警告: 文字数が15,000字を超えています（{char_count}字）")

    # 保存
    docx_path = docx_writer.save_docx(company_code, company_info, sections)

    print(f"\n生成完了: {docx_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="提案書を生成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python -m cli.generate_proposal 12044      # 1社の提案書生成
    python -m cli.generate_proposal --all      # 全10社の提案書生成
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
        "--data-dir",
        default="/app/data",
        help="データディレクトリ (default: /app/data)",
    )

    args = parser.parse_args()

    # 引数チェック
    if not args.all and not args.company_code:
        parser.error("企業コードを指定するか --all オプションを使用してください")

    config = Config(data_dir=args.data_dir)

    codes = COMPANY_CODES if args.all else [args.company_code]

    print("=" * 80)
    print("提案書生成開始")
    print("=" * 80)

    results = {}
    for code in codes:
        try:
            success = process_company(code, config)
            results[code] = "成功" if success else "失敗"
        except Exception as e:
            print(f"エラー（企業コード {code}）: {e}")
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
