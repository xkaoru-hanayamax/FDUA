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

## LangGraphエージェントシステム（実験的）

LangGraphを使用したエージェントベースの提案書生成システム。メインエージェント＋サブエージェント構造で、情報の十分性を判定しながら動的に調査・生成を行います。

### 実行方法

```bash
# 1社の提案書を生成
docker compose run --rm snowflake-llm python -m cli.run_agent --code 12044

# 全10社を生成
docker compose run --rm snowflake-llm python -m cli.run_agent --all
```

### グラフ構造

#### メインエージェント（Orchestrator）

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
                        ┌───────────────┐
                        │extract_issues │  課題抽出エージェント呼び出し
                        └───────┬───────┘
                                │
                                ▼
                        ┌───────────────┐
                        │ organize_info │  情報整理エージェント呼び出し
                        └───────┬───────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │check_sufficiency │  情報十分性をLLMで判定
                      └────────┬─────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼ 不足                ▼ 十分
             ┌─────────────┐       ┌────────────────┐
             │web_research │       │ gen_overview   │
             └──────┬──────┘       └───────┬────────┘
                    │                      │
                    └──────────┬───────────┘
                               ▼
                        ┌─────────────┐
                        │ gen_issues  │  セクション2: 課題の抽出
                        └──────┬──────┘
                               ▼
                       ┌──────────────┐
                       │ gen_strategy │  セクション3: 成長戦略・提案
                       └──────┬───────┘
                              ▼
                       ┌─────────────┐
                       │ gen_effects │  セクション4: 効果試算
                       └──────┬──────┘
                              ▼
                       ┌─────────────┐
                       │ gen_roadmap │  セクション5: ロードマップ
                       └──────┬──────┘
                              ▼
                    ┌──────────────────┐
                    │check_and_truncate│  文字数チェック・短縮
                    └────────┬─────────┘
                             │
                  ┌──────────┴──────────┐
                  ▼ 再調査必要          ▼ OK
           ┌─────────────┐       ┌─────────────┐
           │organize_info│       │ write_docx  │  DOCX出力
           └─────────────┘       └──────┬──────┘
                                        ▼
                                 ┌─────────────┐
                                 │     END     │
                                 └─────────────┘
```

#### サブエージェント構造

```
┌─────────────────────────────────────────────────────────────────┐
│                    メインエージェント（Orchestrator）             │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 課題抽出        │ │ 情報整理        │ │ Web調査         │
│ エージェント    │ │ エージェント    │ │ エージェント    │
│ (IssueExtractor)│ │ (InfoOrganizer) │ │ (WebResearcher) │
│                 │ │                 │ │                 │
│ ・財務分析      │ │ ・必要情報特定  │ │ ・業界動向      │
│ ・有報分析      │ │ ・不足情報整理  │ │ ・地域特性      │
│ ・課題統合      │ │ ・検索クエリ生成│ │ ・技術トレンド  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

#### 課題抽出エージェント（IssueExtractor）

財務データと有価証券報告書を**並列分析**して課題を抽出。

```
        ┌───────────┐
        │   START   │
        └─────┬─────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌───────────────┐ ┌───────────────┐
│analyze_finance│ │analyze_securit│  ← 並列実行
└───────┬───────┘ └───────┬───────┘
        │                 │
        └────────┬────────┘
                 ▼
        ┌────────────────┐
        │integrate_issues│  課題を統合・分類
        └────────┬───────┘
                 ▼
           ┌─────────┐
           │   END   │
           └─────────┘
```

#### Web調査エージェント（WebResearcher）

3つの調査を**並列実行**して知見を統合。

```
              ┌───────────┐
              │   START   │
              └─────┬─────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌────────┐    ┌──────────┐    ┌──────────┐
│industry│    │ regional │    │   tech   │  ← 並列実行
│ trends │    │   info   │    │  trends  │
└───┬────┘    └────┬─────┘    └────┬─────┘
    │              │               │
    └──────────────┼───────────────┘
                   ▼
          ┌────────────────┐
          │summarize_insights│  知見を抽出
          └────────┬───────┘
                   ▼
             ┌─────────┐
             │   END   │
             └─────────┘
```

### ファイル構成

```
src/graph/
├── __init__.py                    # パッケージエクスポート
├── proposal_agent.py              # メインエージェント
│
├── states/                        # 状態クラス
│   ├── proposal_state.py          # ProposalAgentState, Issue
│   ├── issue_state.py             # IssueExtractorState
│   ├── info_state.py              # InfoOrganizerState
│   └── research_state.py          # WebResearcherState
│
├── agents/                        # サブエージェント
│   ├── issue_extractor.py         # 課題抽出（並列分析→統合）
│   ├── info_organizer.py          # 情報整理（順次実行）
│   └── web_researcher.py          # Web調査（並列調査→統合）
│
├── nodes/                         # メインエージェントのノード
│   ├── load_data.py               # データ読み込み
│   ├── extract_issues.py          # 課題抽出呼び出し
│   ├── organize_info.py           # 情報整理呼び出し
│   ├── check_sufficiency.py       # 情報十分性判定
│   ├── web_research.py            # Web調査呼び出し
│   ├── sections.py                # セクション生成（5セクション）
│   ├── truncation.py              # 文字数制御
│   └── output.py                  # DOCX出力
│
└── edges/
    └── conditionals.py            # 条件分岐（should_research, should_regenerate）
```

### 状態管理

LangGraphの`Annotated`型を使用してリデューサー関数を定義し、並列実行ノードからの状態更新を自動マージ：

```python
# 例: prompt_logsは各ノードから返されたリストが自動的に結合される
prompt_logs: Annotated[list[dict], merge_lists]

# 例: research_resultsは各調査ノードの結果が自動的にマージされる
research_results: Annotated[dict[str, str], merge_dicts]
```
