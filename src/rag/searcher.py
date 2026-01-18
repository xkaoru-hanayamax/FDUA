"""
RAGベクトル検索モジュール

ベクトル類似度検索機能を提供
"""

from typing import Optional

from langchain_chroma import Chroma

from ..common.config import Config, default_config
from ..vectordb import VectorDBIndexer, SnowflakeCortexEmbeddings


class RAGSearcher:
    """RAGベクトル検索クラス"""

    def __init__(
        self,
        config: Optional[Config] = None,
        indexer: Optional[VectorDBIndexer] = None,
    ):
        """
        Args:
            config: 設定オブジェクト
            indexer: VectorDBIndexerオブジェクト
        """
        self.config = config or default_config
        self.indexer = indexer or VectorDBIndexer(config=self.config)
        self._vectorstores: dict[str, Chroma] = {}

    def load_index(self, company_code: str, force_reindex: bool = False) -> bool:
        """
        企業のインデックスを読み込む

        Args:
            company_code: 企業コード
            force_reindex: Trueの場合、再インデックス化

        Returns:
            読み込み成功時True
        """
        try:
            vectorstore = self.indexer.create_index(
                company_code,
                force_reindex=force_reindex,
            )
            self._vectorstores[company_code] = vectorstore
            return True
        except Exception as e:
            print(f"インデックス読み込みエラー ({company_code}): {e}")
            return False

    def search(
        self,
        company_code: str,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """
        クエリに関連するチャンクをベクトル類似度検索

        Args:
            company_code: 企業コード
            query: 検索クエリ
            top_k: 返却する上位件数

        Returns:
            (チャンク, 類似度スコア)のリスト
        """
        # インデックスが読み込まれていない場合は読み込む
        if company_code not in self._vectorstores:
            if not self.load_index(company_code):
                return []

        vectorstore = self._vectorstores[company_code]

        # ベクトル類似度検索（スコア付き）
        results = vectorstore.similarity_search_with_score(query, k=top_k)

        # (document, score) -> (text, similarity) に変換
        # ChromaDBのスコアは距離なので、類似度に変換（1 / (1 + distance)）
        return [(doc.page_content, 1 / (1 + score)) for doc, score in results]

    def get_chunks(self, company_code: str) -> list[str]:
        """
        企業のチャンクを取得

        Args:
            company_code: 企業コード

        Returns:
            チャンクのリスト
        """
        return self.indexer.get_chunks(company_code)

    def is_loaded(self, company_code: str) -> bool:
        """
        インデックスが読み込まれているか確認

        Args:
            company_code: 企業コード

        Returns:
            読み込み済みの場合True
        """
        return company_code in self._vectorstores
