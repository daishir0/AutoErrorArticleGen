# AutoErrorArticleGen

## Overview
AutoErrorArticleGen is a Python system that automatically discovers undocumented error messages, collects and translates solution information from English-speaking sources, and generates SEO-optimized Japanese WordPress articles completely automatically.

The system provides the following features:
- **Automatic Error Discovery**: Detects trending errors from Stack Overflow, Reddit, and Google Trends
- **Information Collection**: Automatically collects solution information from official English documentation and communities
- **Article Generation**: Uses OpenAI GPT to generate SEO-optimized Japanese articles
- **Quality Management**: Automatic quality checks and SEO score evaluation
- **WordPress Publishing**: Fully automatic posting and publishing to WordPress
- **Sequential Management**: Organizes and saves article data in the format of `0001_~article/`, `0002_~article/`

## Installation
Follow these steps to install AutoErrorArticleGen:

1. Clone the repository:
```bash
git clone https://github.com/daishir0/AutoErrorArticleGen.git
cd AutoErrorArticleGen
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Copy the sample environment file:
   ```bash
   cp config/.env.sample config/.env
   ```
   - Edit the `.env` file and set the following required variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   WP_SITE_URL=https://your-wordpress-site.com
   WP_USERNAME=your_wp_username
   WP_APP_PASSWORD=your_wp_app_password
   ```

4. Configure the system:
   - Copy the sample configuration file:
   ```bash
   cp config/config.yaml.sample config/config.yaml
   ```
   - Edit `config/config.yaml` to adjust settings as needed

## Usage
### Basic Usage
```bash
# Full automatic execution (error discovery → article generation → WordPress posting)
python main.py

# Run in debug mode
python main.py --debug

# Test error discovery only
python main.py --discover

# Generate article from specified error
python main.py --error "ERROR_FILE_NOT_FOUND 0x80070002"

# Run with custom configuration
python main.py --config custom_config.yaml
```

### Execution Process
The system automatically executes the following processes:
1. **Phase 1: Error Discovery** - Detects trending errors from multiple sources
2. **Phase 2: Information Collection** - Automatically collects solution information from English-speaking sources
3. **Phase 3: Article Generation** - Generates high-quality articles using OpenAI GPT
4. **Phase 4: Quality Check** - Automatically evaluates SEO score and readability
5. **Phase 5: Data Storage** - Organizes and saves all data in sequential directories
6. **Phase 6: WordPress Posting** - Automatically posts and publishes to WordPress

## Notes
- API usage limits:
  - OpenAI API: Token-based billing (can be limited in settings)
  - Stack Overflow API: 10,000 requests per day
  - Reddit API: 100 requests per minute
  - WordPress API: Depends on server settings

- Security:
  - Manage API credentials with environment variables
  - Do not include `config.py` or `credentials.json` in Git repositories
  - Use WordPress application passwords

- Quality management:
  - Final human review of generated articles is recommended
  - Articles with SEO scores below 70 should be checked
  - Automatic duplicate article detection is available

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

# AutoErrorArticleGen

## 概要
AutoErrorArticleGenは、未執筆のエラーメッセージを自動発見し、英語圏の解決情報を収集・翻訳して、SEO最適化された日本語WordPress記事を完全自動生成・投稿するPythonシステムです。

このシステムは以下の機能を提供します：
- **エラー自動発見**: Stack Overflow、Reddit、Google Trendsからトレンドエラーを検出
- **情報収集**: 英語圏の公式ドキュメント、コミュニティから解決情報を自動収集
- **記事生成**: OpenAI GPTを使用してSEO最適化された日本語記事を生成
- **品質管理**: 自動品質チェック、SEOスコア評価
- **WordPress投稿**: 完全自動でWordPressに投稿・公開
- **連番管理**: 記事データを `0001_～記事/`, `0002_～記事/` の形式で整理保存

## インストール方法
以下の手順でAutoErrorArticleGenをインストールしてください：

1. リポジトリをクローンします：
```bash
git clone https://github.com/daishir0/AutoErrorArticleGen.git
cd AutoErrorArticleGen
```

2. 依存関係をインストールします：
```bash
pip install -r requirements.txt
```

3. 環境変数を設定します：
   - サンプル環境変数ファイルをコピーします：
   ```bash
   cp config/.env.sample config/.env
   ```
   - `.env`ファイルを編集して、以下の必須変数を設定します：
   ```
   OPENAI_API_KEY=あなたのOpenAI APIキー
   WP_SITE_URL=https://あなたのWordPressサイト.com
   WP_USERNAME=あなたのWPユーザー名
   WP_APP_PASSWORD=あなたのWPアプリケーションパスワード
   ```

4. システムを設定します：
   - サンプル設定ファイルをコピーします：
   ```bash
   cp config/config.yaml.sample config/config.yaml
   ```
   - `config/config.yaml`を編集して、必要に応じて設定を調整します

## 使い方
### 基本的な使用方法
```bash
# 完全自動実行（エラー発見→記事生成→WordPress投稿）
python main.py

# デバッグモードで実行
python main.py --debug

# エラー発見のみテスト
python main.py --discover

# 指定エラーから記事生成
python main.py --error "ERROR_FILE_NOT_FOUND 0x80070002"

# カスタム設定で実行
python main.py --config custom_config.yaml
```

### 実行プロセス
システムは以下の処理を自動実行します：
1. **Phase 1: エラー発見** - 複数のソースからトレンドエラーを検出
2. **Phase 2: 情報収集** - 英語圏から解決情報を自動収集
3. **Phase 3: 記事生成** - OpenAI GPTで高品質記事を生成
4. **Phase 4: 品質チェック** - SEOスコア・読みやすさを自動評価
5. **Phase 5: データ保存** - 連番ディレクトリに全データを整理保存
6. **Phase 6: WordPress投稿** - 自動でWordPressに投稿・公開

## 注意点
- API使用制限：
  - OpenAI API: トークン課金制（設定で制限可能）
  - Stack Overflow API: 1日10,000リクエスト
  - Reddit API: 1分100リクエスト
  - WordPress API: サーバー設定依存

- セキュリティ：
  - API認証情報は環境変数で管理
  - `config.py`や`credentials.json`はGitリポジトリに含めない
  - WordPressアプリケーションパスワードを使用

- 品質管理：
  - 生成記事の人間による最終チェックを推奨
  - SEOスコア70点以下の記事は要確認
  - 重複記事の自動検出機能あり

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。