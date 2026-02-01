# 建設業向け事業提案システム

Snowflake Cortex LLMを活用して、建設業10社の財務データと有価証券報告書から成長戦略提案書を自動生成するシステム。

## 構造

```
src/          # モジュール（llm, financial, proposal, common）
cli/          # CLIコマンド
data/         # データファイル（財務CSV, PDF, 出力）
```

## セットアップ

### 1. 環境変数の設定

`.env` ファイルを作成：

```env
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

### 2. データファイルの配置

`data/` ディレクトリに以下を配置：

- `financial_data.csv` - 財務データ
- `有価証券報告書（{企業コード}）.pdf` - 各社の有価証券報告書（10社分）

※ PDFファイルは `cli.convert_pdf` でMarkdown形式に変換して使用

### 3. Dockerビルド

```bash
docker compose build
```

## 実行方法

### Step 1: PDF→Markdown変換（初回のみ）

有価証券報告書PDFをdoclingでMarkdown形式に変換：

```bash
# 全10社を変換
docker compose run --rm snowflake-llm python -m cli.convert_pdf --all

# 1社のみ変換
docker compose run --rm snowflake-llm python -m cli.convert_pdf --code 12044
```

出力: `data/有価証券報告書（{企業コード}）.md`

### Step 2: 財務分析

```bash
# 全10社を分析
docker compose run --rm snowflake-llm python -m cli.analyze_financial --all

# 1社のみ分析
docker compose run --rm snowflake-llm python -m cli.analyze_financial 12044
```

出力: `data/output/{企業コード}_summary.txt`

### Step 3: 提案書生成

```bash
# 全10社の提案書を生成
docker compose run --rm snowflake-llm python -m cli.generate_proposal --all

# 1社のみ生成
docker compose run --rm snowflake-llm python -m cli.generate_proposal 12044
```

出力: `data/proposals/{企業コード}.docx`

## 一括実行（推奨）

財務分析→提案書生成を一括実行し、プロンプトログを保存：

```bash
# 事前にPDF変換を実行（初回のみ）
docker compose run --rm snowflake-llm python -m cli.convert_pdf --all

# 一括実行
docker compose run --rm snowflake-llm python -m cli.run_all
```

出力：
- `data/有価証券報告書（{企業コード}）.md` - 変換済みMarkdown（10社分）
- `data/proposals/{企業コード}.docx` - 提案書（10社分）
- `data/prompt_log.txt` - 全プロンプトログ

## CLIオプション

各CLIには `--help` でオプションを確認可能：

```bash
docker compose run --rm snowflake-llm python -m cli.analyze_financial --help
```

主なオプション：
- `--all` : 全10社を処理
- `--data-dir` : データディレクトリ指定（デフォルト: `/app/data`）
- `--no-save` : ファイル出力なし

## 対象企業

| コード | 所在地 | 業種 |
|--------|--------|------|
| 12044 | 茨城 | 総合建設・土木 |
| 71768 | 高知県 | ホールディングス・多角化 |
| 73617 | 岡山県 | 住宅・ハウスメーカー |
| 99702 | 滋賀県 | 道路・基礎・インフラ |
| 141634 | 和歌山県 | 道路・基礎・インフラ |
| 184226 | 岩手県 | 専門工事 |
| 244359 | 静岡県 | 総合建設・土木 |
| 292640 | 北海道 | 専門工事 |
| 308582 | 宮崎県 | 環境・エネルギー関連 |
| 325042 | 新潟県 | 専門工事 |
