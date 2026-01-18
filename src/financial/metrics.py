"""
財務指標計算モジュール

財務指標の算出とフォーマット機能を提供
"""

from typing import Optional

import pandas as pd


def calculate_metrics(company_df: pd.DataFrame) -> dict:
    """
    財務指標を算出

    Args:
        company_df: 企業の財務データDataFrame（年度順にソート済み）

    Returns:
        財務指標の辞書
    """
    latest = company_df.iloc[-1]

    # 基本情報
    metrics = {
        "コード": int(latest["コード"]),
        "所在地": latest["本社所在地"],
        "業種": latest["業種分類"],
        "従業員数": int(latest["従業員数（連結）"]),
        "資本金_億円": float(latest["資本金（億円）"]),
    }

    # 3年分の推移データ
    years = company_df["YEAR"].tolist()
    metrics["年度"] = years

    # PL指標
    sales = company_df["売上高"].tolist()
    metrics["売上高"] = sales
    metrics["売上高成長率"] = [
        None if i == 0 else round((sales[i] - sales[i-1]) / sales[i-1] * 100, 2)
        for i in range(len(sales))
    ]

    op_profit = company_df["営業利益"].tolist()
    metrics["営業利益"] = op_profit
    metrics["営業利益率"] = [
        round(op / s * 100, 2) if s != 0 else 0
        for op, s in zip(op_profit, sales)
    ]

    metrics["当期純利益"] = company_df["当期純利益"].tolist()

    # BS指標
    total_assets = company_df["総資産"].tolist()
    net_assets = company_df["純資産"].tolist()
    metrics["総資産"] = total_assets
    metrics["純資産"] = net_assets
    metrics["自己資本比率"] = [
        round(na / ta * 100, 2) if ta != 0 else 0
        for na, ta in zip(net_assets, total_assets)
    ]

    # CF指標
    metrics["営業CF"] = company_df["営業活動によるキャッシュ・フロー"].tolist()
    metrics["投資CF"] = company_df["投資活動によるキャッシュ・フロー"].tolist()
    metrics["財務CF"] = company_df["財務活動によるキャッシュ・フロー"].tolist()

    return metrics


def _format_number(n: Optional[float]) -> str:
    """数値を読みやすい形式にフォーマット"""
    if n is None:
        return "-"
    if abs(n) >= 100_000_000:
        return f"{n/100_000_000:.1f}億"
    elif abs(n) >= 10_000:
        return f"{n/10_000:.0f}万"
    return f"{n:,.0f}"


def format_metrics_for_llm(metrics: dict) -> str:
    """
    LLMに渡すためのテキスト形式に整形

    Args:
        metrics: calculate_metrics()で算出した財務指標

    Returns:
        整形されたテキスト
    """
    text = f"""
【企業基本情報】
- コード: {metrics['コード']}
- 所在地: {metrics['所在地']}
- 業種: {metrics['業種']}
- 従業員数: {metrics['従業員数']}名
- 資本金: {metrics['資本金_億円']}億円

【損益計算書（PL）3年推移】
年度: {metrics['年度']}
売上高: {[_format_number(x) for x in metrics['売上高']]}
売上高成長率: {metrics['売上高成長率']}%
営業利益: {[_format_number(x) for x in metrics['営業利益']]}
営業利益率: {metrics['営業利益率']}%
当期純利益: {[_format_number(x) for x in metrics['当期純利益']]}

【貸借対照表（BS）】
総資産: {[_format_number(x) for x in metrics['総資産']]}
純資産: {[_format_number(x) for x in metrics['純資産']]}
自己資本比率: {metrics['自己資本比率']}%

【キャッシュフロー（CF）】
営業CF: {[_format_number(x) for x in metrics['営業CF']]}
投資CF: {[_format_number(x) for x in metrics['投資CF']]}
財務CF: {[_format_number(x) for x in metrics['財務CF']]}
"""
    return text
