"""
財務データ読み込みモジュール

CSVファイルからの財務データ読み込み機能を提供
"""

from pathlib import Path
from typing import Union

import pandas as pd

from ..common.config import default_config


def load_financial_data(csv_path: Union[str, Path, None] = None) -> pd.DataFrame:
    """
    財務データをCSVから読み込む

    Args:
        csv_path: CSVファイルパス（Noneの場合はデフォルトパス）

    Returns:
        財務データのDataFrame
    """
    if csv_path is None:
        csv_path = default_config.financial_csv_path
    return pd.read_csv(csv_path)


def get_company_data(df: pd.DataFrame, code: int) -> pd.DataFrame:
    """
    指定企業のデータを抽出

    Args:
        df: 財務データ全体のDataFrame
        code: 企業コード（整数）

    Returns:
        指定企業のデータ（年度順にソート済み）
    """
    return df[df["コード"] == code].sort_values("YEAR")


def get_company_info(df: pd.DataFrame, code: int) -> dict:
    """
    企業の基本情報を取得

    Args:
        df: 財務データ全体のDataFrame
        code: 企業コード（整数）

    Returns:
        企業基本情報の辞書
    """
    company_df = get_company_data(df, code)
    if company_df.empty:
        return {}

    latest = company_df.iloc[-1]
    return {
        "code": str(code),
        "location": latest["本社所在地"],
        "industry": latest["業種分類"],
        "employees": int(latest["従業員数（連結）"]),
        "capital": float(latest["資本金（億円）"]),
    }
