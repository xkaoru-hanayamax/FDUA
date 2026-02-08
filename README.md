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

出力: `data/output/{企業コード}_securities.md`

### Step 2: 財務分析

```bash
# 全10社を分析
docker compose run --rm snowflake-llm python -m cli.analyze_financial --all

# 1社のみ分析
docker compose run --rm snowflake-llm python -m cli.analyze_financial 12044
```

出力: `data/output/{企業コード}_financial.md`

財務分析結果には以下が含まれます：
- 計算済み財務指標（成長率、利益率、自己資本比率など）
- 財務データ生データ（Markdownテーブル）
- LLM分析要約

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
- `data/output/{企業コード}_securities.md` - 有価証券報告書Markdown（10社分）
- `data/output/{企業コード}_financial.md` - 財務分析結果Markdown（10社分）
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

## LangGraphエージェントシステム

LangGraphを使用したエージェントベースの提案書生成システム。直線フローで財務・有報データから提案書を自動生成します。

### 特徴

- **評価基準の組み込み**: コンペの評価基準（地域性、業界特性、GX/DX対応等）をプロンプトに明示的に組み込み
- **セクション間の論理的接続**: 「過去分析→課題→未来提案」の一貫した因果関係を維持
- **統合的な課題抽出**: 財務データと有報を1回のLLM呼び出しで一貫分析

### 実行方法

```bash
# 1社の提案書を生成
docker compose run --rm snowflake-llm python -m cli.run_agent --code 12044

# 全10社を生成
docker compose run --rm snowflake-llm python -m cli.run_agent --all

# デバッグモード（プロンプトログ出力）
docker compose run --rm snowflake-llm python -m cli.run_agent --code 12044 --debug
```

### グラフ構造と各ノードの入出力

```
┌─────────────┐
│    START    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  load_data  │  財務・有報Markdown読み込み
└──────┬──────┘
       │
       ▼
┌──────────────┐
│extract_issues│  課題抽出
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│generate_overview│  セクション1: 企業概要・分析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ generate_issues │  セクション2: 課題の抽出
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│generate_strategy│  セクション3: 成長戦略・提案
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ generate_effects│  セクション4: 効果試算
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ generate_roadmap│  セクション5: ロードマップ
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│check_and_truncate│  文字数チェック・調整
└────────┬─────────┘
         │
         ▼
┌──────────┐
│write_docx│  DOCX出力
└────┬─────┘
     │
     ▼
┌──────────┐
│   END    │
└──────────┘
```

### 各ノードの詳細

#### 1. load_data（データ読み込み）

| 項目 | 内容 |
|------|------|
| **入力** | `company_code`（企業コード） |
| **処理** | 財務分析Markdown・有報Markdownをファイルから読み込み |
| **出力** | `financial_markdown`, `securities_markdown`, `company_info` |

#### 2. extract_issues（課題抽出）

| 項目 | 内容 |
|------|------|
| **入力** | `financial_markdown`, `securities_markdown`, `company_info` |
| **処理** | 1回のLLM呼び出しで財務・有報から課題を統合抽出（JSON形式で出力をパース、カテゴリ別分類・重要度ソート） |
| **出力** | `issues`（課題リスト、重要度順）, `prompt_logs` |

#### 3. generate_overview（企業概要・分析）

| 項目 | 内容 |
|------|------|
| **入力** | `financial_markdown`, `securities_markdown`, `company_info`, `EVALUATION_CRITERIA` |
| **処理** | LLMで企業概要・外部環境・財務分析を生成（上限2,800字） |
| **出力** | `sections["overview"]` |

#### 4. generate_issues（課題の抽出）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["overview"]`, `company_info`, `EVALUATION_CRITERIA` |
| **処理** | 前セクション（overview）を参照し、論理的に接続した課題セクションを生成（上限2,300字） |
| **出力** | `sections["issues"]` |

#### 5. generate_strategy（成長戦略・提案）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["issues"]`, `company_info`, `EVALUATION_CRITERIA` |
| **処理** | 課題から論理的に導かれる成長戦略を生成（上限3,200字） |
| **出力** | `sections["strategy"]` |

#### 6. generate_effects（効果試算）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["strategy"]`, `financial_markdown`, `EVALUATION_CRITERIA` |
| **処理** | 戦略の定量・定性効果を試算（上限1,800字） |
| **出力** | `sections["effects"]` |

#### 7. generate_roadmap（ロードマップ）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["strategy"]`, `EVALUATION_CRITERIA` |
| **処理** | 5年間の実行計画・マイルストーンを生成（上限1,800字） |
| **出力** | `sections["roadmap"]` |

#### 8. check_and_truncate（文字数調整）

| 項目 | 内容 |
|------|------|
| **入力** | `sections`（全5セクション） |
| **処理** | 合計15,000字以内に収まるよう必要に応じてLLMで要約 |
| **出力** | `sections`（調整済み）, `total_char_count` |

#### 9. write_docx（DOCX出力）

| 項目 | 内容 |
|------|------|
| **入力** | `sections`, `company_code` |
| **処理** | python-docxで提案書を生成 |
| **出力** | `data/proposals/{企業コード}.docx` |

### 評価基準の組み込み

全セクション生成時に以下の評価基準がプロンプトに含まれます（`EVALUATION_CRITERIA`定数）:

```
1. 過去3年の分析と未来提案が論理的に接続していること
2. 地域特性を踏まえた具体的な分析・提案であること
3. 官公庁/民間、元請/下請の販路・商流を理解した内容であること
4. GX（環境技術、脱炭素）・DX（ICT施工、BIM/CIM）への対応を含むこと
5. 人材不足・2024年問題・需要変化への対応策を含むこと
```

### ファイル構成

```
src/
├── common/
│   ├── constants.py               # 定数定義（EVALUATION_CRITERIA等）
│   └── debug.py                   # デバッグログ出力
│
├── graph/
│   ├── __init__.py                # パッケージエクスポート
│   ├── proposal_agent.py          # メインエージェント（直線フロー）
│   │
│   ├── states/                    # 状態クラス
│   │   └── proposal_state.py      # ProposalAgentState, Issue
│   │
│   ├── nodes/                     # ノード
│   │   ├── load_data.py           # データ読み込み
│   │   ├── extract_issues.py      # 課題抽出（LLM呼び出し・JSON解析）
│   │   ├── sections.py            # セクション生成（5セクション）
│   │   ├── truncation.py          # 文字数制御
│   │   └── output.py              # DOCX出力
│   │
│   └── edges/
│       └── conditionals.py        # 条件分岐（将来の拡張用）
│
└── proposal/
    └── docx_writer.py             # DOCX出力処理
```

### 状態管理

LangGraphの`Annotated`型を使用してリデューサー関数を定義し、ノードからの状態更新を自動マージ：

```python
# 例: prompt_logsは各ノードから返されたリストが自動的に結合される
prompt_logs: Annotated[list[dict], merge_lists]

# 例: research_resultsは各調査ノードの結果が自動的にマージされる
research_results: Annotated[dict[str, str], merge_dicts]
```

### セクション間の依存関係

各セクションは前セクションの内容を参照し、論理的な接続を維持します：

```
overview（企業概要・分析）
    ↓ 参照
issues（課題の抽出）← overviewの分析結果を踏まえて課題を導出
    ↓ 参照
strategy（成長戦略）← issuesから論理的に導かれる戦略を提案
    ↓ 参照
effects（効果試算）← strategyの施策に対する効果を試算
    ↓ 参照
roadmap（ロードマップ）← strategyの施策を時系列で配置
```
