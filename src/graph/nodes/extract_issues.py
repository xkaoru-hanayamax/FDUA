"""
課題抽出ノード

財務データと有価証券報告書から企業の課題を抽出する
"""

import json
from typing import Any

from ..states.proposal_state import ProposalAgentState, Issue
from ...llm import call_cortex_llm
from ...common.debug import debug_llm_call, debug_log
from ...common.constants import EVALUATION_CRITERIA


def _call_llm_with_log(
    prompt: str,
    step_name: str,
    logs: list[dict],
) -> str:
    """LLMを呼び出してログを記録"""
    debug_log(f"課題抽出LLM呼び出し: {step_name}", f"プロンプト長: {len(prompt)}文字")

    response = call_cortex_llm(prompt)

    # デバッグログ出力
    debug_llm_call(f"課題抽出: {step_name}", prompt, response)

    logs.append({
        "step": step_name,
        "prompt": prompt,
        "response": response,
    })
    return response


def _parse_issues_json(response: str) -> list[Issue]:
    """LLM出力からIssueリストをパース"""
    try:
        # JSON部分を抽出
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            parsed = json.loads(json_str)
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # パース失敗時は空リスト
    return []


def extract_issues(state: ProposalAgentState) -> dict[str, Any]:
    """
    財務データと有価証券報告書から課題を抽出

    1回のLLM呼び出しで財務・有報の両方から一貫した課題抽出を行う

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[extract_issues] 課題抽出を実行中...")

    financial_markdown = state.get("financial_markdown", "")
    securities_markdown = state.get("securities_markdown", "")
    company_info = state.get("company_info", {})

    if not financial_markdown or not securities_markdown:
        return {
            "issues": [],
            "issue_categories": {},
            "errors": state.get("errors", []) + ["データが読み込まれていません"],
        }

    logs: list[dict] = []

    prompt = f"""【役割】
あなたは建設業界に詳しい経営コンサルタント兼財務アナリストです。
財務データと有価証券報告書を統合的に分析し、企業の課題を抽出してください。

{EVALUATION_CRITERIA}

【出力形式の厳守事項】
必ず以下のJSON形式で出力すること。JSON以外のテキストは含めないこと：
[
  {{
    "category": "財務/事業/組織・人材/外部環境/GX・DX",
    "description": "課題の説明",
    "severity": "high/medium/low",
    "source": "財務/有報/両方",
    "evidence": "根拠となる数値データや記述"
  }}
]

【抽出する課題の観点】
■ 財務面（財務データから）
1. 収益性の課題（売上高、利益率の推移）
2. 財務安定性の課題（自己資本比率、流動比率）
3. キャッシュフローの課題
4. 成長性の課題

■ 事業・組織面（有価証券報告書から）
5. 事業面の課題（市場環境、競争力、技術力）
6. 組織・人材面の課題（人手不足、2024年問題、働き方改革）
7. 外部環境の課題（地域の建設需要、規制対応）
8. GX/DX対応の課題（環境技術、デジタル化）

【抽出数】
最低6つ、最大10の課題を抽出すること。
財務面と事業・組織面をバランスよく含めること。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}
- 従業員数: {company_info.get('employees', '不明')}

【財務データ】
{financial_markdown}

【有価証券報告書】
{securities_markdown}
"""

    response = _call_llm_with_log(prompt, "統合課題抽出", logs)
    all_issues = _parse_issues_json(response)

    # カテゴリ別に分類
    categories: dict[str, list[Issue]] = {}
    for issue in all_issues:
        cat = issue.get("category", "その他")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(issue)

    # 重要度でソート
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_issues = sorted(
        all_issues,
        key=lambda x: severity_order.get(x.get("severity", "low"), 2)
    )

    print(f"  - 抽出された課題: {len(sorted_issues)}件")
    for cat, cat_issues in categories.items():
        print(f"    - {cat}: {len(cat_issues)}件")

    return {
        "issues": sorted_issues,
        "issue_categories": categories,
        "prompt_logs": logs,
    }
