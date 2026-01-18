"""
財務分析モジュール

LLMを使用した財務情報の分析・要約機能を提供
"""

from pathlib import Path
from typing import Optional, Union

from ..llm import call_cortex_llm
from ..common.config import Config, default_config
from .loader import load_financial_data, get_company_data
from .metrics import calculate_metrics, format_metrics_for_llm


def summarize_with_llm(metrics: dict) -> str:
    """
    LLMを使って財務情報を要約

    Args:
        metrics: calculate_metrics()で算出した財務指標

    Returns:
        LLMによる要約テキスト
    """
    metrics_text = format_metrics_for_llm(metrics)

    prompt = f"""あなたは建設業界に詳しい財務アナリストです。
以下の企業の財務データを分析し、簡潔に要約してください。

{metrics_text}

以下の観点で要約してください（各項目2-3文程度）：
1. 財務状況の概要（売上・利益の傾向）
2. 収益性・安定性の評価（利益率、自己資本比率）
3. キャッシュフローの状況
4. 地域特性を踏まえた考察（{metrics['所在地']}の建設需要など）
5. 業種特性を踏まえた考察（{metrics['業種']}としての特徴）
"""

    return call_cortex_llm(prompt)


class FinancialAnalyzer:
    """財務分析クラス"""

    def __init__(self, config: Optional[Config] = None):
        """
        Args:
            config: 設定オブジェクト（Noneの場合はデフォルト）
        """
        self.config = config or default_config
        self.prompt_logs: list[dict] = []

    def get_prompt_logs(self) -> list[dict]:
        """プロンプトログを取得"""
        return self.prompt_logs

    def clear_prompt_logs(self) -> None:
        """プロンプトログをクリア"""
        self.prompt_logs = []

    def analyze(
        self,
        company_code: Union[str, int],
        save_output: bool = True,
    ) -> dict:
        """
        企業の財務分析を実行

        Args:
            company_code: 企業コード
            save_output: 結果をファイルに保存するかどうか

        Returns:
            分析結果の辞書
            {
                "metrics": 財務指標,
                "metrics_text": 整形済みテキスト,
                "summary": LLM要約,
                "output_path": 保存先パス（save_output=Trueの場合）
            }
        """
        code = int(company_code)
        print(f"企業コード {code} の分析を開始...")

        # データ読み込み
        df = load_financial_data(self.config.financial_csv_path)
        company_df = get_company_data(df, code)

        if company_df.empty:
            raise ValueError(f"企業コード {code} のデータが見つかりません")

        # 財務指標算出
        metrics = calculate_metrics(company_df)
        metrics_text = format_metrics_for_llm(metrics)
        print("財務指標を算出しました")
        print(metrics_text)

        # LLM要約
        print("LLMで要約中...")
        prompt = f"""あなたは建設業界に詳しい財務アナリストです。
以下の企業の財務データを分析し、簡潔に要約してください。

{metrics_text}

以下の観点で要約してください（各項目2-3文程度）：
1. 財務状況の概要（売上・利益の傾向）
2. 収益性・安定性の評価（利益率、自己資本比率）
3. キャッシュフローの状況
4. 地域特性を踏まえた考察（{metrics['所在地']}の建設需要など）
5. 業種特性を踏まえた考察（{metrics['業種']}としての特徴）
"""
        summary = call_cortex_llm(prompt)

        # プロンプトログに記録
        self.prompt_logs.append({
            "company_code": str(code),
            "query": "財務分析要約",
            "prompt": prompt,
            "response": summary,
        })

        result = {
            "metrics": metrics,
            "metrics_text": metrics_text,
            "summary": summary,
        }

        # ファイル出力
        if save_output:
            output_path = self.config.get_financial_summary_path(str(code))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"=== 企業コード {code} 財務分析結果 ===\n\n")
                f.write("【入力データ】\n")
                f.write(metrics_text)
                f.write("\n\n【LLM要約】\n")
                f.write(summary)

            print(f"結果を {output_path} に保存しました")
            result["output_path"] = str(output_path)

        return result
