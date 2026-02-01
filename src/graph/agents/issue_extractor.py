"""
課題抽出エージェント

財務データと有価証券報告書から企業の課題を抽出する
"""

import json
from typing import Any

from langgraph.graph import StateGraph, START, END

from ..states.issue_state import IssueExtractorState
from ..states.proposal_state import Issue
from ...llm import call_cortex_llm


def _call_llm_with_log(
    prompt: str,
    step_name: str,
    logs: list[dict],
) -> str:
    """LLMを呼び出してログを記録"""
    response = call_cortex_llm(prompt)
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


def analyze_financial(state: IssueExtractorState) -> dict[str, Any]:
    """
    財務データから課題を抽出

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    company_info = state.get("company_info", {})

    prompt = f"""あなたは建設業界に詳しい財務アナリストです。
以下の財務データを分析し、この企業が抱える課題を抽出してください。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}
- 従業員数: {company_info.get('employees', '不明')}

【財務データ】
{state['financial_markdown']}

以下の観点で課題を抽出してください：
1. 収益性の課題（売上高、利益率の推移）
2. 財務安定性の課題（自己資本比率、流動比率）
3. キャッシュフローの課題
4. 成長性の課題

各課題について、以下のJSON形式で出力してください。必ず有効なJSONを出力すること：
[
  {{
    "category": "財務",
    "description": "課題の説明",
    "severity": "high/medium/low",
    "source": "財務",
    "evidence": "根拠となる数値データ"
  }}
]

最低3つ、最大6つの課題を抽出してください。
"""

    response = _call_llm_with_log(prompt, "財務分析", logs)
    financial_issues = _parse_issues_json(response)

    return {
        "financial_issues": financial_issues,
        "prompt_logs": logs,
    }


def analyze_securities(state: IssueExtractorState) -> dict[str, Any]:
    """
    有価証券報告書から課題を抽出

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    company_info = state.get("company_info", {})

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の有価証券報告書の内容を分析し、この企業が抱える課題を抽出してください。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}

【有価証券報告書】
{state['securities_markdown'][:30000]}

以下の観点で課題を抽出してください：
1. 事業面の課題（市場環境、競争力、技術力）
2. 組織・人材面の課題（人手不足、2024年問題、働き方改革）
3. 外部環境の課題（地域の建設需要、規制対応）
4. GX/DX対応の課題（環境技術、デジタル化）

各課題について、以下のJSON形式で出力してください。必ず有効なJSONを出力すること：
[
  {{
    "category": "事業/組織/外部環境/GX・DX",
    "description": "課題の説明",
    "severity": "high/medium/low",
    "source": "有報",
    "evidence": "根拠となる記述"
  }}
]

最低4つ、最大8つの課題を抽出してください。
"""

    response = _call_llm_with_log(prompt, "有報分析", logs)
    securities_issues = _parse_issues_json(response)

    return {
        "securities_issues": securities_issues,
        "prompt_logs": logs,
    }


def integrate_issues(state: IssueExtractorState) -> dict[str, Any]:
    """
    財務課題と有報課題を統合

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])

    financial_issues = state.get("financial_issues", [])
    securities_issues = state.get("securities_issues", [])

    # 全課題を統合
    all_issues = financial_issues + securities_issues

    # カテゴリ別に分類
    categories: dict[str, list[Issue]] = {}
    for issue in all_issues:
        cat = issue.get("category", "その他")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(issue)

    # 重複を排除し、優先度でソート
    severity_order = {"high": 0, "medium": 1, "low": 2}
    integrated = sorted(
        all_issues,
        key=lambda x: severity_order.get(x.get("severity", "low"), 2)
    )

    return {
        "integrated_issues": integrated,
        "issue_categories": categories,
        "prompt_logs": logs,
    }


def create_issue_extractor() -> StateGraph:
    """
    課題抽出エージェントのグラフを構築

    Returns:
        構築されたStateGraph
    """
    graph = StateGraph(IssueExtractorState)

    # ノード追加
    graph.add_node("analyze_financial", analyze_financial)
    graph.add_node("analyze_securities", analyze_securities)
    graph.add_node("integrate_issues", integrate_issues)

    # エッジ追加（並列実行→統合）
    graph.add_edge(START, "analyze_financial")
    graph.add_edge(START, "analyze_securities")
    graph.add_edge("analyze_financial", "integrate_issues")
    graph.add_edge("analyze_securities", "integrate_issues")
    graph.add_edge("integrate_issues", END)

    return graph


def run_issue_extractor(
    financial_markdown: str,
    securities_markdown: str,
    company_info: dict,
) -> dict[str, Any]:
    """
    課題抽出エージェントを実行

    Args:
        financial_markdown: 財務分析結果（Markdown）
        securities_markdown: 有価証券報告書（Markdown）
        company_info: 企業基本情報

    Returns:
        抽出結果（issues, issue_categories, prompt_logs）
    """
    graph = create_issue_extractor()
    app = graph.compile()

    initial_state: IssueExtractorState = {
        "financial_markdown": financial_markdown,
        "securities_markdown": securities_markdown,
        "company_info": company_info,
        "prompt_logs": [],
    }

    result = app.invoke(initial_state)

    return {
        "issues": result.get("integrated_issues", []),
        "issue_categories": result.get("issue_categories", {}),
        "prompt_logs": result.get("prompt_logs", []),
    }
