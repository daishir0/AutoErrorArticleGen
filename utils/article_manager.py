#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事管理モジュール

連番ディレクトリの管理と記事データの保存を担当
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ArticleManager:
    """記事データ管理クラス"""
    
    def __init__(self, articles_dir: str = "articles"):
        """
        初期化
        
        Args:
            articles_dir: 記事保存ディレクトリ
        """
        self.project_root = Path(__file__).parent.parent
        self.articles_dir = self.project_root / articles_dir
        
        # 記事ディレクトリを作成
        self.articles_dir.mkdir(exist_ok=True)
        
        logger.info(f"記事管理システムを初期化: {self.articles_dir}")
    
    def is_error_already_processed(self, error_message: str) -> bool:
        """
        エラーが既に処理済みかチェック
        
        Args:
            error_message: エラーメッセージ
            
        Returns:
            既に処理済みの場合True
        """
        sanitized_error = self._sanitize_error_name(error_message)
        
        # 既存ディレクトリをチェック
        for item in self.articles_dir.iterdir():
            if item.is_dir():
                dir_name = item.name
                # ディレクトリ名からエラー部分を抽出（番号_エラー名_記事の形式）
                parts = dir_name.split('_', 1)
                if len(parts) >= 2:
                    # 最後の"_記事"を除去
                    error_part = parts[1].replace('_記事', '')
                    if error_part == sanitized_error:
                        logger.info(f"エラー '{error_message}' は既に処理済みです: {dir_name}")
                        return True
        
        return False
    
    def get_next_article_number(self) -> int:
        """
        次の記事番号を取得
        
        Returns:
            次の記事番号（4桁）
        """
        existing_dirs = []
        
        # 既存のディレクトリをスキャン
        for item in self.articles_dir.iterdir():
            if item.is_dir():
                # ディレクトリ名から連番を抽出
                match = re.match(r'^(\d{4})_', item.name)
                if match:
                    existing_dirs.append(int(match.group(1)))
        
        # 最大番号を取得し、+1
        if existing_dirs:
            next_number = max(existing_dirs) + 1
        else:
            next_number = 1
        
        logger.debug(f"次の記事番号: {next_number:04d}")
        return next_number
    
    def create_article_directory(self, error_message: str) -> Path:
        """
        記事用ディレクトリを作成
        
        Args:
            error_message: エラーメッセージ
            
        Returns:
            作成されたディレクトリのパス
        """
        # 次の記事番号を取得
        article_number = self.get_next_article_number()
        
        # エラーメッセージから安全なディレクトリ名を生成
        safe_error_name = self._sanitize_error_name(error_message)
        
        # ディレクトリ名を生成
        dir_name = f"{article_number:04d}_{safe_error_name}_記事"
        article_dir = self.articles_dir / dir_name
        
        # ディレクトリを作成
        article_dir.mkdir(exist_ok=True)
        
        logger.info(f"記事ディレクトリを作成: {article_dir}")
        return article_dir
    
    def _sanitize_error_name(self, error_message: str) -> str:
        """
        エラーメッセージからディレクトリ名に安全な文字列を生成
        
        Args:
            error_message: エラーメッセージ
            
        Returns:
            サニタイズされた文字列
        """
        # 英数字、ハイフン、アンダースコアのみ残す
        safe_name = re.sub(r'[^\w\-_]', '_', error_message)
        
        # 連続するアンダースコアを1つに
        safe_name = re.sub(r'_+', '_', safe_name)
        
        # 前後のアンダースコアを除去
        safe_name = safe_name.strip('_')
        
        # 長すぎる場合は切り詰める
        if len(safe_name) > 50:
            safe_name = safe_name[:50].rstrip('_')
        
        # 空の場合はデフォルト値
        if not safe_name:
            safe_name = "UNKNOWN_ERROR"
        
        logger.debug(f"エラー名サニタイズ: {error_message} -> {safe_name}")
        return safe_name
    
    def save_article_data(self, article_dir: Path, data: Dict[str, Any]) -> None:
        """
        記事データを保存
        
        Args:
            article_dir: 記事ディレクトリ
            data: 保存するデータ
        """
        logger.info(f"記事データを保存中: {article_dir}")
        
        try:
            # 1. 記事本文（Markdown）を保存
            if 'article' in data and 'content' in data['article']:
                article_md_path = article_dir / "article.md"
                with open(article_md_path, 'w', encoding='utf-8') as f:
                    f.write(data['article']['content'])
                logger.debug(f"記事Markdownを保存: {article_md_path}")
            
            # 2. 記事本文（HTML）を保存（WordPress投稿用）
            if 'article' in data and 'html_content' in data['article']:
                article_html_path = article_dir / "article.html"
                with open(article_html_path, 'w', encoding='utf-8') as f:
                    f.write(data['article']['html_content'])
                logger.debug(f"記事HTMLを保存: {article_html_path}")
            
            # 3. メタデータを保存
            if 'article' in data:
                metadata = {
                    'title': data['article'].get('title', ''),
                    'slug': data['article'].get('slug', ''),
                    'category': data['article'].get('category', ''),
                    'tags': data['article'].get('tags', []),
                    'excerpt': data['article'].get('excerpt', ''),
                    'word_count': data['article'].get('word_count', 0),
                    'created_at': datetime.now().isoformat(),
                    'error_message': data.get('error_candidate', {}).get('error_message', '')
                }
                
                metadata_path = article_dir / "metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                logger.debug(f"メタデータを保存: {metadata_path}")
            
            # 4. 収集した情報ソースを保存
            if 'sources' in data:
                sources_path = article_dir / "sources.json"
                with open(sources_path, 'w', encoding='utf-8') as f:
                    json.dump(data['sources'], f, ensure_ascii=False, indent=2)
                logger.debug(f"情報ソースを保存: {sources_path}")
            
            # 5. 品質チェック結果を保存
            if 'quality' in data:
                quality_path = article_dir / "seo_data.json"
                with open(quality_path, 'w', encoding='utf-8') as f:
                    json.dump(data['quality'], f, ensure_ascii=False, indent=2)
                logger.debug(f"品質データを保存: {quality_path}")
            
            # 6. エラー候補情報を保存
            if 'error_candidate' in data:
                error_path = article_dir / "error_candidate.json"
                with open(error_path, 'w', encoding='utf-8') as f:
                    json.dump(data['error_candidate'], f, ensure_ascii=False, indent=2)
                logger.debug(f"エラー候補を保存: {error_path}")
            
            logger.info("記事データの保存が完了しました")
            
        except Exception as e:
            logger.error(f"記事データの保存に失敗しました: {e}")
            raise
    
    def save_wordpress_result(self, article_dir: Path, result: Dict[str, Any]) -> None:
        """
        WordPress投稿結果を保存
        
        Args:
            article_dir: 記事ディレクトリ
            result: WordPress投稿結果
        """
        try:
            wordpress_result = {
                'post_id': result.get('id'),
                'url': result.get('link'),
                'published_at': result.get('date'),
                'status': result.get('status'),
                'slug': result.get('slug'),
                'saved_at': datetime.now().isoformat()
            }
            
            result_path = article_dir / "wordpress_result.json"
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(wordpress_result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"WordPress投稿結果を保存: {result_path}")
            
        except Exception as e:
            logger.error(f"WordPress投稿結果の保存に失敗しました: {e}")
    
    def get_article_list(self) -> List[Dict[str, Any]]:
        """
        記事一覧を取得
        
        Returns:
            記事一覧
        """
        articles = []
        
        try:
            for item in sorted(self.articles_dir.iterdir()):
                if item.is_dir():
                    # ディレクトリ名から記事番号を抽出
                    match = re.match(r'^(\d{4})_', item.name)
                    if match:
                        article_number = int(match.group(1))
                        
                        # メタデータを読み込み
                        metadata_path = item / "metadata.json"
                        metadata = {}
                        if metadata_path.exists():
                            try:
                                with open(metadata_path, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                            except Exception as e:
                                logger.warning(f"メタデータの読み込みに失敗: {e}")
                        
                        # WordPress結果を読み込み
                        wordpress_path = item / "wordpress_result.json"
                        wordpress_result = {}
                        if wordpress_path.exists():
                            try:
                                with open(wordpress_path, 'r', encoding='utf-8') as f:
                                    wordpress_result = json.load(f)
                            except Exception as e:
                                logger.warning(f"WordPress結果の読み込みに失敗: {e}")
                        
                        articles.append({
                            'number': article_number,
                            'directory': str(item),
                            'directory_name': item.name,
                            'title': metadata.get('title', ''),
                            'error_message': metadata.get('error_message', ''),
                            'created_at': metadata.get('created_at', ''),
                            'word_count': metadata.get('word_count', 0),
                            'wordpress_url': wordpress_result.get('url', ''),
                            'wordpress_id': wordpress_result.get('post_id', ''),
                        })
            
            logger.info(f"記事一覧を取得: {len(articles)}件")
            return articles
            
        except Exception as e:
            logger.error(f"記事一覧の取得に失敗しました: {e}")
            return []
    
    def get_article_data(self, article_number: int) -> Optional[Dict[str, Any]]:
        """
        指定された記事番号の記事データを取得
        
        Args:
            article_number: 記事番号
            
        Returns:
            記事データ、見つからない場合はNone
        """
        try:
            # 記事ディレクトリを探す
            target_dir = None
            for item in self.articles_dir.iterdir():
                if item.is_dir():
                    match = re.match(r'^(\d{4})_', item.name)
                    if match and int(match.group(1)) == article_number:
                        target_dir = item
                        break
            
            if not target_dir:
                logger.warning(f"記事番号 {article_number:04d} が見つかりません")
                return None
            
            # 各ファイルを読み込み
            data = {}
            
            # メタデータ
            metadata_path = target_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data['metadata'] = json.load(f)
            
            # 記事本文
            article_md_path = target_dir / "article.md"
            if article_md_path.exists():
                with open(article_md_path, 'r', encoding='utf-8') as f:
                    data['content_md'] = f.read()
            
            article_html_path = target_dir / "article.html"
            if article_html_path.exists():
                with open(article_html_path, 'r', encoding='utf-8') as f:
                    data['content_html'] = f.read()
            
            # 情報ソース
            sources_path = target_dir / "sources.json"
            if sources_path.exists():
                with open(sources_path, 'r', encoding='utf-8') as f:
                    data['sources'] = json.load(f)
            
            # SEOデータ
            seo_path = target_dir / "seo_data.json"
            if seo_path.exists():
                with open(seo_path, 'r', encoding='utf-8') as f:
                    data['seo_data'] = json.load(f)
            
            # WordPress結果
            wordpress_path = target_dir / "wordpress_result.json"
            if wordpress_path.exists():
                with open(wordpress_path, 'r', encoding='utf-8') as f:
                    data['wordpress_result'] = json.load(f)
            
            # エラー候補
            error_path = target_dir / "error_candidate.json"
            if error_path.exists():
                with open(error_path, 'r', encoding='utf-8') as f:
                    data['error_candidate'] = json.load(f)
            
            logger.info(f"記事データを取得: {article_number:04d}")
            return data
            
        except Exception as e:
            logger.error(f"記事データの取得に失敗しました: {e}")
            return None