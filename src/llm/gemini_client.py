"""
Gemini APIクライアント

Google検索グラウンディング機能を使用したWeb検索
"""

import os
from typing import Optional

from google import genai
from google.genai import types


_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    """
    Geminiクライアントを取得（シングルトン）

    Returns:
        Geminiクライアント
    """
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY環境変数が設定されていません")
        _client = genai.Client(api_key=api_key)
    return _client


def search_with_gemini(
    query: str,
    context: str = "",
    model: str = "gemini-2.0-flash",
) -> str:
    """
    Gemini APIでGoogle検索グラウンディングを使用して検索

    Args:
        query: 検索クエリ
        context: 追加のコンテキスト情報
        model: 使用するモデル

    Returns:
        検索結果を含む回答
    """
    client = get_gemini_client()

    prompt = f"""以下の質問について、Google検索で最新の情報を調べて回答してください。

【質問】
{query}

【コンテキスト】
{context}

回答は日本語で、具体的な数値や事例を含めて300字程度で簡潔にまとめてください。
情報源がある場合は明記してください。
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    return response.text


def search_multiple_queries(
    queries: list[str],
    context: str = "",
    model: str = "gemini-2.0-flash",
) -> dict[str, str]:
    """
    複数のクエリでGoogle検索を実行

    Args:
        queries: 検索クエリのリスト
        context: 追加のコンテキスト情報
        model: 使用するモデル

    Returns:
        クエリ→検索結果のマッピング
    """
    results = {}
    for query in queries:
        try:
            result = search_with_gemini(query, context, model)
            results[query] = result
        except Exception as e:
            results[query] = f"検索エラー: {str(e)}"
    return results
