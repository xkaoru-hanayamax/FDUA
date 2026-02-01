"""
コンテキスト構築モジュール

財務分析結果と有価証券報告書（Markdown形式）を統合してLLMに渡すコンテキストを構築
"""

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
        self.pdf_full_text: Optional[str] = None

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

    def load_pdf_full_text(self, company_code: str) -> str:
        """
        有価証券報告書Markdownファイルを読み込んで保持

        事前に変換済みのMarkdownファイルを使用

        Args:
            company_code: 企業コード

        Returns:
            Markdownテキスト
        """
        md_path = self.config.get_markdown_path(company_code)
        if not md_path.exists():
            raise FileNotFoundError(
                f"有価証券報告書Markdownが見つかりません: {md_path}\n"
                "先に 'python -m cli.convert_pdf --all' を実行してください"
            )

        with open(md_path, encoding="utf-8") as f:
            self.pdf_full_text = f.read()
        return self.pdf_full_text

    def load_all(self, company_code: str) -> None:
        """
        財務データと有価証券報告書全文を読み込む

        Args:
            company_code: 企業コード
        """
        self.load_financial_data(company_code)
        self.load_pdf_full_text(company_code)

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

        # 有価証券報告書（Markdown形式）
        if self.pdf_full_text:
            context_parts.append(f"""【有価証券報告書（Markdown形式）】
{self.pdf_full_text}
""")

        return "\n".join(context_parts)

    def get_company_info(self) -> Optional[dict]:
        """企業基本情報を取得"""
        return self.company_info

    def get_financial_metrics(self) -> Optional[dict]:
        """財務指標を取得"""
        return self.financial_metrics

    def get_pdf_full_text(self) -> Optional[str]:
        """有価証券報告書（Markdown形式）を取得"""
        return self.pdf_full_text
