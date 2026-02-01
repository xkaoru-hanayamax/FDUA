"""
コンテキスト構築モジュール

財務分析結果（Markdown）と有価証券報告書（Markdown）を統合してLLMに渡すコンテキストを構築
"""

from typing import Optional

from ..common.config import Config, default_config
from ..financial import load_financial_data, get_company_data, calculate_metrics, format_metrics_for_llm, format_raw_data_as_markdown


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
        self.financial_markdown: Optional[str] = None  # 財務分析結果全体（Markdown）
        self.securities_report_markdown: Optional[str] = None  # 有価証券報告書（Markdown）

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

        # 財務分析Markdownファイルを読み込む
        summary_path = self.config.get_financial_summary_path(company_code)
        if summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                self.financial_markdown = f.read()
        else:
            # ファイルがない場合は、指標と生データからMarkdownを生成
            metrics_text = format_metrics_for_llm(self.financial_metrics)
            raw_data_text = format_raw_data_as_markdown(company_df)
            self.financial_markdown = f"# 財務データ\n\n{metrics_text}\n\n{raw_data_text}"

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
            self.securities_report_markdown = f.read()
        return self.securities_report_markdown

    def load_all(self, company_code: str) -> None:
        """
        財務データと有価証券報告書を読み込む

        Args:
            company_code: 企業コード
        """
        self.load_financial_data(company_code)
        self.load_pdf_full_text(company_code)

    def build_context(self) -> str:
        """
        LLMに渡す統合コンテキストを構築

        財務分析結果（計算済み指標 + 生データ + LLM要約）と
        有価証券報告書を統合したMarkdown形式のコンテキストを生成

        Returns:
            統合されたMarkdownテキスト
        """
        context_parts = []

        # 財務分析結果（Markdown）
        if self.financial_markdown:
            context_parts.append(self.financial_markdown)

        # 有価証券報告書（Markdown）
        if self.securities_report_markdown:
            context_parts.append(f"""
---

# 有価証券報告書

{self.securities_report_markdown}
""")

        return "\n".join(context_parts)

    def get_company_info(self) -> Optional[dict]:
        """企業基本情報を取得"""
        return self.company_info

    def get_financial_metrics(self) -> Optional[dict]:
        """財務指標を取得"""
        return self.financial_metrics

    def get_financial_markdown(self) -> Optional[str]:
        """財務分析結果（Markdown）を取得"""
        return self.financial_markdown

    def get_securities_report_markdown(self) -> Optional[str]:
        """有価証券報告書（Markdown）を取得"""
        return self.securities_report_markdown

    # 後方互換性のため維持
    def get_pdf_full_text(self) -> Optional[str]:
        """有価証券報告書（Markdown形式）を取得（後方互換性）"""
        return self.securities_report_markdown
