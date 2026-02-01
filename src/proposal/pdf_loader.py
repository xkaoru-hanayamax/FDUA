"""
PDF読み込みモジュール

PDFファイルの読み込みとMarkdown変換機能を提供
doclingを使用してPDFを構造化されたMarkdownに変換
"""

from pathlib import Path
from typing import Union

from docling.document_converter import DocumentConverter


# DocumentConverterのシングルトンインスタンス（初期化コストを削減）
_converter: DocumentConverter = None


def _get_converter() -> DocumentConverter:
    """DocumentConverterのシングルトンインスタンスを取得"""
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def load_pdf(pdf_path: Union[str, Path]) -> str:
    """
    PDFファイルからテキストを抽出（後方互換性のため維持）

    Args:
        pdf_path: PDFファイルのパス

    Returns:
        抽出されたMarkdownテキスト
    """
    return load_pdf_as_markdown(pdf_path)


def load_pdf_as_markdown(pdf_path: Union[str, Path]) -> str:
    """
    PDFファイルをMarkdown形式に変換

    doclingを使用してPDFを解析し、構造を保持したMarkdownを生成

    Args:
        pdf_path: PDFファイルのパス

    Returns:
        変換されたMarkdownテキスト
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")

    converter = _get_converter()
    result = converter.convert(str(pdf_path))

    # Markdownとしてエクスポート
    markdown_text = result.document.export_to_markdown()

    # 「架空・サンプルデータ」を削除
    markdown_text = markdown_text.replace("架空・サンプルデータ", "")

    return markdown_text
