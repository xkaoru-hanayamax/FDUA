"""
Snowflake Cortex LLM クライアントモジュール

Snowflake Cortexへの接続とLLM呼び出し機能を提供
"""

import json
import os
from typing import Optional

from ..common.constants import DEFAULT_LLM_MODEL, DEFAULT_CROSS_REGION, DEFAULT_MAX_TOKENS


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
    max_tokens: Optional[int] = None,
) -> str:
    """
    Snowflake Cortex LLMを呼び出す

    Args:
        prompt: LLMに送るプロンプト
        model: 使用するモデル名 (claude-sonnet-4-5, llama3.1-70b, etc.)
        region: クロスリージョン推論のリージョン (AWS_APJ, AWS_US, AWS_EU, ANY_REGION, etc.)
        max_tokens: 最大出力トークン数

    Returns:
        LLMからの応答テキスト

    Raises:
        Exception: LLM呼び出しエラー時
    """
    if model is None:
        model = DEFAULT_LLM_MODEL
    if region is None:
        region = DEFAULT_CROSS_REGION
    if max_tokens is None:
        max_tokens = DEFAULT_MAX_TOKENS

    conn = get_snowflake_connection()
    cursor = conn.cursor()

    try:
        # クロスリージョン推論を有効化（ACCOUNTADMINロールが必要）
        cursor.execute(f"ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = '{region}'")

        messages = [{"role": "user", "content": prompt}]
        options = {"max_tokens": max_tokens}
        messages_json = json.dumps(messages, ensure_ascii=False)
        options_json = json.dumps(options)
        query = """
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            %s,
            PARSE_JSON(%s),
            PARSE_JSON(%s)
        ) AS response
        """
        cursor.execute(query, (model, messages_json, options_json))
        result = cursor.fetchone()
        if not result or not result[0]:
            return ""
        response = json.loads(result[0])
        choice = response.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason", "")
        if finish_reason == "length":
            print(f"[WARNING] LLM出力がmax_tokens上限に到達し途中で打ち切られました (max_tokens={max_tokens})")
        return choice.get("messages", "")
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
