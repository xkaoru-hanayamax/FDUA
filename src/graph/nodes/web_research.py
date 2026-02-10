"""
Web調査ノード

Tavily Search API を使って企業の地域特性・業界動向・GX/DX等の
外部情報を収集し、提案書の品質を向上させる。
結果はマークダウンファイルとして保存し、下流ノードで参照される。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...common.config import Config
from ...llm import call_cortex_llm
from ...common.debug import debug_llm_call, debug_log

logger = logging.getLogger(__name__)

# PDF中心のドメインはTavilyのテキスト抽出品質が極端に低いため除外
_EXCLUDE_DOMAINS: list[str] = [
    "ibaken.or.jp",       # 茨城県建設業協会（PDF統計表）
    "nikkenren.com",      # 日本建設業連合会（PDFパンフレット）
    "cas.go.jp",          # 内閣官房（PDF資料）
    "cezaidan.or.jp",     # 建設業技術者センター（PDF報告書）
    "jsite.mhlw.go.jp",   # 厚生労働省地方局（PDF通達）
    "env.go.jp",          # 環境省（PDF補助金資料）
    "ktr.mlit.go.jp",     # 関東地方整備局（PDF議事録）
]

# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


def _generate_queries_with_llm(
    state: ProposalAgentState,
) -> tuple[list[dict[str, str]], list[dict]]:
    """
    LLMを使って企業固有の検索クエリを生成する。

    Args:
        state: 現在の状態（company_info, financial_markdown, securities_markdown を使用）

    Returns:
        (queries, prompt_logs)
        queries: [{"category": "...", "query": "..."}, ...]
        prompt_logs: [{"step": "...", "prompt": "...", "response": "..."}, ...]
    """
    company_info = state.get("company_info", {})
    financial_markdown = state.get("financial_markdown", "")
    securities_markdown = state.get("securities_markdown", "")

    company_code = company_info.get("code", state.get("company_code", "unknown"))
    location = company_info.get("location", "不明")
    industry = company_info.get("industry", "不明")
    employees = company_info.get("employees", "不明")
    capital = company_info.get("capital", "不明")

    prompt = f"""【役割】
あなたは建設業界の経営コンサルタントです。
以下の企業情報を分析し、この企業の課題抽出と成長戦略策定に必要な
外部情報を収集するための Web 検索クエリを生成してください。

【評価基準（これらの観点をカバーするクエリを生成すること）】
1. 地域特性: 企業所在地の人口動態、公共工事動向、地域固有の課題
2. 業界特性・販路商流: この企業の具体的な事業領域の市場動向
3. GX: この企業の事業内容に即した環境・脱炭素の取り組み
4. DX: この企業の事業内容に即したデジタル化・省力化
5. 人材・需要: この企業の規模・地域に即した人材確保策

【出力形式】
必ず以下のJSON配列で出力すること。JSON以外のテキストは含めないこと：
[
  {{"category": "カテゴリ名", "query": "検索クエリ文字列"}},
  ...
]

【ルール】
- 5つのクエリを生成すること
- 各クエリはWeb検索エンジンに直接入力できる自然な検索キーワードにすること
- この企業固有の状況（地域、業種、財務状況、事業内容）を反映した具体的なクエリにすること
- 一般的な「建設業 DX」のような汎用クエリではなく、企業の特性を踏まえたクエリにすること

【企業情報】
- 企業コード: {company_code}
- 所在地: {location}
- 業種: {industry}
- 従業員数: {employees}
- 資本金: {capital}億円

【財務データ（3年分）】
{financial_markdown}

