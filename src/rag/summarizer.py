"""
RAG要約モジュール

検索結果のLLM要約機能を提供
"""

from typing import Optional

from ..llm import call_cortex_llm
from ..common.config import Config, default_config
from ..common.constants import DEFAULT_RAG_QUERIES
from .searcher import RAGSearcher


# デフォルトクエリ（後方互換性のためエクスポート）
DEFAULT_QUERIES = DEFAULT_RAG_QUERIES


class RAGSummarizer:
    """RAG要約クラス"""

    def __init__(
        self,
        config: Optional[Config] = None,
        searcher: Optional[RAGSearcher] = None,
    ):
        """
        Args:
            config: 設定オブジェクト
            searcher: RAGSearcherオブジェクト
        """
        self.config = config or default_config
        self.searcher = searcher or RAGSearcher(config=self.config)
        self.prompt_logs: list[dict] = []

    def summarize(
        self,
        company_code: str,
        query: str,
        top_k: int = 20,
    ) -> str:
        """
        クエリに基づいてRAG要約を生成

        Args:
            company_code: 企業コード
            query: 要約のクエリ（何を知りたいか）
            top_k: 使用するチャンク数

        Returns:
            要約テキスト
        """
        # 関連チャンクを検索
        search_results = self.searcher.search(company_code, query, top_k)
        if not search_results:
            return "関連する情報が見つかりませんでした。"

        # コンテキスト構築
        context = "\n\n---\n\n".join([chunk for chunk, _ in search_results])

        # プロンプト作成
        prompt = f"""以下は有価証券報告書から抽出した関連テキストです。

【抽出テキスト】
{context}

【要約テーマ】
{query}

上記の抽出テキストに基づいて、テーマに関する内容を日本語で要約してください。
抽出テキストに含まれる情報のみを使用し、具体的な数値や固有名詞があれば含めてください。
箇条書きで要点を整理した形式で回答してください。"""

        # LLM呼び出し
        response = call_cortex_llm(prompt)

        # プロンプトログに記録
        self.prompt_logs.append({
            "company_code": company_code,
            "query": query,
            "prompt": prompt,
            "response": response,
        })

        return response

    def summarize_all(
        self,
        company_code: str,
        queries: Optional[list[str]] = None,
        top_k: int = 20,
        save_output: bool = True,
    ) -> dict[str, str]:
        """
        複数クエリで一括要約

        Args:
            company_code: 企業コード
            queries: 要約クエリのリスト（Noneの場合はデフォルトクエリ）
            top_k: 使用するチャンク数
            save_output: 結果をファイルに保存するかどうか

        Returns:
            {クエリ: 要約}の辞書
        """
        if queries is None:
            queries = DEFAULT_QUERIES

        # インデックスを読み込む
        self.searcher.load_index(company_code)

        print(f"企業コード {company_code} の有価証券報告書を読込みました")
        print(f"チャンク数: {len(self.searcher.get_chunks(company_code))}")

        # 各クエリで要約
        results = {}
        for query in queries:
            print(f"\n要約中: {query}")
            summary = self.summarize(company_code, query, top_k)
            results[query] = summary
            print("完了")

        # ファイル出力
        if save_output:
            output_file = self.config.get_rag_summary_path(company_code)
            self._save_summaries(company_code, results, output_file)

        return results

    def _save_summaries(
        self,
        company_code: str,
        results: dict[str, str],
        output_file,
    ) -> None:
        """要約結果をファイルに保存"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"有価証券報告書要約 - 企業コード: {company_code}\n")
            f.write("=" * 60 + "\n\n")
            for query, summary in results.items():
                f.write(f"【{query}】\n")
                f.write("-" * 40 + "\n")
                f.write(summary + "\n\n")

        print(f"\n出力ファイル: {output_file}")

    def get_prompt_logs(self) -> list[dict]:
        """プロンプトログを取得"""
        return self.prompt_logs

    def clear_prompt_logs(self) -> None:
        """プロンプトログをクリア"""
        self.prompt_logs = []


def write_prompt_log(
    all_prompt_logs: list[tuple[str, list[dict]]],
    output_file=None,
) -> None:
    """
    プロンプトログをファイルに書き出す

    Args:
        all_prompt_logs: [(企業コード, プロンプトログリスト), ...]
        output_file: 出力ファイルパス（Noneの場合はデフォルトパス）
    """
    if output_file is None:
        output_file = default_config.get_prompt_log_path()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("プロンプトログ - 有価証券報告書RAG要約\n")
        f.write("=" * 80 + "\n\n")

        for company_code, prompt_logs in all_prompt_logs:
            f.write(f"{'#' * 80}\n")
            f.write(f"# 企業コード: {company_code}\n")
            f.write(f"{'#' * 80}\n\n")

            for i, log in enumerate(prompt_logs, 1):
                f.write(f"[{i}] クエリ: {log['query']}\n")
                f.write("-" * 60 + "\n")
                f.write("【入力プロンプト】\n")
                f.write(log["prompt"] + "\n\n")
                f.write("【LLM出力】\n")
                f.write(log["response"] + "\n")
                f.write("\n" + "=" * 60 + "\n\n")

    print(f"プロンプトログ出力: {output_file}")
