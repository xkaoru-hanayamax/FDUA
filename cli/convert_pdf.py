"""
PDF→Markdown変換CLI

有価証券報告書PDFをMarkdown形式に変換して保存
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.config import default_config
from src.common.constants import COMPANY_CODES
from src.proposal.pdf_loader import load_pdf_as_markdown


def convert_pdf(company_code: str, config=None) -> Path:
    """
    PDFをMarkdownに変換して保存

    Args:
        company_code: 企業コード
        config: 設定オブジェクト

    Returns:
        保存されたMarkdownファイルのパス
    """
    config = config or default_config

    pdf_path = config.get_pdf_path(company_code)
    md_path = config.get_markdown_path(company_code)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")

    print(f"  変換中: {pdf_path.name} -> {md_path.name}")

    markdown_text = load_pdf_as_markdown(pdf_path)
    md_path.write_text(markdown_text, encoding="utf-8")

    print(f"  完了: {len(markdown_text):,} 文字")

    return md_path


def main():
    parser = argparse.ArgumentParser(
        description="有価証券報告書PDFをMarkdownに変換"
    )
    parser.add_argument(
        "--code",
        type=str,
        help="変換する企業コード（単一）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全企業のPDFを変換",
    )

    args = parser.parse_args()

    if not args.code and not args.all:
        parser.print_help()
        sys.exit(1)

    if args.all:
        codes = COMPANY_CODES
    else:
        codes = [args.code]

    print(f"PDF→Markdown変換開始（{len(codes)}社）")
    print("=" * 50)

    success = 0
    failed = 0

    for code in codes:
        print(f"\n[{code}]")
        try:
            convert_pdf(code)
            success += 1
        except Exception as e:
            print(f"  エラー: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"完了: 成功 {success} / 失敗 {failed}")


if __name__ == "__main__":
    main()
