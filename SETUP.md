# 🚀 自動エラー解決記事生成システム セットアップガイド

## 📋 クイックスタート

### 1. 設定ファイルの準備

```bash
# 設定ファイルをコピー
cp config/config.yaml.sample config/config.yaml

# 環境変数ファイルをコピー
cp config/.env.sample config/.env
```

### 2. 環境変数の設定

`config/.env` ファイルを編集して、以下の必須項目を設定：

```bash
# 必須：OpenAI API（記事生成に必要）
OPENAI_API_KEY=your_openai_api_key_here

# 必須：WordPress設定（記事投稿に必要）
WP_SITE_URL=https://your-wordpress-site.com
WP_USERNAME=your_wp_username  
WP_APP_PASSWORD=your_wp_app_password
```

### 3. 依存関係のインストール

```bash
# Python環境をアクティベート
conda activate 311

# 依存関係をインストール
pip install -r requirements.txt
```

### 4. システムテスト

```bash
# エラー発見機能のテスト
python main.py --discover --debug

# 指定エラーでの記事生成テスト
python main.py --error "ERROR_FILE_NOT_FOUND 0x80070002" --debug
```

## 🔑 APIキー取得方法

### OpenAI API Key（必須）
1. [OpenAI Platform](https://platform.openai.com/) にログイン
2. [API Keys](https://platform.openai.com/account/api-keys) ページへ
3. "Create new secret key" をクリック
4. 生成されたキーを `OPENAI_API_KEY` に設定

### WordPress設定（必須）
1. WordPress管理画面にログイン
2. **ユーザー** → **プロフィール** へ
3. **アプリケーションパスワード** セクションで新しいパスワードを生成
4. 生成されたパスワードを `WP_APP_PASSWORD` に設定

### Stack Overflow API Key（オプション）
1. [Stack Apps](https://stackapps.com/apps/oauth/register) で登録
2. アプリケーションを作成
3. 生成されたキーを設定（なくても動作します）

## 🛠 設定レベル別ガイド

### レベル1: 最小構成（テスト用）
- OpenAI API Key のみ設定
- WordPress設定は後回し
- エラー発見・記事生成のテストが可能

```bash
# テスト実行
python main.py --error "TEST_ERROR" --debug
```

### レベル2: 基本構成（記事投稿まで）
- OpenAI API Key
- WordPress設定
- 自動エラー発見から投稿まで完全動作

```bash
# 完全自動実行
python main.py --debug
```

### レベル3: 本格運用構成
- 全APIキー設定
- 監視・アラート機能
- スケジュール実行

## 📊 設定ファイル詳細

### config.yaml の主要設定

#### エラー発見の感度調整
```yaml
selection_criteria:
  min_confidence_score: 0.1    # 0.1-1.0（低いほど多くのエラーを検出）
  min_search_volume: 10        # 月間検索ボリューム最小値
```

#### 記事品質の設定
```yaml
quality:
  thresholds:
    min_word_count: 1000       # 最小文字数
    min_seo_score: 50          # SEOスコア閾値
```

#### WordPress投稿設定
```yaml
wordpress:
  auto_publish: false          # テスト時はfalse（下書き保存）
  post_settings:
    status: "draft"            # "draft" または "publish"
```

## 🔍 トラブルシューティング

### よくあるエラーと解決方法

#### 1. OpenAI APIエラー
```
Error code: 401 - Incorrect API key provided
```
**解決方法:**
- API Key が正しく設定されているか確認
- API残高・利用制限をチェック
- 環境変数が正しく読み込まれているか確認

#### 2. WordPress接続エラー
```
WordPress接続テスト失敗: 401
```
**解決方法:**
- WP_SITE_URL が正しいか確認（https://含む）
- アプリケーションパスワードが正しく生成されているか確認
- WordPressのREST APIが有効か確認

#### 3. エラーが見つからない
```
フィルタリング後にエラー候補が残りませんでした
```
**解決方法:**
- `config.yaml` の `min_confidence_score` を下げる（0.1推奨）
- API制限でStack Overflowから情報が取得できていない可能性

#### 4. 依存関係エラー
```
ModuleNotFoundError: No module named 'openai'
```
**解決方法:**
```bash
conda activate 311
pip install -r requirements.txt
```

## 📁 ディレクトリ構造の確認

正しくセットアップされている場合：

```
auto_error_article_generator/
├── config/
│   ├── config.yaml          ✅ 実際の設定
│   ├── config.yaml.sample   📄 サンプル
│   ├── .env                 ✅ 実際の環境変数
│   └── .env.sample          📄 サンプル
├── articles/                📁 記事出力先
├── logs/                    📁 ログ出力先
└── main.py                  ⚡ 実行ファイル
```

## 🎯 実行モード

### 開発・テスト段階
```bash
# エラー発見のみ
python main.py --discover --debug

# 特定エラーで記事生成
python main.py --error "YOUR_ERROR_MESSAGE" --debug

# 完全実行（下書き保存）
python main.py --debug
```

### 本番運用段階
```bash
# 設定調整後の本格実行
python main.py

# スケジュール実行（cron等で設定）
0 2 * * 1,3,5 /path/to/python /path/to/main.py
```

## 📞 サポート

設定でお困りの場合は、以下の順序で確認してください：

1. **ログファイル確認**: `logs/auto_error_generator.log`
2. **設定ファイル確認**: 必須項目が設定されているか
3. **APIキー確認**: 各サービスで正しく動作するか
4. **ネットワーク確認**: 外部APIにアクセスできるか

---

🎉 **セットアップ完了後は、高品質なエラー解決記事が自動生成されます！**