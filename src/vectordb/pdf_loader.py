"""
PDF読み込み・チャンク分割モジュール

PDFファイルの読み込みとテキスト抽出、チャンク分割機能を提供
"""

from pathlib import Path
from typing import Union, Optional

import fitz  # pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..common.constants import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


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


def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[str]:
    """
    テキストをチャンクに分割

    Args:
        text: 入力テキスト
        chunk_size: チャンクサイズ（文字数）
        chunk_overlap: チャンク間のオーバーラップ（文字数）

    Returns:
        チャンクのリスト
    """
    if chunk_size is None:
        chunk_size = DEFAULT_CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = DEFAULT_CHUNK_OVERLAP

    # テキストスプリッター（日本語対応セパレータ）
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "、", " ", ""],
        length_function=len,
    )

    return text_splitter.split_text(text)


def load_and_chunk_pdf(
    pdf_path: Union[str, Path],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[str]:
    """
    PDFを読み込んでチャンクに分割

    Args:
        pdf_path: PDFファイルのパス
        chunk_size: チャンクサイズ（文字数）
        chunk_overlap: チャンク間のオーバーラップ（文字数）

    Returns:
        チャンクのリスト
    """
    print(f"PDFを読み込み中: {pdf_path}")
    text = load_pdf(pdf_path)

    print("チャンク分割中...")
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    print(f"チャンク数: {len(chunks)}")

    return chunks
