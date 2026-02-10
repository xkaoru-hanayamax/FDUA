"""Tavily Search API テストスクリプト"""

import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    print("ERROR: TAVILY_API_KEY が .env に設定されていません")
    exit(1)

client = TavilyClient(api_key=api_key)

# テスト検索
query = "茨城県 建設業 市場動向 2024"
print(f"検索クエリ: {query}\n")

response = client.search(query, max_results=3)

for i, result in enumerate(response["results"], 1):
    print(f"--- 結果 {i} ---")
    print(f"タイトル: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"スコア: {result['score']}")
    print(f"内容: {result['content'][:200]}...")
    print()
