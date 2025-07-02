#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress投稿モジュール

ref/post_wordpressを基に記事生成システム用に最適化したWordPress投稿機能
"""

import logging
import requests
import time
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """WordPress投稿クラス（記事生成システム用）"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.wp_config = config.get('wordpress', {})
        
        # WordPress設定
        self.site_url = self.wp_config.get('site_url', '').rstrip('/')
        self.username = self.wp_config.get('username', '')
        self.app_password = self.wp_config.get('app_password', '')
        self.default_category = self.wp_config.get('default_category', 'エラー解決')
        self.default_category_id = self.wp_config.get('default_category_id', 1)
        
        # 投稿設定
        self.post_settings = self.wp_config.get('post_settings', {})
        self.auto_publish = self.wp_config.get('auto_publish', True)
        
        # API エンドポイント
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.posts_endpoint = f"{self.api_base}/posts"
        self.categories_endpoint = f"{self.api_base}/categories"
        self.tags_endpoint = f"{self.api_base}/tags"
        
        # 認証設定
        self.auth = HTTPBasicAuth(self.username, self.app_password)
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        logger.info(f"WordPress投稿器を初期化: {self.site_url}")
    
    def publish_article(self, article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        記事をWordPressに投稿
        
        Args:
            article_data: 記事データ
            
        Returns:
            投稿結果、失敗時はNone
        """
        logger.info(f"記事をWordPressに投稿中: {article_data.get('title', '')}")
        
        try:
            # WordPress接続テスト
            if not self.test_connection():
                logger.error("WordPress接続テストに失敗しました")
                return None
            
            # カテゴリとタグのIDを取得/作成
            category_ids = self._get_or_create_categories(article_data)
            tag_ids = self._get_or_create_tags(article_data)
            
            # 投稿データを準備
            post_data = self._prepare_post_data(article_data, category_ids, tag_ids)
            
            # 記事を投稿
            response = requests.post(
                self.posts_endpoint,
                auth=self.auth,
                headers=self.headers,
                json=post_data,
                timeout=60
            )
            
            if response.status_code == 201:
                result = response.json()
                logger.info(f"投稿成功: ID={result['id']}, URL={result['link']}")
                
                # 投稿後の処理
                self._post_publication_tasks(result, article_data)
                
                return result
            else:
                logger.error(f"投稿失敗: {response.status_code}")
                logger.error(f"レスポンス: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"WordPress投稿中にエラーが発生: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        WordPress接続をテスト
        
        Returns:
            接続成功の真偽値
        """
        try:
            response = requests.get(
                self.api_base,
                auth=self.auth,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.debug("WordPress接続テスト成功")
                return True
            else:
                logger.error(f"WordPress接続テスト失敗: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress接続エラー: {e}")
            return False
    
    def _get_or_create_categories(self, article_data: Dict[str, Any]) -> list:
        """カテゴリIDを取得（.envで設定されたWP_DEFAULT_CATEGORY_IDを使用）"""
        
        # .envで設定されたWP_DEFAULT_CATEGORY_IDを常に使用（新規カテゴリ作成を回避）
        logger.debug(f"設定されたデフォルトカテゴリIDを使用: {self.default_category_id}")
        return [self.default_category_id]
    
    def _get_or_create_tags(self, article_data: Dict[str, Any]) -> list:
        """タグIDを取得または作成"""
        tag_ids = []
        tags = article_data.get('tags', [])
        
        if not tags:
            return tag_ids
        
        try:
            for tag_name in tags[:10]:  # 最大10個のタグ
                # 既存タグを検索
                params = {'search': tag_name}
                response = requests.get(
                    self.tags_endpoint,
                    auth=self.auth,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    tags_data = response.json()
                    
                    # 完全一致するタグを探す
                    found = False
                    for tag in tags_data:
                        if tag['name'] == tag_name:
                            tag_ids.append(tag['id'])
                            found = True
                            break
                    
                    # タグが見つからない場合は作成
                    if not found:
                        create_data = {
                            'name': tag_name,
                            'slug': self._generate_slug(tag_name)
                        }
                        
                        create_response = requests.post(
                            self.tags_endpoint,
                            auth=self.auth,
                            headers=self.headers,
                            json=create_data,
                            timeout=30
                        )
                        
                        if create_response.status_code == 201:
                            new_tag = create_response.json()
                            tag_ids.append(new_tag['id'])
                            logger.debug(f"新しいタグを作成: {tag_name} (ID: {new_tag['id']})")
                
                # レート制限対応
                time.sleep(0.1)
            
            logger.debug(f"タグIDを取得: {tag_ids}")
            return tag_ids
            
        except Exception as e:
            logger.warning(f"タグ処理でエラー: {e}")
            return []
    
    def _prepare_post_data(self, article_data: Dict[str, Any], category_ids: list, tag_ids: list) -> Dict[str, Any]:
        """WordPress投稿用データを準備"""
        
        # 投稿ステータスを決定
        status = 'draft'  # デフォルトは下書き
        if self.auto_publish:
            status = self.post_settings.get('status', 'publish')
        
        # コンテンツを準備（HTMLまたはMarkdown）
        content = article_data.get('html_content', article_data.get('content', ''))
        
        post_data = {
            'title': article_data.get('title', ''),
            'content': content,
            'excerpt': article_data.get('excerpt', ''),
            'status': status,
            'slug': article_data.get('slug', ''),
            'categories': category_ids,
            'tags': tag_ids,
            'comment_status': self.post_settings.get('comment_status', 'open'),
            'ping_status': self.post_settings.get('ping_status', 'open')
        }
        
        # メタフィールドを追加（カスタムフィールド）
        post_data['meta'] = {
            'error_message': article_data.get('error_message', ''),
            'seo_score': article_data.get('seo_score', 0),
            'word_count': article_data.get('word_count', 0),
            'generated_by': 'auto_error_article_generator',
            'generation_time': article_data.get('generated_at', time.time())
        }
        
        return post_data
    
    def _generate_slug(self, text: str) -> str:
        """テキストからスラッグを生成"""
        import re
        
        # 日本語文字を除去し、英数字とハイフンのみにする
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # 長すぎる場合は切り詰める
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
        
        # 空の場合はデフォルト値
        if not slug:
            slug = f"auto-generated-{int(time.time())}"
        
        return slug
    
    def _post_publication_tasks(self, post_result: Dict[str, Any], article_data: Dict[str, Any]) -> None:
        """投稿後のタスク処理"""
        try:
            post_id = post_result.get('id')
            
            # アイキャッチ画像の設定（将来実装）
            # self._set_featured_image(post_id, article_data)
            
            # SEO設定の追加（Yoast SEO等のプラグインがある場合）
            # self._set_seo_settings(post_id, article_data)
            
            # カスタムフィールドの設定
            self._set_custom_fields(post_id, article_data)
            
            logger.debug(f"投稿後処理完了: Post ID {post_id}")
            
        except Exception as e:
            logger.warning(f"投稿後処理でエラー: {e}")
    
    def _set_custom_fields(self, post_id: int, article_data: Dict[str, Any]) -> None:
        """カスタムフィールドを設定（オプション機能）"""
        try:
            # カスタムフィールドは投稿成功に必要ない管理用データのため、
            # エラーが発生してもWARNINGを出力しない（静音モード）
            
            custom_fields = {
                'article_quality_score': article_data.get('seo_score', 0),
                'error_solutions_count': len(article_data.get('solutions', [])),
                'source_reliability': article_data.get('avg_reliability', 0)
            }
            
            # 各カスタムフィールドを設定
            for field_key, field_value in custom_fields.items():
                meta_endpoint = f"{self.api_base}/posts/{post_id}/meta"
                
                meta_data = {
                    'key': field_key,
                    'value': str(field_value)
                }
                
                response = requests.post(
                    meta_endpoint,
                    auth=self.auth,
                    headers=self.headers,
                    json=meta_data,
                    timeout=30
                )
                
                # 成功時のみデバッグログ出力（失敗時は無音）
                if response.status_code in [200, 201]:
                    logger.debug(f"カスタムフィールド設定成功: {field_key}={field_value}")
                
                time.sleep(0.1)  # レート制限対応
            
        except Exception as e:
            # カスタムフィールドエラーは投稿成功に影響しないため無音
            logger.debug(f"カスタムフィールド設定（オプション機能）: {e}")
    
    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """投稿を取得"""
        try:
            response = requests.get(
                f"{self.posts_endpoint}/{post_id}",
                auth=self.auth,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"投稿取得失敗: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"投稿取得エラー: {e}")
            return None
    
    def update_post(self, post_id: int, update_data: Dict[str, Any]) -> bool:
        """投稿を更新"""
        try:
            response = requests.post(
                f"{self.posts_endpoint}/{post_id}",
                auth=self.auth,
                headers=self.headers,
                json=update_data,
                timeout=60
            )
            
            if response.status_code == 200:
                logger.info(f"投稿更新成功: ID={post_id}")
                return True
            else:
                logger.error(f"投稿更新失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"投稿更新エラー: {e}")
            return False
    
    def delete_post(self, post_id: int) -> bool:
        """投稿を削除"""
        try:
            response = requests.delete(
                f"{self.posts_endpoint}/{post_id}",
                auth=self.auth,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"投稿削除成功: ID={post_id}")
                return True
            else:
                logger.error(f"投稿削除失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"投稿削除エラー: {e}")
            return False