"""
Web調査エージェント（課題駆動型）

課題ごとに対策案を生成し、Google検索で裏付け情報を収集する

フロー:
    generate_solutions → research_solutions → summarize_insights
"""

import json
import os
from typing import Any

from langgraph.graph import StateGraph, START, END

from ..states.research_state import WebResearcherState, SolutionItem
from ..states.proposal_state import Issue
from ...llm import call_cortex_llm, search_with_gemini


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


def generate_solutions(state: WebResearcherState) -> dict[str, Any]:
    """
    課題ごとに対策案と検索クエリを生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs: list[dict] = []
    issues = state.get("issues", [])
    company_info = state.get("company_info", {})
    location = company_info.get("location", "")
    industry = company_info.get("industry", "建設業")

    solutions: list[SolutionItem] = []

    # 課題を優先度順に上位5件に絞る（LLM呼び出し回数を抑制）
    severity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_issues = sorted(
        issues,
        key=lambda x: severity_order.get(x.get("severity", "low"), 2)
    )[:5]

    for issue in sorted_issues:
        prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の課題に対して、具体的な対策案と、その対策を裏付ける情報を得るための検索クエリを生成してください。

【課題】
- カテゴリ: {issue.get('category', '不明')}
- 説明: {issue.get('description', '')}
- 深刻度: {issue.get('severity', '不明')}
- 根拠: {issue.get('evidence', '')}

【企業情報】
- 所在地: {location}
- 業種: {industry}

以下の形式でJSON出力してください。必ず有効なJSONのみを出力すること：
{{
  "solution": "具体的な対策案（100-200字）",
  "search_query": "対策の根拠となる情報を得るための検索クエリ"
}}

対策案は以下を考慮してください：
- 企業の規模・地域特性に適した現実的な提案
- 建設業界のGX/DX、2024年問題への対応
- 具体的な施策と期待効果
"""

        response = _call_llm_with_log(prompt, f"対策案生成: {issue.get('category', '不明')}", logs)

        # JSONパース
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                parsed = json.loads(response[start:end])
                solution_item: SolutionItem = {
                    "issue": issue,
                    "solution": parsed.get("solution", ""),
                    "search_query": parsed.get("search_query", ""),
                    "evidence": "",  # 後で調査結果を追加
                }
                solutions.append(solution_item)
        except (json.JSONDecodeError, ValueError):
            # パース失敗時はデフォルトクエリを使用
            solution_item: SolutionItem = {
                "issue": issue,
                "solution": f"{issue.get('description', '')}への対応が必要",
                "search_query": f"{industry} {issue.get('category', '')} 対策 事例",
                "evidence": "",
            }
            solutions.append(solution_item)

    return {
        "solutions": solutions,
        "prompt_logs": logs,
    }


def _search_with_google(query: str, context: str, logs: list[dict]) -> str:
    """
    Google検索で情報を取得（Gemini API使用）

    GEMINI_API_KEYが設定されていない場合はLLMにフォールバック
    """
    # Gemini APIキーがあればGoogle検索を使用
    if os.getenv("GEMINI_API_KEY"):
        try:
            response = search_with_gemini(query, context)
            logs.append({
                "step": f"Google検索: {query[:50]}...",
                "prompt": f"検索クエリ: {query}\nコンテキスト: {context}",
                "response": response,
                "source": "google_search",
            })
            return response
        except Exception as e:
            # エラー時はLLMにフォールバック
            logs.append({
                "step": f"Google検索エラー: {query[:50]}...",
                "error": str(e),
            })

    # フォールバック: LLMの知識を使用
    fallback_prompt = f"""以下の検索クエリについて、あなたの知識で回答してください。

【検索クエリ】
{query}

【コンテキスト】
{context}

具体的な事例、数値、根拠を含めて300字程度で回答してください。
"""
    response = call_cortex_llm(fallback_prompt)
    logs.append({
        "step": f"LLMフォールバック: {query[:50]}...",
        "prompt": fallback_prompt,
        "response": response,
        "source": "llm_fallback",
    })
    return response


