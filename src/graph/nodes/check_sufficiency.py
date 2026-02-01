"""
情報十分性判定ノード

提案書作成に十分な情報があるかをLLMで判定する
"""

import json
from typing import Any

from ..states.proposal_state import ProposalAgentState
from ...llm import call_cortex_llm


def check_sufficiency(state: ProposalAgentState) -> dict[str, Any]:
    """
    情報が十分かどうかをLLMで判定

    判定基準:
    1. 全カテゴリ（財務/事業/組織/外部環境）に課題があるか
    2. 地域特性情報が含まれているか
    3. 業界動向情報が含まれているか
    4. GX/DX関連情報があるか
    5. 具体的な数値データがあるか

    Args:
        state: 現在の状態

    Returns:
        更新された状態の差分
    """
    print("[check_sufficiency] 情報十分性を判定中...")

    company_info = state.get("company_info", {})
    issues = state.get("issues", [])
    research_results = state.get("research_results", {})
    check_count = state.get("sufficiency_check_count", 0)

    # 最大3回までチェック
    if check_count >= 3:
        print("  - チェック回数上限に達しました。情報十分と判定します。")
        return {
            "is_info_sufficient": True,
            "sufficiency_check_count": check_count,
        }

    # 課題のカテゴリを確認
    issue_categories = set()
    for issue in issues:
        cat = issue.get("category", "")
        issue_categories.add(cat)

    issues_text = "\n".join([
        f"- [{issue.get('category')}] {issue.get('description')} (重要度: {issue.get('severity')})"
        for issue in issues[:10]  # 最大10件
    ])

    research_text = "\n".join([
        f"【{key}】\n{value[:300]}..."
        for key, value in research_results.items()
    ]) if research_results else "（調査結果なし）"

    prompt = f"""あなたは建設業の経営コンサルタントです。
以下の情報をもとに、建設業の提案書を作成するのに十分な情報があるか判定してください。

【企業情報】
- 企業コード: {company_info.get('code', '不明')}
- 所在地: {company_info.get('location', '不明')}
- 業種: {company_info.get('industry', '不明')}
- 従業員数: {company_info.get('employees', '不明')}

【抽出された課題（カテゴリ: {', '.join(issue_categories)}）】
{issues_text}

【調査結果】
{research_text}

【評価基準】
1. 地域特性（{company_info.get('location', '')}の建設需要）の情報があるか
2. 業界動向（建設業界のトレンド）の情報があるか
3. GX/DX関連の技術動向情報があるか
4. 人材・2024年問題に関する情報があるか
5. 具体的な提案につながる数値データがあるか

判定結果をJSON形式で出力してください：
{{"is_sufficient": true/false, "missing_areas": ["不足している領域"], "reason": "理由"}}
"""

    response = call_cortex_llm(prompt)

    # JSONをパース
    is_sufficient = True
    missing_areas = []
    reason = ""

    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(response[start:end])
            is_sufficient = result.get("is_sufficient", True)
            missing_areas = result.get("missing_areas", [])
            reason = result.get("reason", "")
    except (json.JSONDecodeError, ValueError):
        # パース失敗時は十分と判定
        is_sufficient = True

    # 調査結果がある場合は十分と判定
    if research_results:
        is_sufficient = True

    print(f"  - 判定結果: {'十分' if is_sufficient else '不足'}")
    if not is_sufficient:
        print(f"  - 不足領域: {missing_areas}")
        print(f"  - 理由: {reason}")

    prompt_log = {
        "step": "情報十分性判定",
        "prompt": prompt,
        "response": response,
    }

    return {
        "is_info_sufficient": is_sufficient,
        "sufficiency_check_count": check_count + 1,
        "prompt_logs": [prompt_log],
    }
