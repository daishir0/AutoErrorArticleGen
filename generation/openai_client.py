#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI連携モジュール

参照コード（ref/openai_prompt）を基に、記事生成用に最適化したOpenAIクライアント
"""

import time
import json
import logging
from typing import Dict, List, Optional, Union, Any

from openai import OpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(__name__)


class ArticleOpenAIClient:
    """
    記事生成用OpenAIクライアントクラス
    
    ref/openai_promptのOpenAIClientを基に、記事生成に特化した機能を追加
    """
    
    def __init__(
        self, 
        api_key: str,
        model: str = "gpt-4o-mini",
        max_retries: int = 3,
        retry_delay: int = 2,
        backoff_factor: int = 2
    ):
        """
        初期化
        
        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル
            max_retries: 最大リトライ回数
            retry_delay: 初期リトライ間隔（秒）
            backoff_factor: バックオフ係数
        """
        if not api_key:
            raise ValueError("APIキーが設定されていません")
        
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        
        # OpenAIクライアントの初期化
        self.client = OpenAI(api_key=self.api_key)
        
        logger.debug(f"記事生成用OpenAIClientを初期化 - モデル: {self.model}")
    
    def generate_article(
        self, 
        error_info: Dict[str, Any],
        template: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        エラー情報から記事を生成
        
        Args:
            error_info: エラー情報と解決策データ
            template: 記事テンプレート
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            
        Returns:
            生成された記事データ
        """
        try:
            # システムプロンプトを構築
            system_prompt = self._build_system_prompt(template)
            
            # ユーザープロンプトを構築
            user_prompt = self._build_user_prompt(error_info)
            
            # 記事を生成
            response = self._ask_with_retry(
                system=system_prompt,
                prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if not response:
                logger.error("記事生成APIの呼び出しに失敗しました")
                return None
            
            # レスポンスから記事データを抽出
            article_data = self._extract_article_data(response, error_info)
            
            logger.info(f"記事生成完了: {article_data.get('title', 'タイトル不明')}")
            return article_data
            
        except Exception as e:
            logger.error(f"記事生成中にエラーが発生: {e}")
            return None
    
    def _build_system_prompt(self, template: Optional[str] = None) -> str:
        """システムプロンプトを構築"""
        
        base_prompt = """あなたは技術系ブログの専門ライターです。
エラー解決記事を日本語で執筆することが専門です。

以下の要件に従って、高品質なエラー解決記事を作成してください：

【記事の要件】
1. SEOに最適化されたタイトル（エラーメッセージ + 解決方法 + 年号）
2. エラーメッセージにエラー番号があるのならば、必ず含めること
3. 構造化された見出し（H1, H2, H3を適切に使用）
4. 具体的で実行可能な解決手順
5. 読者にとって分かりやすい説明
6. **必須**: 3500文字以上の十分な文字数（5000文字推奨）
7. 関連情報や予防策も含める
8. 各セクションを詳細に記述し、十分な情報量を確保する

【記事構成テンプレート - WordPress投稿用（各セクション詳細記述必須）】
# H1: [エラーメッセージ]の解決方法【2025年最新版】

## H2: エラーの概要・症状（400文字以上）
- エラーが表示される状況
- 具体的な症状と影響
- ユーザーの困りごと

## H2: このエラーが発生する原因（600文字以上）
- 主要な原因3-5個を詳細説明
- 各原因の技術的背景
- システム環境との関係

## H2: 解決方法1（最も効果的）（800文字以上）
### H3: 手順1-1（具体的なステップ）
### H3: 手順1-2（詳細な操作方法）
### H3: 注意点とトラブルシューティング

## H2: 解決方法2（代替手段）（600文字以上）
- 方法1が効果ない場合の対処
- 詳細な手順と注意点

## H2: 解決方法3（上級者向け）（500文字以上）
- より技術的なアプローチ
- コマンドラインや設定変更

## H2: エラーの予防方法（400文字以上）
- 事前対策
- 定期メンテナンス方法

## H2: 関連するエラーと対処法（400文字以上）
- 類似エラーの紹介
- 関連する問題への対処

## H2: まとめ（300文字以上）
- 重要ポイントの再確認
- 次のステップ提案

【重要：コードとコマンドの表記ルール】
- コマンド、コード、ファイル名は必ず引用符で囲む（例：`sudo apt update`、`config.xml`）
- 複数行のコードは引用ブロック形式で記述：
```
コード例をここに
複数行可能
```
- HTMLタグやXMLタグを記述する場合は、必ずエスケープして読みやすくする
- シェーダーコードなどの技術的コードは適切にフォーマットして引用ブロックで表示

【出力形式】
JSON形式で以下の構造で回答してください：
{
  "title": "記事タイトル",
  "slug": "url-slug",
  "content": "記事本文（Markdown形式、3500文字以上必須、コード部分は引用ブロック使用）",
  "excerpt": "記事の概要（120-160文字、SEO最適化されたメタディスクリプション）",
  "meta_description": "SEO用メタディスクリプション（120-160文字、検索結果に表示される説明文）",
  "tags": ["エラー解決", "Windows", "トラブルシューティング"],
  "category": "エラー解決",
  "word_count": 文字数
}"""
        
        if template:
            # カスタムテンプレートが提供された場合は併用
            return f"{base_prompt}\n\n【追加テンプレート】\n{template}"
        
        return base_prompt
    
    def _build_user_prompt(self, error_info: Dict[str, Any]) -> str:
        """ユーザープロンプトを構築"""
        
        error_message = error_info.get('error_message', '不明なエラー')
        solutions = error_info.get('solutions', [])
        sources = error_info.get('sources', [])
        
        prompt = f"""以下のエラーについて、解決記事を作成してください。

【エラーメッセージ】
{error_message}

【収集した解決情報】
"""
        
        # 解決策情報を追加
        for i, solution in enumerate(solutions, 1):
            prompt += f"""
--- 解決策 {i} ---
説明: {solution.get('description', '')}
手順: {solution.get('steps', '')}
信頼度: {solution.get('reliability', 'N/A')}
ソース: {solution.get('source_url', '')}
"""
        
        # ソース情報を追加
        if sources:
            prompt += "\n【参考ソース】\n"
            for i, source in enumerate(sources, 1):
                prompt += f"{i}. {source.get('title', '')} - {source.get('url', '')}\n"
        
        prompt += """
上記の情報を基に、日本語で分かりやすいエラー解決記事を作成してください。
技術的な内容は正確に、初心者でも理解できるよう丁寧に説明してください。
"""
        
        return prompt
    
    def _ask_with_retry(
        self, 
        system: str,
        prompt: str, 
        max_tokens: int = 4000,
        temperature: float = 0.7
    ) -> Optional[ChatCompletion]:
        """
        リトライ機能付きでAPIを呼び出し
        
        Args:
            system: システムプロンプト
            prompt: ユーザープロンプト
            max_tokens: 最大トークン数
            temperature: 温度
            
        Returns:
            ChatCompletion レスポンス
        """
        retry_count = 0
        last_error = None
        current_delay = self.retry_delay
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
        
        while retry_count <= self.max_retries:
            try:
                logger.debug(f"OpenAI API呼び出し - リトライ回数: {retry_count}")
                
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                end_time = time.time()
                
                logger.debug(f"API呼び出し成功 - 所要時間: {end_time - start_time:.2f}秒")
                return response
                
            except Exception as e:
                logger.warning(f"API呼び出しエラー: {e}")
                last_error = e
                
                if retry_count < self.max_retries:
                    logger.info(f"{current_delay}秒後にリトライします ({retry_count+1}/{self.max_retries})")
                    time.sleep(current_delay)
                    current_delay *= self.backoff_factor
                else:
                    logger.error(f"最大リトライ回数を超えました")
                    break
            
            retry_count += 1
        
        if last_error:
            raise last_error
        else:
            raise Exception("不明なエラーが発生しました")
    
    def _extract_article_data(self, response: ChatCompletion, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        APIレスポンスから記事データを抽出
        
        Args:
            response: OpenAI APIレスポンス
            error_info: 元のエラー情報
            
        Returns:
            記事データ
        """
        try:
            # レスポンステキストを取得
            content = response.choices[0].message.content
            if not content:
                raise ValueError("レスポンスが空です")
            
            # JSONを抽出
            article_json = self._extract_json_from_text(content)
            
            if not article_json:
                # JSONが取得できない場合は、テキストをそのまま使用
                logger.warning("JSON形式での抽出に失敗。テキストから記事データを生成します")
                article_json = self._generate_fallback_article_data(content, error_info)
            
            # 必要なフィールドを補完
            article_data = {
                'title': article_json.get('title', f"{error_info.get('error_message', '')}の解決方法"),
                'slug': article_json.get('slug', ''),
                'content': article_json.get('content', content),
                'html_content': self._markdown_to_html(article_json.get('content', content)),
                'excerpt': article_json.get('excerpt', ''),
                'meta_description': article_json.get('meta_description', article_json.get('excerpt', '')),
                'tags': article_json.get('tags', []),
                'category': article_json.get('category', 'エラー解決'),
                'word_count': article_json.get('word_count', len(content)),
                'error_message': error_info.get('error_message', ''),
                'generated_at': time.time(),
                'model_used': self.model
            }
            
            # スラッグが空の場合は生成
            if not article_data['slug']:
                article_data['slug'] = self._generate_slug(article_data['title'])
            
            return article_data
            
        except Exception as e:
            logger.error(f"記事データの抽出に失敗: {e}")
            # フォールバック記事データを生成
            return self._generate_fallback_article_data(
                response.choices[0].message.content or "",
                error_info
            )
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """テキストからJSONを抽出"""
        try:
            # JSONブロックを探す
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
            else:
                logger.warning("JSONブロックが見つかりませんでした")
                return None
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSONのデコードに失敗: {e}")
            return None
    
    def _generate_fallback_article_data(self, content: str, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """フォールバック用の記事データを生成"""
        error_message = error_info.get('error_message', '不明なエラー')
        
        return {
            'title': f"{error_message}の解決方法【2025年最新版】",
            'slug': self._generate_slug(error_message),
            'content': content,
            'html_content': self._markdown_to_html(content),
            'excerpt': f"{error_message}のエラーが発生した場合の解決方法を詳しく解説します。",
            'meta_description': f"{error_message}エラーの原因と解決方法を初心者にも分かりやすく解説。実際に効果のある対処法を複数紹介し、予防策も含めて詳細に説明します。",
            'tags': [error_message, "エラー解決", "トラブルシューティング"],
            'category': 'エラー解決',
            'word_count': len(content),
            'error_message': error_message,
            'generated_at': time.time(),
            'model_used': self.model
        }
    
    def _generate_slug(self, title: str) -> str:
        """タイトルからスラッグを生成"""
        import re
        
        # 日本語を除去し、英数字とハイフンのみにする
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # 長すぎる場合は切り詰める
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
        
        # 空の場合はデフォルト値
        if not slug:
            slug = f"error-article-{int(time.time())}"
        
        return slug
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """MarkdownをHTMLに変換（WordPress最適化版）"""
        try:
            # markdownライブラリがある場合は使用（拡張機能付き）
            import markdown
            
            # WordPress向けの拡張機能を有効化
            extensions = ['fenced_code', 'codehilite', 'tables', 'nl2br']
            extension_configs = {
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False  # WordPressのシンタックスハイライターを使用
                }
            }
            
            html = markdown.markdown(
                markdown_text, 
                extensions=extensions,
                extension_configs=extension_configs
            )
            return html
            
        except ImportError:
            # フォールバック: WordPress向け改良版簡易変換
            import re
            lines = markdown_text.split('\n')
            html_lines = []
            in_code_block = False
            code_block_lang = ''
            code_block_content = []
            in_list = False
            
            for line in lines:
                # コードブロックの開始/終了を検出
                if line.strip().startswith('```'):
                    if not in_code_block:
                        # コードブロック開始
                        in_code_block = True
                        code_block_lang = line.strip()[3:].strip()
                        code_block_content = []
                    else:
                        # コードブロック終了
                        in_code_block = False
                        code_content = '\n'.join(code_block_content)
                        # HTMLエスケープ
                        code_content = code_content.replace('&', '&amp;')
                        code_content = code_content.replace('<', '&lt;')
                        code_content = code_content.replace('>', '&gt;')
                        
                        if code_block_lang:
                            html_lines.append(f'<pre><code class="language-{code_block_lang}">{code_content}</code></pre>')
                        else:
                            html_lines.append(f'<pre><code>{code_content}</code></pre>')
                    continue
                
                # コードブロック内の場合
                if in_code_block:
                    code_block_content.append(line)
                    continue
                
                # 見出しの変換
                if line.startswith('### '):
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    html_lines.append(f'<h3>{line[4:]}</h3>')
                elif line.startswith('## '):
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    html_lines.append(f'<h2>{line[3:]}</h2>')
                elif line.startswith('# '):
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    html_lines.append(f'<h1>{line[2:]}</h1>')
                
                # リストの変換
                elif line.startswith('- '):
                    if not in_list:
                        html_lines.append('<ul>')
                        in_list = True
                    # インラインコードの変換
                    list_content = re.sub(r'`([^`]+)`', r'<code>\1</code>', line[2:])
                    html_lines.append(f'<li>{list_content}</li>')
                
                # 空行の処理
                elif line.strip() == '':
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    html_lines.append('')
                
                # 通常の段落
                else:
                    if in_list:
                        html_lines.append('</ul>')
                        in_list = False
                    # インラインコードの変換
                    paragraph = re.sub(r'`([^`]+)`', r'<code>\1</code>', line)
                    # 太字の変換
                    paragraph = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', paragraph)
                    html_lines.append(f'<p>{paragraph}</p>')
            
            # リストが開いたままの場合は閉じる
            if in_list:
                html_lines.append('</ul>')
            
            # 空行を除去して結合
            html = '\n'.join([line for line in html_lines if line.strip() != ''])
            
            return html
    
    def get_usage_info(self, response: ChatCompletion) -> Dict[str, int]:
        """使用量情報を取得"""
        if not response or not response.usage:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }