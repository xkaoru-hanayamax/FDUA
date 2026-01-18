"""
ChromaDBインデックス管理モジュール

ベクトルDBへのインデックス作成・管理機能を提供
"""

from pathlib import Path
from typing import Optional, Union

from langchain_chroma import Chroma

from ..common.config import Config, default_config
from .embeddings import SnowflakeCortexEmbeddings
from .pdf_loader import load_and_chunk_pdf


class VectorDBIndexer:
    """ベクトルDBインデックス管理クラス"""

    def __init__(
        self,
        config: Optional[Config] = None,
        embeddings: Optional[SnowflakeCortexEmbeddings] = None,
    ):
        """
        Args:
            config: 設定オブジェクト
            embeddings: Embeddingsオブジェクト
        """
        self.config = config or default_config
        self.embeddings = embeddings or SnowflakeCortexEmbeddings()

    @property
    def persist_directory(self) -> str:
        """ChromaDB永続化ディレクトリ"""
        return str(self.config.chroma_db_path)

    def _get_collection_name(self, company_code: str) -> str:
        """企業コードからコレクション名を生成"""
        return f"securities_report_{company_code}"

    def check_existing_index(self, company_code: str) -> bool:
        """
        既存のインデックスが存在するか確認

        Args:
            company_code: 企業コード

        Returns:
            インデックスが存在する場合True
        """
        collection_name = self._get_collection_name(company_code)
        try:
            vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
            # コレクションにドキュメントがあるか確認
            count = vectorstore._collection.count()
            return count > 0
        except Exception:
            return False

    def delete_index(self, company_code: str) -> bool:
        """
        既存インデックスを削除

        Args:
            company_code: 企業コード

        Returns:
            削除成功時True
        """
        collection_name = self._get_collection_name(company_code)
        try:
            import chromadb
            client = chromadb.PersistentClient(path=self.persist_directory)
            client.delete_collection(collection_name)
            print(f"既存コレクションを削除しました: {collection_name}")
            return True
        except Exception:
            return False

    def load_existing_index(self, company_code: str) -> Optional[Chroma]:
        """
        既存インデックスを読み込む

        Args:
            company_code: 企業コード

        Returns:
            Chromaベクトルストア（存在しない場合None）
        """
        if not self.check_existing_index(company_code):
            return None

        collection_name = self._get_collection_name(company_code)
        print(f"既存のインデックスを使用します: {collection_name}")

        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

    def create_index(
        self,
        company_code: str,
        pdf_path: Optional[Union[str, Path]] = None,
        force_reindex: bool = False,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Chroma:
        """
        PDFからインデックスを作成

        Args:
            company_code: 企業コード
            pdf_path: PDFファイルパス（Noneの場合はデフォルトパス）
            force_reindex: Trueの場合、既存インデックスを削除して再作成
            chunk_size: チャンクサイズ
            chunk_overlap: チャンクオーバーラップ

        Returns:
            Chromaベクトルストア
        """
        collection_name = self._get_collection_name(company_code)

        # 既存インデックスの確認
        if not force_reindex:
            existing = self.load_existing_index(company_code)
            if existing is not None:
                return existing

        # PDFパス取得
        if pdf_path is None:
            pdf_path = self.config.get_pdf_path(company_code)

        # PDF読み込み・チャンク分割
        chunks = load_and_chunk_pdf(pdf_path, chunk_size, chunk_overlap)

        # 既存コレクションを削除（force_reindexの場合）
        if force_reindex:
            self.delete_index(company_code)

        # メタデータを付与
        metadatas = [
            {"company_code": company_code, "chunk_index": i}
            for i in range(len(chunks))
        ]

        # ChromaDBにベクトルストアを作成
        print("Embeddingを生成してChromaDBにインデックス化中...")
        vectorstore = Chroma.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=metadatas,
            collection_name=collection_name,
            persist_directory=self.persist_directory,
        )

        print(f"インデックス化完了: {collection_name}")
        return vectorstore

    def get_chunks(self, company_code: str) -> list[str]:
        """
        インデックスからチャンクを取得

        Args:
            company_code: 企業コード

        Returns:
            チャンクのリスト
        """
        vectorstore = self.load_existing_index(company_code)
        if vectorstore is None:
            return []

        results = vectorstore._collection.get()
        return results.get("documents", [])