【有価証券報告書】
{securities_markdown}
"""

    logs: list[dict] = []

    debug_log("Web調査クエリ生成LLM呼び出し", f"プロンプト長: {len(prompt)}文字")

    response = call_cortex_llm(prompt)

    debug_llm_call("Web調査: クエリ生成", prompt, response)

    logs.append({
        "step": "web_research_query_generation",
        "prompt": prompt,
        "response": response,
    })

    # JSON部分を抽出してパース
    start = response.find("[")
    end = response.rfind("]") + 1
    if start < 0 or end <= start:
        raise ValueError(f"LLMクエリ生成: レスポンスにJSON配列が見つかりません: {response[:200]}")

    json_str = response[start:end]
    parsed = json.loads(json_str)

    if (
        not isinstance(parsed, list)
        or len(parsed) < 1
        or not all(
            isinstance(q, dict) and "category" in q and "query" in q
            for q in parsed
        )
    ):
        raise ValueError(f"LLMクエリ生成: バリデーション失敗: {parsed}")

    print(f"  - LLMクエリ生成成功: {len(parsed)}件")
    return parsed, logs


def _build_research_markdown(query_answers: list[dict]) -> tuple[dict[str, str], str]:
    """
    各クエリの Tavily advanced answer をカテゴリ別マークダウンに整形する。

    Args:
        query_answers: [{"category", "query", "answer", "sources"}, ...]

    Returns:
        (research_results dict, markdown全文)
        research_results は単一キー "Web調査結果" の辞書。
    """
    sections: list[str] = []
    for qa in query_answers:
        category = qa.get("category", "")
        query = qa.get("query", "")
        answer = qa.get("answer", "")
        sources = qa.get("sources", [])

        if not answer:
            continue

        source_lines = "\n".join(
            f"- {s.get('title', '（タイトルなし）')} ({s.get('url', '')})"
            for s in sources
            if s.get("url")
        )

        section = f"## {category}\n検索: {query}\n\n{answer}\n"
        if source_lines:
            section += f"\n出典:\n{source_lines}\n"
        sections.append(section)

    flat_text = "\n".join(sections)

    # State 用の dict（単一キー）
    research_results: dict[str, str] = {"Web調査結果": flat_text}

    # ファイル保存用のマークダウン全文
    full_markdown = f"# Web調査結果\n\n{flat_text}\n"
    return research_results, full_markdown


def _save_research_markdown(
    company_code: str,
    markdown: str,
    config_dict: dict,
) -> Path:
    """調査結果をマークダウンファイルとして保存する。"""
    if config_dict.get("data_dir"):
        config = Config(data_dir=config_dict["data_dir"])
    else:
        config = Config()

    file_path = config.output_dir / f"{company_code}_web_research.md"
    file_path.write_text(markdown, encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# メインノード関数
# ---------------------------------------------------------------------------


def web_research(state: ProposalAgentState) -> dict[str, Any]:
    """
    Tavily Search API を使った Web 調査ノード。

    1. LLMで企業固有の検索クエリを生成
    2. 各クエリで Tavily search (include_answer="advanced") で要約回答を取得
    3. 各クエリの answer をカテゴリ別マークダウンに整形
    4. マークダウンファイルに保存 + research_results に格納
    """
    print("[web_research] Web調査を実行中...")

    company_info = state.get("company_info", {})
    company_code = state.get("company_code", "unknown")
    config_dict = state.get("config", {})

    # --- API キーチェック ---
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        print("  [web_research] WARNING: TAVILY_API_KEY が未設定のため、Web調査をスキップします")
        logger.warning("TAVILY_API_KEY が未設定です。Web調査をスキップします。")
        return {
            "search_queries": [],
            "research_results": {},
            "insights": [],
            "is_info_sufficient": True,
        }

    # --- Tavily クライアント初期化 ---
    try:
        from tavily import TavilyClient
    except ImportError:
        print("  [web_research] WARNING: tavily-python が未インストールです。Web調査をスキップします")
        logger.warning("tavily-python が未インストールです。")
        return {
            "search_queries": [],
            "research_results": {},
            "insights": [],
            "is_info_sufficient": True,
        }

    client = TavilyClient(api_key=api_key)

    # --- LLMによるクエリ生成 ---
    queries, query_logs = _generate_queries_with_llm(state)
    search_query_strings = [q["query"] for q in queries]
    print(f"  - 検索クエリ数: {len(queries)}")
    for q in queries:
        print(f"    [{q['category']}] {q['query']}")

    # --- 検索実行（include_answer="advanced" で要約回答を取得） ---
    query_answers: list[dict] = []

    for q in queries:
        try:
            response = client.search(
                query=q["query"],
                search_depth="advanced",
                max_results=5,
                exclude_domains=_EXCLUDE_DOMAINS,
                include_answer="advanced",
            )
            answer = response.get("answer", "")
            results = response.get("results", [])
            sources = [
                {"title": r.get("title", ""), "url": r.get("url", "")}
                for r in results
            ]
            query_answers.append({
                "category": q["category"],
                "query": q["query"],
                "answer": answer,
                "sources": sources,
            })
            answer_preview = answer[:80] + "..." if len(answer) > 80 else answer
            print(f"  - [{q['category']}] answer取得 ({len(answer)}文字): {answer_preview}")
        except Exception as e:
            logger.error(f"検索エラー [{q['category']}]: {e}")
            print(f"  - [{q['category']}] エラー: {e}")

    answers_with_content = [qa for qa in query_answers if qa.get("answer")]
    print(f"  - answer取得件数: {len(answers_with_content)}/{len(queries)}")

    # --- マークダウン整形 ---
    research_results, full_markdown = _build_research_markdown(query_answers)

    # --- マークダウンファイル保存 ---
    md_path = _save_research_markdown(company_code, full_markdown, config_dict)
    print(f"  - 保存: {md_path}")

    # --- insights 生成（各answerの冒頭を要約として使用） ---
    insights = [
        f"{qa['category']}: {qa['answer'][:100]}"
        for qa in query_answers
        if qa.get("answer")
    ]

    # --- 情報十分性判定（answerが空でないクエリが3件以上） ---
    is_sufficient = len(answers_with_content) >= 3

    print(f"  - 情報十分性: {is_sufficient} ({len(answers_with_content)}/3件以上)")
    print("[web_research] Web調査完了")

    return {
        "search_queries": search_query_strings,
        "research_results": research_results,
        "insights": insights,
        "is_info_sufficient": is_sufficient,
        "prompt_logs": query_logs,
    }
