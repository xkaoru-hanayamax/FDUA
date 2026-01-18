"""
Snowflake Cortex LLM クライアントモジュール

Snowflake Cortexへの接続とLLM呼び出し機能を提供
"""

import os
from typing import Optional

from ..common.constants import DEFAULT_LLM_MODEL, DEFAULT_CROSS_REGION


def get_snowflake_connection():
    """
    Snowflake接続を取得

    環境変数から接続情報を読み込んで接続を確立する

    Returns:
        Snowflake接続オブジェクト

    Raises:
        snowflake.connector.Error: 接続エラー時
    """
    import snowflake.connector

    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    return conn


def call_cortex_llm(
    prompt: str,
    model: Optional[str] = None,
    region: Optional[str] = None,
) -> str:
    """
    Snowflake Cortex LLMを呼び出す

    Args:
        prompt: LLMに送るプロンプト
        model: 使用するモデル名 (claude-sonnet-4-5, llama3.1-70b, etc.)
        region: クロスリージョン推論のリージョン (AWS_APJ, AWS_US, AWS_EU, ANY_REGION, etc.)

    Returns:
        LLMからの応答テキスト

    Raises:
        Exception: LLM呼び出しエラー時
    """
    if model is None:
        model = DEFAULT_LLM_MODEL
    if region is None:
        region = DEFAULT_CROSS_REGION

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # クロスリージョン推論を有効化（ACCOUNTADMINロールが必要）
        cursor.execute(f"ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = '{region}'")

        escaped_prompt = prompt.replace("'", "''")
        query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            '{model}',
            '{escaped_prompt}'
        ) AS response
        """
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0] if result else ""
    finally:
        cursor.close()
        conn.close()


def test_connection() -> bool:
    """
    Snowflake Cortex LLM 接続テスト

    Returns:
        テスト成功時True、失敗時False
    """
    print("Snowflake Cortex LLM 接続テスト開始...")
    try:
        response = call_cortex_llm("こんにちは。一言で返答してください。")
        print(f"応答: {response}")
        print("テスト成功")
        return True
    except Exception as e:
        print(f"エラー: {e}")
        return False
