"""
コンテキスト構築モジュール

財務分析結果とRAG要約を統合してLLMに渡すコンテキストを構築
"""

import re
from pathlib import Path
from typing import Optional

from ..common.config import Config, default_config
from ..financial import load_financial_data, get_company_data, calculate_metrics, format_metrics_for_llm


class ContextBuilder:
    """コンテキスト構築クラス"""

    def __init__(self, config: Optional[Config] = None):
        """
        Args:
            config: 設定オブジェクト
        """
        self.config = config or default_config
        self.company_code: Optional[str] = None
        self.company_info: Optional[dict] = None
        self.financial_metrics: Optional[dict] = None
        self.financial_summary: Optional[str] = None
        self.rag_summaries: Optional[dict[str, str]] = None

    def load_financial_data(self, company_code: str) -> dict:
        """
        財務データを読み込む

        Args:
            company_code: 企業コード

        Returns:
            財務指標の辞書
        """
        self.company_code = company_code

        # CSVから直接計算
        csv_path = self.config.financial_csv_path
        df = load_financial_data(str(csv_path))
        company_df = get_company_data(df, int(company_code))

        if company_df.empty:
            raise ValueError(f"企業コード {company_code} のデータが見つかりません")

        self.financial_metrics = calculate_metrics(company_df)

        # 企業基本情報を保持
        self.company_info = {
            "code": company_code,
            "location": self.financial_metrics["所在地"],
            "industry": self.financial_metrics["業種"],
            "employees": self.financial_metrics["従業員数"],
            "capital": self.financial_metrics["資本金_億円"],
        }

        # 既存の分析結果ファイルがあれば読み込む
        summary_path = self.config.get_financial_summary_path(company_code)
        if summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                content = f.read()
                # LLM要約部分を抽出
                if "【LLM要約】" in content:
                    self.financial_summary = content.split("【LLM要約】")[1].strip()
                else:
                    self.financial_summary = content

        return self.financial_metrics

    def load_rag_summaries(self, company_code: str) -> dict[str, str]:
        """
        RAG要約結果を読み込む

        Args:
            company_code: 企業コード

        Returns:
            {クエリ: 要約}の辞書
        """
        # 要約ファイルパス
        rag_path = self.config.get_rag_summary_path(company_code)

        if not rag_path.exists():
            print(f"警告: RAG要約ファイルが見つかりません: {rag_path}")
            self.rag_summaries = {}
            return self.rag_summaries

        with open(rag_path, encoding="utf-8") as f:
            content = f.read()

        # クエリごとの要約を抽出
        self.rag_summaries = {}
        sections = re.split(r"【(.+?)】\n-+\n", content)

        # sections[0]はヘッダー、その後は[クエリ, 要約, クエリ, 要約, ...]の繰り返し
        for i in range(1, len(sections) - 1, 2):
            query = sections[i].strip()
            summary = sections[i + 1].strip()
            self.rag_summaries[query] = summary

        return self.rag_summaries

    def load_all(self, company_code: str) -> None:
        """
        財務データとRAG要約を両方読み込む

        Args:
            company_code: 企業コード
        """
        self.load_financial_data(company_code)
        self.load_rag_summaries(company_code)

    def build_context(self) -> str:
        """
        LLMに渡すコンテキストを構築

        Returns:
            構築されたコンテキストテキスト
        """
        context_parts = []

        # 企業基本情報
        if self.company_info:
            context_parts.append(f"""【企業基本情報】
- 企業コード: {self.company_info['code']}
- 所在地: {self.company_info['location']}
- 業種: {self.company_info['industry']}
- 従業員数: {self.company_info['employees']}名
- 資本金: {self.company_info['capital']}億円
""")

        # 財務指標
        if self.financial_metrics:
            context_parts.append(format_metrics_for_llm(self.financial_metrics))

        # 財務分析サマリー
        if self.financial_summary:
            context_parts.append(f"""【財務分析サマリー】
{self.financial_summary}
""")

        # RAG要約
        if self.rag_summaries:
            rag_text = "\n\n".join([
                f"【{query}】\n{summary}"
                for query, summary in self.rag_summaries.items()
            ])
            context_parts.append(f"""【有価証券報告書からの抽出情報】
{rag_text}
""")

        return "\n".join(context_parts)

    def get_company_info(self) -> Optional[dict]:
        """企業基本情報を取得"""
        return self.company_info

    def get_financial_metrics(self) -> Optional[dict]:
        """財務指標を取得"""
        return self.financial_metrics

    def get_rag_summaries(self) -> Optional[dict[str, str]]:
        """RAG要約を取得"""
        return self.rag_summaries
