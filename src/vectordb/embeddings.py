"""
Snowflake Cortex Embeddings モジュール

Snowflake CortexのEmbedding APIをLangChain互換で提供
"""

import json
import re
from typing import Optional

from langchain_core.embeddings import Embeddings

from ..llm import get_snowflake_connection
from ..common.constants import DEFAULT_EMBEDDING_MODEL


class SnowflakeCortexEmbeddings(Embeddings):
    """
    Snowflake CortexのEmbedding APIをLangChain互換で提供するラッパークラス

    SNOWFLAKE.CORTEX.EMBED_TEXT_768()を使用して768次元のベクトルを生成する。
    """

    def __init__(self, model: Optional[str] = None):
        """
        Args:
            model: 使用するEmbeddingモデル名
                   - snowflake-arctic-embed-m (768次元、推奨)
                   - e5-base-v2 (768次元、英語)
        """
        self.model = model or DEFAULT_EMBEDDING_MODEL
        self._embedding_dim = 768

    @property
    def embedding_dim(self) -> int:
        """Embedding次元数"""
        return self._embedding_dim

    def _get_embedding(self, text: str) -> list[float]:
        """
        単一テキストのEmbeddingを取得

        Args:
            text: 入力テキスト

        Returns:
            768次元のEmbeddingベクトル
        """
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        try:
            # テキストが空の場合はゼロベクトルを返す
            if not text or not text.strip():
                return [0.0] * self._embedding_dim

            # テキストをサニタイズ
            # 制御文字を除去
            sanitized_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text)
            # 連続空白を単一空白に
            sanitized_text = ' '.join(sanitized_text.split())
            # テキストを制限（Snowflake Embeddingの入力制限対応）
            max_length = 512  # トークン制限を考慮して短めに
            if len(sanitized_text) > max_length:
                sanitized_text = sanitized_text[:max_length]

            # シングルクォートをエスケープ
            escaped_text = sanitized_text.replace("'", "''")

            # Snowflake Cortex EMBED_TEXT_768 を直接呼び出し
            query = f"SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('{self.model}', '{escaped_text}')"
            cursor.execute(query)
            result = cursor.fetchone()

            if result and result[0]:
                embedding_data = result[0]
                # リストの場合はそのまま返す
                if isinstance(embedding_data, list):
                    return [float(x) for x in embedding_data]
                # 文字列の場合はJSONとしてパース
                if isinstance(embedding_data, str):
                    embedding_data = json.loads(embedding_data)
                    if isinstance(embedding_data, list):
                        return [float(x) for x in embedding_data]
                print(f"Warning: Unexpected embedding format: type={type(embedding_data)}")
            return [0.0] * self._embedding_dim
        except Exception as e:
            print(f"Embedding error for text (first 50 chars): '{text[:50]}...': {e}")
            return [0.0] * self._embedding_dim
        finally:
            cursor.close()
            conn.close()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        複数のドキュメントをEmbeddingに変換

        Args:
            texts: テキストのリスト

        Returns:
            Embeddingベクトルのリスト
        """
        embeddings = []
        for i, text in enumerate(texts):
            if i > 0 and i % 10 == 0:
                print(f"  Embedding進捗: {i}/{len(texts)}")
            embedding = self._get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """
        クエリテキストをEmbeddingに変換

        Args:
            text: クエリテキスト

        Returns:
            Embeddingベクトル
        """
        return self._get_embedding(text)
