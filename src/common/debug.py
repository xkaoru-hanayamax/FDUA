"""
デバッグユーティリティ

全フローで入出力を確認するためのログ機能
"""

import os
from pathlib import Path
from datetime import datetime

# デバッグモードの有効/無効
_debug_mode = False
_debug_log_path: Path | None = None


def set_debug_mode(enabled: bool, log_dir: str | None = None) -> None:
    """
    デバッグモードを設定

    Args:
        enabled: デバッグモードを有効にするかどうか
        log_dir: ログ出力先ディレクトリ（Noneの場合はoutput/debug）
    """
    global _debug_mode, _debug_log_path
    _debug_mode = enabled

    if enabled:
        if log_dir:
            base_dir = Path(log_dir)
        else:
            base_dir = Path("output/debug")
        base_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _debug_log_path = base_dir / f"debug_log_{timestamp}.txt"
        print(f"[DEBUG] デバッグモード有効: ログ出力先 {_debug_log_path}")


def is_debug_mode() -> bool:
    """デバッグモードが有効かどうか"""
    return _debug_mode or os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


def debug_log(step: str, message: str, data: str | None = None) -> None:
    """
    デバッグログを出力

    Args:
        step: 処理ステップ名
        message: メッセージ
        data: 追加データ（長いテキストなど）
    """
    if not is_debug_mode():
        return

    separator = "=" * 80
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"""
{separator}
[{timestamp}] {step}
{separator}
{message}
"""
    if data:
        log_entry += f"""
--- データ ---
{data[:5000]}{"... (truncated)" if len(data) > 5000 else ""}
"""

    # コンソールに出力
    print(log_entry)

    # ファイルにも出力
    if _debug_log_path:
        with open(_debug_log_path, "a", encoding="utf-8") as f:
            # ファイルにはフルデータを出力
            full_entry = f"""
{separator}
[{timestamp}] {step}
{separator}
{message}
"""
            if data:
                full_entry += f"""
--- データ ---
{data}
"""
            f.write(full_entry)


def debug_log_io(step: str, input_data: dict | str, output_data: dict | str) -> None:
    """
    入出力をデバッグログに出力

    Args:
        step: 処理ステップ名
        input_data: 入力データ
        output_data: 出力データ
    """
    if not is_debug_mode():
        return

    separator = "=" * 80
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 入力データを文字列に変換
    if isinstance(input_data, dict):
        input_str = "\n".join([f"  {k}: {_truncate_value(v)}" for k, v in input_data.items()])
    else:
        input_str = str(input_data)

    # 出力データを文字列に変換
    if isinstance(output_data, dict):
        output_str = "\n".join([f"  {k}: {_truncate_value(v)}" for k, v in output_data.items()])
    else:
        output_str = str(output_data)

    log_entry = f"""
{separator}
[{timestamp}] {step}
{separator}

【入力】
{input_str}

【出力】
{output_str}
"""

    # コンソールに出力
    print(log_entry)

    # ファイルにも出力
    if _debug_log_path:
        with open(_debug_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)


def _truncate_value(value, max_len: int = 500) -> str:
    """値を適切に切り詰めて文字列化"""
    if value is None:
        return "None"
    if isinstance(value, (list, tuple)):
        return f"[{len(value)} items]"
    if isinstance(value, dict):
        return f"{{dict with {len(value)} keys}}"
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + f"... ({len(s)} chars total)"
    return s


def debug_llm_call(section: str, prompt: str, response: str) -> None:
    """
    LLM呼び出しのログを出力

    Args:
        section: セクション名
        prompt: プロンプト
        response: レスポンス
    """
    if not is_debug_mode():
        return

    separator = "=" * 80
    sub_separator = "-" * 60
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"""
{separator}
[{timestamp}] LLM呼び出し: {section}
{separator}

【プロンプト】（{len(prompt)}文字）
{sub_separator}
{prompt[:3000]}{"... (truncated)" if len(prompt) > 3000 else ""}

【レスポンス】（{len(response)}文字）
{sub_separator}
{response[:3000]}{"... (truncated)" if len(response) > 3000 else ""}
"""

    print(log_entry)

    # ファイルには全文出力
    if _debug_log_path:
        with open(_debug_log_path, "a", encoding="utf-8") as f:
            full_entry = f"""
{separator}
[{timestamp}] LLM呼び出し: {section}
{separator}

【プロンプト】（{len(prompt)}文字）
{sub_separator}
{prompt}

【レスポンス】（{len(response)}文字）
{sub_separator}
{response}
"""
            f.write(full_entry)


def debug_docx_processing(original: str, cleaned: str) -> None:
    """
    DOCX出力時のMarkdown除去処理をログ出力

    Args:
        original: 元のテキスト
        cleaned: 除去後のテキスト
    """
    if not is_debug_mode():
        return

    if original != cleaned:
        print(f"[DEBUG] Markdown除去: '{original[:50]}...' -> '{cleaned[:50]}...'")

        if _debug_log_path:
            with open(_debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[Markdown除去]\n  前: {original}\n  後: {cleaned}\n")
