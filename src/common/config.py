"""
設定管理モジュール

パス設定、環境設定などを管理
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """設定管理クラス"""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: データディレクトリのパス（Noneの場合は環境変数またはデフォルト）
        """
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            # 環境変数 > デフォルト(/app/data)
            self._data_dir = Path(os.getenv("FDUA_DATA_DIR", "/app/data"))

    @property
    def data_dir(self) -> Path:
        """データディレクトリ"""
        return self._data_dir

    @property
    def financial_csv_path(self) -> Path:
        """財務データCSVパス"""
        return self._data_dir / "financial_data.csv"

    @property
    def chroma_db_path(self) -> Path:
        """ChromaDB永続化ディレクトリ"""
        return self._data_dir / "chroma_db"

    @property
    def output_dir(self) -> Path:
        """分析結果出力ディレクトリ"""
        path = self._data_dir / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def proposals_dir(self) -> Path:
        """提案書出力ディレクトリ"""
        path = self._data_dir / "proposals"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_pdf_path(self, company_code: str) -> Path:
        """
        企業コードから有価証券報告書PDFパスを取得

        Args:
            company_code: 企業コード

        Returns:
            PDFファイルパス
        """
        return self._data_dir / f"有価証券報告書（{company_code}）.pdf"

    def get_rag_summary_path(self, company_code: str) -> Path:
        """
        企業コードからRAG要約ファイルパスを取得

        Args:
            company_code: 企業コード

        Returns:
            要約ファイルパス
        """
        return self._data_dir / f"有価証券報告書要約（{company_code}）.txt"

    def get_financial_summary_path(self, company_code: str) -> Path:
        """
        企業コードから財務分析サマリーファイルパスを取得

        Args:
            company_code: 企業コード

        Returns:
            サマリーファイルパス
        """
        return self.output_dir / f"{company_code}_summary.txt"

    def get_proposal_path(self, company_code: str) -> Path:
        """
        企業コードから提案書ファイルパスを取得

        Args:
            company_code: 企業コード

        Returns:
            提案書ファイルパス
        """
        return self.proposals_dir / f"{company_code}.docx"

    def get_prompt_log_path(self) -> Path:
        """
        プロンプトログファイルパスを取得

        Returns:
            プロンプトログファイルパス
        """
        return self._data_dir / "prompt_log.txt"


# デフォルトのConfig インスタンス
default_config = Config()
