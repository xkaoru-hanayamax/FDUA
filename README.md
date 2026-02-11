# 建設業向け事業提案システム

Snowflake Cortex LLMとTavily Search APIを活用して、建設業10社の財務データ・有価証券報告書・Web調査から成長戦略提案書を自動生成するシステム。

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
TAVILY_API_KEY=your_tavily_api_key
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
docker compose run --rm snowflake-llm python -m cli.run_agent --all

# 1社のみ生成
docker compose run --rm snowflake-llm python -m cli.run_agent --code 12044
```

出力:
- `data/proposals/{企業コード}.docx` - 提案書（10社分）
- `data/prompt_log.txt` - プロンプトログ

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

- **Web調査の統合**: Tavily Search APIで企業ごとに地域特性・業界動向・GX/DX・人材市場の最新情報を自動収集し、全セクションの生成コンテキストに活用
- **セクション見出しテンプレート**: `SECTION_HEADING_TEMPLATES`で5セクションの`##`/`###`見出し構造を定義し、全10社で統一した章立てを保証
- **二段階の文字数制御**: 各セクション生成では目安文字数のみ提示し、最終統合処理（`check_and_truncate`）で総文字数13,000字以内を厳守
- **評価基準の組み込み**: コンペの評価基準（地域性、業界特性、GX/DX対応等）をプロンプトに明示的に組み込み
- **セクション間の論理的接続**: 「過去分析→課題→未来提案」の一貫した因果関係を維持

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
│ web_research │  Tavily APIによるWeb調査
└──────┬───────┘
       │
       ▼
┌──────────────┐
│extract_issues│  課題抽出（Web調査結果も活用）
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
│check_and_truncate│  全体統合・品質向上・文字数調整
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

#### 2. web_research（Web調査）

| 項目 | 内容 |
|------|------|
| **入力** | `company_info`, `financial_markdown`, `securities_markdown` |
| **処理** | LLMが企業情報を分析して5つの検索クエリを生成（地域特性・業界特性・GX・DX・人材の5観点）。Tavily APIで`search_depth="advanced"`, `include_answer="advanced"`により検索実行。AI要約付き結果を取得 |
| **出力** | `search_queries`, `research_results`, `is_info_sufficient` |

#### 3. extract_issues（課題抽出）

| 項目 | 内容 |
|------|------|
| **入力** | `financial_markdown`, `securities_markdown`, `company_info`, `research_results` |
| **処理** | 1回のLLM呼び出しで財務・有報・Web調査結果から課題を統合抽出（JSON形式で出力をパース、カテゴリ別分類・重要度ソート） |
| **出力** | `issues`（課題リスト、重要度順）, `prompt_logs` |

#### 4. generate_overview（企業概要・分析）

| 項目 | 内容 |
|------|------|
| **入力** | `financial_markdown`, `securities_markdown`, `research_results`, `company_info`, `EVALUATION_CRITERIA`, `SECTION_HEADING_TEMPLATES["overview"]` |
| **処理** | LLMで企業概要・外部環境・財務分析を生成（目安2,800字、見出しテンプレートに準拠） |
| **出力** | `sections["overview"]` |

#### 5. generate_issues（課題の抽出）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["overview"]`, `research_results`, `company_info`, `EVALUATION_CRITERIA`, `SECTION_HEADING_TEMPLATES["issues"]` |
| **処理** | 前セクション（overview）を参照し、論理的に接続した課題セクションを生成（目安2,300字、見出しテンプレートに準拠） |
| **出力** | `sections["issues"]` |

#### 6. generate_strategy（成長戦略・提案）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["issues"]`, `research_results`, `company_info`, `EVALUATION_CRITERIA`, `SECTION_HEADING_TEMPLATES["strategy"]` |
| **処理** | 課題から論理的に導かれる成長戦略を生成（目安3,200字、見出しテンプレートに準拠） |
| **出力** | `sections["strategy"]` |

#### 7. generate_effects（効果試算）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["strategy"]`, `sections["overview"]`, `research_results`, `EVALUATION_CRITERIA`, `SECTION_HEADING_TEMPLATES["effects"]` |
| **処理** | 戦略の定量・定性効果を試算（目安1,800字、見出しテンプレートに準拠、総合効果サマリー必須） |
| **出力** | `sections["effects"]` |

#### 8. generate_roadmap（ロードマップ）

| 項目 | 内容 |
|------|------|
| **入力** | `issues`, `sections["strategy"]`, `research_results`, `EVALUATION_CRITERIA`, `SECTION_HEADING_TEMPLATES["roadmap"]` |
| **処理** | 3フェーズの実行計画・マイルストーン・推進体制を生成（目安1,800字、見出しテンプレートに準拠） |
| **出力** | `sections["roadmap"]` |

#### 9. check_and_truncate（全体統合・品質向上・文字数調整）

| 項目 | 内容 |
|------|------|
| **入力** | `sections`（全5セクション） |
| **処理** | 5セクションをマークダウン形式で統合し、1回のLLM呼び出しで品質向上（用語統一・冗長削除・論理接続強化・重複排除）と文字数調整（総文字数13,000字以内厳守）を実行。見出しテンプレートも統合プロンプトに埋め込み、章立て統一を二重保証 |
| **出力** | `sections`（調整済み）, `section_char_counts` |

