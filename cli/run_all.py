"""
全体一括実行CLI

全ステップ（財務分析→提案書生成）を実行し、
プロンプトログをタイムスタンプ付きで保存する。

NOTE: ベクトルDB構築とRAG要約ステップは廃止済み。
      PDF全文を直接LLMに入力する方式に移行。

使用方法:
    python -m cli.run_all
"""

import argparse
from datetime import datetime
from pathlib import Path

from src.common import COMPANY_CODES, PROPOSAL_MAX_CHARS, Config
from src.financial import FinancialAnalyzer
from src.proposal import ContextBuilder, SectionGenerator, DocxWriter


def run_all(config: Config) -> dict:
    """
    全ステップを実行

    Args:
        config: 設定オブジェクト

    Returns:
        結果サマリー
    """
    all_prompt_logs = []  # 全プロンプトログを収集
    results = {code: {} for code in COMPANY_CODES}

    # ========================================
    # Step 1: 財務分析
    # ========================================
    print("\n" + "=" * 80)
    print("Step 1/2: 財務分析")
    print("=" * 80)

    for code in COMPANY_CODES:
        try:
            print(f"\n[{code}] 財務分析中...")
            analyzer = FinancialAnalyzer(config=config)
            analyzer.analyze(code, save_output=True)

            # プロンプトログ収集
            for log in analyzer.get_prompt_logs():
                all_prompt_logs.append({
                    "step": "財務分析",
                    "company_code": code,
                    **log
                })

            results[code]["financial"] = "成功"
        except Exception as e:
            print(f"[{code}] エラー: {e}")
            results[code]["financial"] = f"失敗: {e}"

    # ========================================
    # Step 2: 提案書生成
    # ========================================
    print("\n" + "=" * 80)
    print("Step 2/2: 提案書生成")
    print("=" * 80)

    for code in COMPANY_CODES:
        try:
            print(f"\n[{code}] 提案書生成中...")

            # コンテキスト構築
            context_builder = ContextBuilder(config=config)
            context_builder.load_all(code)

            # セクション生成
            section_generator = SectionGenerator(context_builder)
            sections = section_generator.generate_all()

            # プロンプトログ収集
            for log in section_generator.get_prompt_logs():
                all_prompt_logs.append({
                    "step": "提案書生成",
                    "company_code": code,
                    **log
                })

            # DOCX出力
            docx_writer = DocxWriter(config=config)
            company_info = context_builder.get_company_info() or {}

            char_count = docx_writer.count_characters(code, company_info, sections)
            print(f"  文字数: {char_count:,}字")

            # 文字数超過チェック
            if char_count > PROPOSAL_MAX_CHARS:
                raise ValueError(
                    f"文字数が{PROPOSAL_MAX_CHARS:,}字を超過しています（{char_count:,}字）。"
                    f"超過: {char_count - PROPOSAL_MAX_CHARS:,}字"
                )

            docx_writer.save_docx(code, company_info, sections)
            results[code]["proposal"] = "成功"

        except Exception as e:
            print(f"[{code}] エラー: {e}")
            import traceback
            traceback.print_exc()
            results[code]["proposal"] = f"失敗: {e}"

    return results, all_prompt_logs


def save_prompt_log(all_prompt_logs: list[dict], config: Config) -> str:
    """
    プロンプトログを保存

    Args:
        all_prompt_logs: 全プロンプトログ
        config: 設定オブジェクト

    Returns:
        保存したファイルパス
    """
    output_path = config.data_dir / "prompt_log.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"プロンプトログ - 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        current_step = None
        current_company = None
        log_index = 0

        for log in all_prompt_logs:
            # ステップが変わったらヘッダー出力
            if log["step"] != current_step:
                current_step = log["step"]
                f.write("\n" + "#" * 80 + "\n")
                f.write(f"# {current_step}\n")
                f.write("#" * 80 + "\n\n")

            # 企業が変わったらサブヘッダー出力
            if log["company_code"] != current_company:
                current_company = log["company_code"]
                log_index = 0
                f.write(f"\n{'=' * 60}\n")
                f.write(f"企業コード: {current_company}\n")
                f.write(f"{'=' * 60}\n\n")

            log_index += 1

            # クエリまたはセクション名
            label = log.get("query") or log.get("section", "")
            f.write(f"[{log_index}] {label}\n")
            f.write("-" * 60 + "\n")
            f.write("【入力プロンプト】\n")
            f.write(log["prompt"] + "\n\n")
            f.write("【LLM出力】\n")
            f.write(log["response"] + "\n")
            f.write("\n" + "-" * 60 + "\n\n")

    print(f"\nプロンプトログを保存しました: {output_path}")
    return str(output_path)


def print_summary(results: dict):
    """結果サマリーを表示"""
    print("\n" + "=" * 80)
    print("処理結果サマリー")
    print("=" * 80)
    print(f"{'企業コード':<12} {'財務分析':<12} {'提案書':<12}")
    print("-" * 36)

    for code, result in results.items():
        financial = "OK" if result.get("financial") == "成功" else "NG"
        proposal = "OK" if result.get("proposal") == "成功" else "NG"
        print(f"{code:<12} {financial:<12} {proposal:<12}")

    # 成功数カウント
    total = len(COMPANY_CODES)
    success_counts = {
        "financial": sum(1 for r in results.values() if r.get("financial") == "成功"),
        "proposal": sum(1 for r in results.values() if r.get("proposal") == "成功"),
    }

    print("-" * 36)
    print(f"{'合計':<12} {success_counts['financial']}/{total:<9} {success_counts['proposal']}/{total:<9}")


def main():
    parser = argparse.ArgumentParser(
        description="全ステップを一括実行（財務分析→提案書生成）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    python -m cli.run_all                # 全ステップ実行
        """,
    )
    parser.add_argument(
        "--data-dir",
        default="/app/data",
        help="データディレクトリ (default: /app/data)",
    )

    args = parser.parse_args()

    config = Config(data_dir=args.data_dir)

    print("=" * 80)
    print("全体一括実行開始")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 実行
    results, all_prompt_logs = run_all(config)

    # プロンプトログ保存
    if all_prompt_logs:
        save_prompt_log(all_prompt_logs, config)

    # サマリー表示
    print_summary(results)

    print(f"\n終了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
