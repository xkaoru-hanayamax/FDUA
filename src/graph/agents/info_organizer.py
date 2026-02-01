"""
情報整理エージェント

課題解決に必要な情報を整理し、不足を特定する
"""

import json
from typing import Any

from langgraph.graph import StateGraph, START, END

from ..states.info_state import InfoOrganizerState
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


def _parse_string_list(response: str) -> list[str]:
    """LLM出力から文字列リストをパース"""
    try:
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def identify_required_info(state: InfoOrganizerState) -> dict[str, Any]:
    """
    課題解決に必要な情報を特定

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    issues = state.get("issues", [])
    company_info = state.get("company_info", {})

    # 課題を文字列に変換
    issues_text = "\n".join([
        f"- [{issue.get('category')}] {issue.get('description')} (重要度: {issue.get('severity')})"
        for issue in issues
    ])

    prompt = f"""あなたは建設業界に詳しい経営コンサルタントです。
以下の企業の課題に対して、解決策を提案するために必要な情報をリストアップしてください。

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}
- 従業員数: {company_info.get('employees', '不明')}

【抽出された課題】
{issues_text}

【考慮すべき観点】
1. 地域特性（地域の建設需要、人口動態、行政施策）
2. 業界動向（建設業界のトレンド、技術動向）
3. GX/DX（環境技術、デジタル化の事例）
4. 人材対策（2024年問題、外国人材、働き方改革）
5. 競合・市場（官公庁/民間の比率、元請/下請の構造）

必要な情報を以下のJSON形式でリストアップしてください：
[
  "必要な情報1",
  "必要な情報2",
  ...
]

10個程度の情報をリストアップしてください。
"""

    response = _call_llm_with_log(prompt, "必要情報特定", logs)
    required_info = _parse_string_list(response)

    return {
        "required_info": required_info,
        "prompt_logs": logs,
    }


def check_availability(state: InfoOrganizerState) -> dict[str, Any]:
    """
    現在持っている情報と突合し、不足を特定

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    required_info = state.get("required_info", [])
    available_info = state.get("available_info", {})
    company_info = state.get("company_info", {})

    # 利用可能な情報を文字列に変換
    available_text = "\n".join([
        f"- {key}: {value[:200]}..." if len(str(value)) > 200 else f"- {key}: {value}"
        for key, value in available_info.items()
    ])

    prompt = f"""あなたは情報整理の専門家です。
以下の「必要な情報」と「利用可能な情報」を比較し、不足している情報を特定してください。

【必要な情報】
{chr(10).join([f"- {info}" for info in required_info])}

【利用可能な情報】
{available_text}

【企業情報】
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}

不足している情報を以下のJSON形式で出力してください：
[
  "不足している情報1",
  "不足している情報2",
  ...
]

Web検索で補完可能な情報に絞ってください。
"""

    response = _call_llm_with_log(prompt, "不足情報特定", logs)
    missing_info = _parse_string_list(response)

    return {
        "missing_info": missing_info,
        "prompt_logs": logs,
    }


def generate_search_queries(state: InfoOrganizerState) -> dict[str, Any]:
    """
    不足情報を補完するための検索クエリを生成

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    logs = state.get("prompt_logs", [])
    missing_info = state.get("missing_info", [])
    company_info = state.get("company_info", {})

    location = company_info.get('location', '')
    industry = company_info.get('industry', '')

    # 基本クエリを事前に設定
    base_queries = [
        f"{location} 建設業 市場動向 2024 2025",
        f"{industry} 業界 課題 トレンド",
        "建設業 DX 省力化 事例",
        "建設業 GX カーボンニュートラル",
    ]

    if not missing_info:
        return {
            "search_queries": base_queries,
            "prompt_logs": logs,
        }

    prompt = f"""あなたはWeb検索の専門家です。
以下の不足情報を補完するための効果的な検索クエリを生成してください。

【不足情報】
{chr(10).join([f"- {info}" for info in missing_info])}

【企業情報】
- 所在地: {location}
- 業種: {industry}

【要件】
- 各検索クエリは日本語で、具体的なキーワードを含めること
- 地域名や業種名を適切に組み込むこと
- 最新の情報が得られるよう「2024」「2025」などの年号を含めること

検索クエリを以下のJSON形式で出力してください：
[
  "検索クエリ1",
  "検索クエリ2",
  ...
]

5〜8個の検索クエリを生成してください。
"""

    response = _call_llm_with_log(prompt, "検索クエリ生成", logs)
    generated_queries = _parse_string_list(response)

    # 基本クエリと生成クエリを結合（重複除去）
    all_queries = base_queries + [q for q in generated_queries if q not in base_queries]

    return {
        "search_queries": all_queries[:10],  # 最大10クエリ
        "prompt_logs": logs,
    }


def create_info_organizer() -> StateGraph:
    """
    情報整理エージェントのグラフを構築

    Returns:
        構築されたStateGraph
    """
    graph = StateGraph(InfoOrganizerState)

    # ノード追加
    graph.add_node("identify_required_info", identify_required_info)
    graph.add_node("check_availability", check_availability)
    graph.add_node("generate_search_queries", generate_search_queries)

    # エッジ追加（順次実行）
    graph.add_edge(START, "identify_required_info")
    graph.add_edge("identify_required_info", "check_availability")
    graph.add_edge("check_availability", "generate_search_queries")
    graph.add_edge("generate_search_queries", END)

    return graph


def run_info_organizer(
    issues: list[dict],
    company_info: dict,
    available_info: dict,
) -> dict[str, Any]:
    """
    情報整理エージェントを実行

    Args:
        issues: 抽出された課題リスト
        company_info: 企業基本情報
        available_info: 現在持っている情報

    Returns:
        整理結果（required_info, missing_info, search_queries, prompt_logs）
    """
    graph = create_info_organizer()
    app = graph.compile()

    initial_state: InfoOrganizerState = {
        "issues": issues,
        "company_info": company_info,
        "available_info": available_info,
        "prompt_logs": [],
    }

    result = app.invoke(initial_state)

    return {
        "required_info": result.get("required_info", []),
        "missing_info": result.get("missing_info", []),
        "search_queries": result.get("search_queries", []),
        "prompt_logs": result.get("prompt_logs", []),
    }
