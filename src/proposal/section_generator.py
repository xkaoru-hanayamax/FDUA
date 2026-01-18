"""
セクション生成モジュール

LLMを使用して提案書の各セクションを生成
"""

from typing import Optional

from ..common.constants import SECTION_CHAR_LIMITS
from ..llm import call_cortex_llm
from .context_builder import ContextBuilder


class SectionGenerator:
    """セクション生成クラス"""

    def __init__(self, context_builder: ContextBuilder):
        """
        Args:
            context_builder: コンテキストビルダー
        """
        self.context_builder = context_builder
        self.sections: dict[str, str] = {}
        self.prompt_logs: list[dict] = []

    def _call_llm_with_log(self, prompt: str, section_name: str) -> str:
        """LLMを呼び出しログを記録する"""
        response = call_cortex_llm(prompt)

        self.prompt_logs.append({
            "section": section_name,
            "prompt": prompt,
            "response": response,
        })

        return response

    def _truncate_section(self, text: str, section_name: str, limit: int) -> str:
        """
        超過したセクションをLLMで短縮

        Args:
            text: 元のセクションテキスト
            section_name: セクション名（ログ用）
            limit: 文字数上限

        Returns:
            短縮されたテキスト
        """
        current_len = len(text)
        if current_len <= limit:
            return text

        print(f"  ⚠ {section_name}が{current_len}字で上限{limit}字を超過。短縮中...")

        prompt = f"""以下のテキストを{limit}字以内に短縮してください。

【重要な要件】
- 必ず{limit}字以内に収めること（厳守）
- 主要な論点と具体的な数値は維持すること
- 冗長な表現や繰り返しを削除すること
- 構造（見出し「■」「●」「・」）は維持すること
- 内容の質を落とさずに簡潔化すること

【短縮対象テキスト】
{text}
"""
        shortened = self._call_llm_with_log(prompt, f"{section_name}（短縮）")

        # 短縮後も超過していたら警告
        new_len = len(shortened)
        if new_len > limit:
            print(f"  ⚠ 短縮後も{new_len}字で超過。強制切り詰めを適用...")
            # 最終手段：強制切り詰め（文末で切る）
            shortened = shortened[:limit - 3] + "..."

        print(f"  → {current_len}字 → {len(shortened)}字に短縮完了")
        return shortened

    @property
    def company_info(self) -> dict:
        """企業基本情報"""
        return self.context_builder.get_company_info() or {}

    def generate_overview(self) -> str:
        """
        セクション1: 企業概要・分析を生成

        Returns:
            生成されたセクションテキスト
        """
        context = self.context_builder.build_context()
        company_info = self.company_info
        limit = SECTION_CHAR_LIMITS["overview"]

        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「企業概要・分析」セクションを作成してください。

{context}

【作成するセクション】
1. 企業概要・分析
   1.1 企業概要（事業内容、沿革、強み）
   1.2 外部環境分析（業界動向、地域特性）
   1.3 財務情報分析（過去3年の推移と傾向）

【要件】
- 具体的な数値やデータを引用すること
- 地域特性（{company_info.get('location', '')}）を踏まえた分析を含めること
- 業種特性（{company_info.get('industry', '')}）を踏まえた分析を含めること
- 官公庁/民間、元請/下請の販路構成にも言及すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

        response = self._call_llm_with_log(prompt, "企業概要・分析")
        self.sections["overview"] = response
        return response

    def generate_issues(self) -> str:
        """
        セクション2: 課題の抽出を生成

        Returns:
            生成されたセクションテキスト
        """
        context = self.context_builder.build_context()
        company_info = self.company_info
        limit = SECTION_CHAR_LIMITS["issues"]

        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「課題の抽出」セクションを作成してください。

{context}

【作成するセクション】
2. 課題の抽出
   2.1 財務面の課題（収益性、安定性、キャッシュフロー等）
   2.2 事業面の課題（市場環境、競争力、技術等）
   2.3 人材・組織面の課題（人手不足、2024年問題、働き方改革等）

【要件】
- 財務データとRAG情報から具体的な課題を特定すること
- 建設業界共通の課題（GX/DX、人材不足、2024年問題）と照らし合わせること
- 地域特性（{company_info.get('location', '')}）に起因する課題も検討すること
- 各課題の優先度・重要度も示すこと
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

        response = self._call_llm_with_log(prompt, "課題の抽出")
        self.sections["issues"] = response
        return response

    def generate_strategy(self) -> str:
        """
        セクション3: 成長戦略・提案を生成

        Returns:
            生成されたセクションテキスト
        """
        context = self.context_builder.build_context()
        issues = self.sections.get("issues", "")
        limit = SECTION_CHAR_LIMITS["strategy"]

        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「成長戦略・提案」セクションを作成してください。

