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
    LLMに渡すためのMarkdown形式に整形

    Args:
        metrics: calculate_metrics()で算出した財務指標

    Returns:
        整形されたMarkdownテキスト
    """
    years = metrics['年度']

    # 計算済み指標のMarkdownテーブル
    text = f"""## 企業基本情報

| 項目 | 値 |
|------|-----|
| コード | {metrics['コード']} |
| 所在地 | {metrics['所在地']} |
| 業種 | {metrics['業種']} |
| 従業員数 | {metrics['従業員数']}名 |
| 資本金 | {metrics['資本金_億円']}億円 |

## 財務指標（3年推移）

### 損益計算書（PL）

| 指標 | {years[0]} | {years[1]} | {years[2]} |
|------|------------|------------|------------|
| 売上高 | {_format_number(metrics['売上高'][0])} | {_format_number(metrics['売上高'][1])} | {_format_number(metrics['売上高'][2])} |
| 売上高成長率 | - | {metrics['売上高成長率'][1]}% | {metrics['売上高成長率'][2]}% |
| 営業利益 | {_format_number(metrics['営業利益'][0])} | {_format_number(metrics['営業利益'][1])} | {_format_number(metrics['営業利益'][2])} |
| 営業利益率 | {metrics['営業利益率'][0]}% | {metrics['営業利益率'][1]}% | {metrics['営業利益率'][2]}% |
| 当期純利益 | {_format_number(metrics['当期純利益'][0])} | {_format_number(metrics['当期純利益'][1])} | {_format_number(metrics['当期純利益'][2])} |

### 貸借対照表（BS）

| 指標 | {years[0]} | {years[1]} | {years[2]} |
|------|------------|------------|------------|
| 総資産 | {_format_number(metrics['総資産'][0])} | {_format_number(metrics['総資産'][1])} | {_format_number(metrics['総資産'][2])} |
| 純資産 | {_format_number(metrics['純資産'][0])} | {_format_number(metrics['純資産'][1])} | {_format_number(metrics['純資産'][2])} |
| 自己資本比率 | {metrics['自己資本比率'][0]}% | {metrics['自己資本比率'][1]}% | {metrics['自己資本比率'][2]}% |

### キャッシュフロー（CF）

| 指標 | {years[0]} | {years[1]} | {years[2]} |
|------|------------|------------|------------|
| 営業CF | {_format_number(metrics['営業CF'][0])} | {_format_number(metrics['営業CF'][1])} | {_format_number(metrics['営業CF'][2])} |
| 投資CF | {_format_number(metrics['投資CF'][0])} | {_format_number(metrics['投資CF'][1])} | {_format_number(metrics['投資CF'][2])} |
| 財務CF | {_format_number(metrics['財務CF'][0])} | {_format_number(metrics['財務CF'][1])} | {_format_number(metrics['財務CF'][2])} |
"""
    return text


def format_raw_data_as_markdown(company_df: pd.DataFrame) -> str:
    """
    財務データの生データをMarkdownテーブルに変換

    Args:
        company_df: 企業の財務データDataFrame

    Returns:
        Markdownテーブル形式のテキスト
    """
    # 主要な列を選択（LLMが参照しやすい項目）
    key_columns = [
        "YEAR",
        "売上高", "営業利益", "経常利益", "当期純利益",
        "総資産", "純資産",
        "営業活動によるキャッシュ・フロー",
        "投資活動によるキャッシュ・フロー",
        "財務活動によるキャッシュ・フロー",
        "現金及び現金同等物期末残高",
        "売上高_完成工事高", "売上高_不動産事業売上高", "売上高_商品売上高",
        "売上原価_完成工事原価",
        "販売費及び一般管理費",
        "有形固定資産",
        "流動資産", "流動負債",
        "固定負債_長期借入金",
    ]

    # 存在する列のみ抽出
    available_columns = [col for col in key_columns if col in company_df.columns]
    subset_df = company_df[available_columns].copy()

    # 列名を短縮
    rename_map = {
        "YEAR": "年度",
        "営業活動によるキャッシュ・フロー": "営業CF",
        "投資活動によるキャッシュ・フロー": "投資CF",
        "財務活動によるキャッシュ・フロー": "財務CF",
        "現金及び現金同等物期末残高": "現金残高",
        "売上高_完成工事高": "完成工事高",
        "売上高_不動産事業売上高": "不動産売上",
        "売上高_商品売上高": "商品売上",
        "売上原価_完成工事原価": "工事原価",
        "販売費及び一般管理費": "販管費",
        "固定負債_長期借入金": "長期借入金",
    }
    subset_df = subset_df.rename(columns=rename_map)

    # 数値をフォーマット
    for col in subset_df.columns:
        if col != "年度":
            subset_df[col] = subset_df[col].apply(
                lambda x: _format_number(x) if pd.notna(x) else "-"
            )

    # Markdownテーブルに変換
    markdown = "## 財務データ（生データ抜粋）\n\n"
    markdown += subset_df.to_markdown(index=False)

    return markdown