#### 10. write_docx（DOCX出力）

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
│   ├── constants.py               # 定数定義（見出しテンプレート、文字数目安、評価基準等）
│   ├── config.py                  # パス設定・Config管理
│   └── debug.py                   # デバッグログ出力
│
├── graph/
│   ├── __init__.py                # パッケージエクスポート
│   ├── proposal_agent.py          # メインエージェント（10ノード直線フロー）
│   │
│   ├── states/                    # 状態クラス
│   │   └── proposal_state.py      # ProposalAgentState, Issue
│   │
│   ├── nodes/                     # ノード
│   │   ├── load_data.py           # データ読み込み
│   │   ├── web_research.py        # Tavily APIによるWeb調査
│   │   ├── extract_issues.py      # 課題抽出（LLM呼び出し・JSON解析）
│   │   ├── sections.py            # セクション生成（5セクション、見出しテンプレート適用）
│   │   ├── truncation.py          # 全体統合・品質向上・文字数調整
│   │   └── output.py              # DOCX出力
│   │
│   └── edges/
│       └── conditionals.py        # 条件分岐（将来の拡張用）
│
├── proposal/
│   ├── docx_writer.py             # マークダウン→DOCX変換
│   ├── context_builder.py         # 財務・有報データ読み込み
│   └── pdf_loader.py              # 有価証券報告書PDF解析
│
├── financial/
│   ├── loader.py                  # 財務CSV読み込み
│   ├── analyzer.py                # 財務指標計算
│   └── metrics.py                 # 財務比率定義
│
└── llm/
    └── snowflake_client.py        # LLM APIクライアント（Claude Sonnet 4.5）
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

### セクション見出しテンプレート

`constants.py`の`SECTION_HEADING_TEMPLATES`で各セクションの見出し構造を定義。全10社で統一された章立てを保証する。

| セクション | ## 大見出し |
|-----------|------------|
| overview | 企業概要 / 外部環境分析 / 財務情報分析 |
| issues | 財務面の課題 / 事業面の課題 / 人材・組織面の課題 |
| strategy | 短期施策（1年以内） / 中期施策（1-3年） / 長期施策（3-5年） |
| effects | 定量効果 / 定性的効果 / 総合効果サマリー |
| roadmap | 実行計画 / マイルストーン / 推進体制 |

見出しルール（`HEADING_RULES`）:
- `##` で大見出し、`###` で中見出し（`####` 以下は禁止）
- 見出しに番号（1. 2. 等）を付けない
- `##` のテキストはテンプレート通り固定、`###` は企業固有に置き換え可

適用箇所:
1. `sections.py` — 各セクション生成プロンプトにテンプレートを埋め込み（一次生成で統一）
2. `truncation.py` — 統合プロンプトにもテンプレートを埋め込み（二重防御）

### 文字数制御

| 制御段階 | ファイル | 方式 |
|---------|---------|------|
| セクション生成時 | `sections.py` | 目安として提示（`約○○字を目安に`） |
| 全体統合時 | `truncation.py` | 厳守（`総文字数13,000字以内・超過不可`） |

セクション別の目安文字数（`SECTION_CHAR_LIMITS`）:
- 企業概要・分析: 約2,800字
- 課題の抽出: 約2,300字
- 成長戦略・提案: 約3,200字
- 効果試算: 約1,800字
- ロードマップ: 約1,800字

LLMによるセクション個別の圧縮リトライは行わず、最終統合プロンプト1回で全体の文字数制御と品質向上を完結させる。

## LangGraph Studio（開発・デバッグ用）

LangGraph StudioはLangGraphエージェントの可視化・デバッグツールです。グラフの実行状態をリアルタイムで確認できます。

### 起動方法

```bash
# LangGraph Studioを起動
docker compose up langgraph-studio
```

起動後、以下のURLにアクセス：

| URL | 説明 |
|-----|------|
| http://localhost:8123 | API エンドポイント |
| http://localhost:8123/docs | API ドキュメント（Swagger UI） |
| https://smith.langchain.com/studio/?baseUrl=http://localhost:8123 | Studio UI（Web版） |

### Studio UIの使い方

1. ブラウザで `https://smith.langchain.com/studio/?baseUrl=http://localhost:8123` を開く
2. LangSmithアカウントでログイン（必要な場合）
3. 左側のグラフ一覧から `proposal_agent` を選択
4. 「New Thread」でスレッドを作成
5. 入力に以下のJSON形式で企業コードを指定して実行：

```json
{
  "company_code": "12044"
}
```

### 主な機能

- **グラフ可視化**: ノード間の接続とフローを視覚的に確認
- **ステップ実行**: 各ノードの入出力をリアルタイムで確認
- **状態確認**: 実行中のstate（財務データ、課題リスト、生成セクション等）を閲覧
- **デバッグ**: エラー発生時のスタックトレースと状態を確認

### 停止方法

```bash
# Ctrl+C で停止、または別ターミナルで
docker compose down langgraph-studio
```