{context}

【抽出された課題】
{issues}

【作成するセクション】
3. 成長戦略・提案
   3.1 短期施策（1年以内）：即効性のある改善策
   3.2 中期施策（1-3年）：競争力強化策
   3.3 長期施策（3-5年）：持続的成長に向けた投資

【要件】
- 抽出した課題に対応する具体的な施策を提案すること
- GX（環境技術、脱炭素）への対応策を含めること
- DX（ICT施工、BIM/CIM、省力化）への対応策を含めること
- 人材確保・育成策（2024年問題対応、外国人材活用等）を含めること
- 地域特性を活かした戦略を提案すること
- 実現可能性の高い具体的な施策とすること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

        response = self._call_llm_with_log(prompt, "成長戦略・提案")
        self.sections["strategy"] = response
        return response

    def generate_effects(self) -> str:
        """
        セクション4: 効果試算を生成

        Returns:
            生成されたセクションテキスト
        """
        context = self.context_builder.build_context()
        strategy = self.sections.get("strategy", "")
        limit = SECTION_CHAR_LIMITS["effects"]

        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「効果試算」セクションを作成してください。

{context}

【提案した成長戦略】
{strategy}

【作成するセクション】
4. 効果試算
   4.1 売上・利益への影響（定量効果）
   4.2 定性的効果（ブランド、人材、技術力等）

【要件】
- 提案した施策の効果を具体的な数値で試算すること
- 現在の財務データを基準に、改善率や成長率で示すこと
- 短期・中期・長期それぞれの期待効果を区分すること
- 投資対効果（ROI）の観点も含めること
- 定性的効果も具体的に記述すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

        response = self._call_llm_with_log(prompt, "効果試算")
        self.sections["effects"] = response
        return response

    def generate_roadmap(self) -> str:
        """
        セクション5: ロードマップを生成

        Returns:
            生成されたセクションテキスト
        """
        context = self.context_builder.build_context()
        strategy = self.sections.get("strategy", "")
        limit = SECTION_CHAR_LIMITS["roadmap"]

        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の情報に基づいて、提案書の「ロードマップ」セクションを作成してください。

{context}

【提案した成長戦略】
{strategy}

【作成するセクション】
5. ロードマップ
   5.1 実行計画（フェーズ別の取り組み内容）
   5.2 マイルストーン（重要な節目と達成目標）

【要件】
- 5年間の実行計画を示すこと
- 年度ごとの主要施策とKPIを明確にすること
- 優先順位と依存関係を考慮した実行順序を示すこと
- 推進体制や必要なリソースにも言及すること
- 【厳守】必ず{limit}字以内で作成すること。超過は許容されません。
- マークダウン形式は使わず、見出しは「■」「●」「・」で階層化すること
"""

        response = self._call_llm_with_log(prompt, "ロードマップ")
        self.sections["roadmap"] = response
        return response

    def _check_and_truncate(self, section_key: str, section_name: str) -> None:
        """セクションの文字数をチェックし、超過時は短縮する"""
        limit = SECTION_CHAR_LIMITS.get(section_key, 3000)
        text = self.sections.get(section_key, "")
        char_count = len(text)
        print(f"  文字数: {char_count}字 (上限: {limit}字)")

        if char_count > limit:
            truncated = self._truncate_section(text, section_name, limit)
            self.sections[section_key] = truncated

    def generate_all(self) -> dict[str, str]:
        """
        全セクションを生成

        Returns:
            {セクション名: テキスト}の辞書
        """
        print("[1/5] セクション1: 企業概要・分析を生成中...")
        self.generate_overview()
        self._check_and_truncate("overview", "企業概要・分析")

        print("[2/5] セクション2: 課題の抽出を生成中...")
        self.generate_issues()
        self._check_and_truncate("issues", "課題の抽出")

        print("[3/5] セクション3: 成長戦略・提案を生成中...")
        self.generate_strategy()
        self._check_and_truncate("strategy", "成長戦略・提案")

        print("[4/5] セクション4: 効果試算を生成中...")
        self.generate_effects()
        self._check_and_truncate("effects", "効果試算")

        print("[5/5] セクション5: ロードマップを生成中...")
        self.generate_roadmap()
        self._check_and_truncate("roadmap", "ロードマップ")

        # 合計文字数を表示
        total_chars = sum(len(s) for s in self.sections.values())
        print(f"\n全セクション合計: {total_chars}字")

        return self.sections

    def get_sections(self) -> dict[str, str]:
        """生成されたセクションを取得"""
        return self.sections

    def get_prompt_logs(self) -> list[dict]:
        """プロンプトログを取得"""
        return self.prompt_logs