def research_solutions(state: WebResearcherState) -> dict[str, Any]:
    """
    各対策案に対してGoogle検索で調査し、裏付け情報を収集

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs: list[dict] = []
    solutions = state.get("solutions", [])
    company_info = state.get("company_info", {})
    location = company_info.get("location", "")
    industry = company_info.get("industry", "建設業")

    updated_solutions: list[SolutionItem] = []
    research_results: dict[str, str] = {}

    # Google検索が利用可能かログ出力
    if os.getenv("GEMINI_API_KEY"):
        print("  - Google検索を使用します（Gemini API）")
    else:
        print("  - GEMINI_API_KEY未設定のため、LLMの知識を使用します")

    for solution_item in solutions:
        issue = solution_item.get("issue", {})
        solution = solution_item.get("solution", "")
        search_query = solution_item.get("search_query", "")

        # コンテキスト情報
        context = f"""
対象: {location}の{industry}企業
課題: {issue.get('description', '')}
対策案: {solution}

以下の観点で情報を収集:
1. 類似事例・成功事例（企業名、具体的な施策、効果）
2. 関連する数値データ・統計
3. 地域特性を考慮した適用可能性
4. 期待される効果・ROI
"""

        # Google検索で裏付け情報を取得
        response = _search_with_google(search_query, context, logs)

        # 更新されたSolutionItemを作成
        updated_item: SolutionItem = {
            "issue": issue,
            "solution": solution,
            "search_query": search_query,
            "evidence": response,
        }
        updated_solutions.append(updated_item)

        # 旧形式との互換性のためresearch_resultsにも追加
        category = issue.get('category', 'その他')
        research_results[f"solution_{category}"] = f"【対策】{solution}\n\n【裏付け】{response}"

    return {
        "solutions": updated_solutions,
        "research_results": research_results,
        "prompt_logs": logs,
    }


def summarize_insights(state: WebResearcherState) -> dict[str, Any]:
    """
    調査結果から知見を統合

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs: list[dict] = []
    solutions = state.get("solutions", [])
    company_info = state.get("company_info", {})

    # 全調査結果を結合
    all_findings = []
    for item in solutions:
        issue = item.get("issue", {})
        all_findings.append(f"""
【課題】{issue.get('description', '')}
【対策案】{item.get('solution', '')}
【裏付け情報】{item.get('evidence', '')}
""")

    combined_findings = "\n---\n".join(all_findings)

    prompt = f"""あなたは経営コンサルタントです。
以下の課題・対策・調査結果から、{company_info.get('industry', '建設業')}企業への提案に活用できる重要な知見を抽出してください。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}

【調査結果】
{combined_findings}

以下の形式で、提案に活用できる具体的な知見を5〜8個抽出してください。
各知見は、課題と対策の関係性を明確にし、具体的な数値や事例を含めてください。

出力形式（JSON）：
[
  "知見1: 課題〇〇に対して、△△の対策が有効。事例として□□がある",
  "知見2: 具体的な内容",
  ...
]
"""

    response = _call_llm_with_log(prompt, "知見統合", logs)

    # 知見をパース
    insights = []
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            insights = json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        # パース失敗時は対策のサマリーを使用
        insights = [
            f"対策: {item.get('solution', '')}" for item in solutions[:5]
        ]

    return {
        "insights": insights,
        "prompt_logs": logs,
    }


def create_web_researcher() -> StateGraph:
    """
    Web調査エージェントのグラフを構築（課題駆動型）

    Returns:
        構築されたStateGraph
    """
    graph = StateGraph(WebResearcherState)

    # ノード追加
    graph.add_node("generate_solutions", generate_solutions)
    graph.add_node("research_solutions", research_solutions)
    graph.add_node("summarize_insights", summarize_insights)

    # エッジ追加（順次実行）
    graph.add_edge(START, "generate_solutions")
    graph.add_edge("generate_solutions", "research_solutions")
    graph.add_edge("research_solutions", "summarize_insights")
    graph.add_edge("summarize_insights", END)

    return graph


def run_web_researcher(
    issues: list[Issue],
    company_info: dict,
) -> dict[str, Any]:
    """
    Web調査エージェントを実行（課題駆動型）

    Args:
        issues: 課題リスト
        company_info: 企業基本情報

    Returns:
        調査結果（solutions, insights, research_results, prompt_logs）
    """
    graph = create_web_researcher()
    app = graph.compile()

    initial_state: WebResearcherState = {
        "issues": issues,
        "company_info": company_info,
        "solutions": [],
        "prompt_logs": [],
    }

    result = app.invoke(initial_state)

    return {
        "solutions": result.get("solutions", []),
        "research_results": result.get("research_results", {}),
        "insights": result.get("insights", []),
        "prompt_logs": result.get("prompt_logs", []),
    }
