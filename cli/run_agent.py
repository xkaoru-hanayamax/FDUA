"""
LangGraphエージェント実行CLI

提案書生成エージェントを実行する
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

from src.graph import run_proposal_agent
from src.common.constants import COMPANY_CODES
from src.common.config import Config


def save_prompt_log(
    prompt_logs: list[dict],
    company_code: str,
    config: Config,
) -> str:
    """
    プロンプトログをファイルに保存

    Args:
        prompt_logs: プロンプトログのリスト
        company_code: 企業コード
        config: 設定オブジェクト

    Returns:
        保存先パス
    """
    output_path = config.get_prompt_log_path()

    # 追記モードで保存
    mode = "a" if output_path.exists() else "w"

    with open(output_path, mode, encoding="utf-8") as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"企業コード: {company_code} - エージェント実行ログ\n")
        f.write(f"{'='*80}\n\n")

        for i, log in enumerate(prompt_logs, 1):
            step = log.get("step") or log.get("section", "不明")
            f.write(f"[{i}] ステップ: {step}\n")
            f.write("-" * 60 + "\n")
            f.write("【入力プロンプト】\n")
            f.write(log.get("prompt", "") + "\n\n")
            f.write("【LLM出力】\n")
            f.write(log.get("response", "") + "\n")
            f.write("\n" + "=" * 60 + "\n\n")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="LangGraphベースの提案書生成エージェントを実行"
    )
    parser.add_argument(
        "--code",
        type=str,
        help="企業コード（例: 12044）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="全企業を処理",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="データディレクトリパス",
    )
    parser.add_argument(
        "--save-log",
        action="store_true",
        default=True,
        help="プロンプトログを保存（デフォルト: True）",
    )

    args = parser.parse_args()

    # 引数チェック
    if not args.code and not args.all:
        parser.error("--code または --all を指定してください")

    # 処理対象企業コード
    if args.all:
        codes = COMPANY_CODES
    else:
        codes = [args.code]

    # Config
    config = Config(data_dir=args.data_dir) if args.data_dir else Config()

    # 実行
    for code in codes:
        print(f"\n{'#'*60}")
        print(f"# 企業コード: {code}")
        print(f"{'#'*60}\n")

        try:
            result = run_proposal_agent(
                company_code=code,
                data_dir=args.data_dir,
            )

            # 結果表示
            print("\n--- 実行結果 ---")
            print(f"企業コード: {result['company_code']}")
            print(f"企業情報: {result['company_info']}")
            print(f"抽出された課題: {len(result['issues'])}件")
            print(f"調査結果: {len(result['research_results'])}カテゴリ")
            print(f"知見: {len(result['insights'])}件")
            print(f"出力ファイル: {result['output_path']}")
            print(f"総文字数: {result['total_chars']}字")

            if result['errors']:
                print(f"エラー: {result['errors']}")

            # セクション別文字数
            print("\n--- セクション別文字数 ---")
            for section, count in result['section_char_counts'].items():
                print(f"  {section}: {count}字")

            # プロンプトログ保存
            if args.save_log and result['prompt_logs']:
                log_path = save_prompt_log(
                    result['prompt_logs'],
                    code,
                    config,
                )
                print(f"\nプロンプトログ: {log_path}")

        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("\n処理完了")


if __name__ == "__main__":
    main()
