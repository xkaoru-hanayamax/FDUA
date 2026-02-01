"""
PDF読み込みモジュール

PDFファイルの読み込みとテキスト抽出機能を提供
"""

from pathlib import Path
from typing import Union

import fitz  # pymupdf


def load_pdf(pdf_path: Union[str, Path]) -> str:
    """
    PDFファイルからテキストを抽出

    Args:
        pdf_path: PDFファイルのパス

    Returns:
        抽出されたテキスト（空白・改行正規化済み）
    """
    doc = fitz.open(str(pdf_path))
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    # 空白・改行の正規化
    full_text = " ".join(full_text.split())
    return full_text
