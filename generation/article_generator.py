#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事生成モジュール

収集した解決情報からSEO最適化された記事を生成
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .openai_client import ArticleOpenAIClient

logger = logging.getLogger(__name__)


class ArticleGenerator:
    """記事生成エンジンクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.content_config = config.get('content_generation', {})
        self.openai_config = self.content_config.get('openai', {})
        
        # OpenAIクライアントの初期化
        api_key = self.openai_config.get('api_key', '')
        if not api_key:
            raise ValueError("OpenAI APIキーが設定されていません")
        
        self.openai_client = ArticleOpenAIClient(
            api_key=api_key,
            model=self.openai_config.get('model', 'gpt-4o-mini'),
            max_retries=3,
            retry_delay=2
        )
        
        logger.info("記事生成エンジンを初期化しました")
    
    def generate_article(self, solution_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解決情報から記事を生成
        
        Args:
            solution_info: 収集された解決情報
            
        Returns:
            生成された記事データ、失敗時はNone
        """
        error_message = solution_info.get('error_message', '')
        logger.info(f"記事生成を開始: {error_message}")
        
        try:
            # エラーメッセージのタイプを判定してテンプレートを選択
            template = self._select_template(error_message)
            
            # 記事生成パラメータを準備（長い記事生成のため上限増加）
            generation_params = {
                'max_tokens': self.openai_config.get('max_tokens', 6000),  # 3500文字以上確保のため増加
                'temperature': self.openai_config.get('temperature', 0.7)
            }
            
            # OpenAIで記事を生成
            article_data = self.openai_client.generate_article(
                error_info=solution_info,
                template=template,
                **generation_params
            )
            
            if not article_data:
                logger.error("記事生成に失敗しました")
                return None
            
            # SEO最適化とポストプロセッシング
            optimized_article = self._optimize_article(article_data, solution_info)
            
            # 品質チェック
            quality_result = self._basic_quality_check(optimized_article)
            optimized_article['quality_check'] = quality_result
            
            logger.info(f"記事生成完了: {optimized_article['title']}")
            return optimized_article
            
        except Exception as e:
            logger.error(f"記事生成中にエラーが発生: {e}")
            return None
    
    def _select_template(self, error_message: str) -> Optional[str]:
        """エラーメッセージに基づいてテンプレートを選択"""
        
        error_lower = error_message.lower()
        templates_config = self.content_config.get('templates', {})
        
        # エラータイプを判定
        if any(keyword in error_lower for keyword in ['windows', '0x', 'bsod', 'registry']):
            template_file = templates_config.get('windows_error')
        elif any(keyword in error_lower for keyword in ['macos', 'mac os', 'darwin', 'kernel panic']):
            template_file = templates_config.get('macos_error')
        elif any(keyword in error_lower for keyword in ['linux', 'ubuntu', 'debian', 'permission denied']):
            template_file = templates_config.get('linux_error')
        elif any(keyword in error_lower for keyword in ['application', 'software', 'program']):
            template_file = templates_config.get('software_error')
        else:
            template_file = templates_config.get('default')
        
        # テンプレートファイルを読み込み
        if template_file:
            try:
                template_path = Path(__file__).parent.parent / template_file
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    logger.warning(f"テンプレートファイルが見つかりません: {template_path}")
            except Exception as e:
                logger.warning(f"テンプレート読み込みエラー: {e}")
        
        return None
    
    def _optimize_article(self, article_data: Dict[str, Any], solution_info: Dict[str, Any]) -> Dict[str, Any]:
        """記事のSEO最適化とポストプロセッシング"""
        
        optimized = article_data.copy()
        
        # 1. タイトル最適化
        optimized['title'] = self._optimize_title(article_data['title'], solution_info)
        
        # 2. メタディスクリプション最適化
        if not optimized.get('excerpt'):
            optimized['excerpt'] = self._generate_meta_description(optimized, solution_info)
        
        # 3. スラッグ最適化
        optimized['slug'] = self._optimize_slug(optimized['slug'], solution_info)
        
        # 4. タグ最適化
        optimized['tags'] = self._optimize_tags(optimized.get('tags', []), solution_info)
        
        # 5. 内部リンク追加（将来実装）
        # optimized['content'] = self._add_internal_links(optimized['content'])
        
        # 6. 文字数チェック
        content_length = len(optimized['content'])
        target_range = self.content_config.get('target_length', [3000, 5000])
        
        if content_length < target_range[0]:
            logger.warning(f"記事の文字数が少なすぎます: {content_length}文字 (目標: {target_range[0]}-{target_range[1]}文字)")
        elif content_length > target_range[1]:
            logger.warning(f"記事の文字数が多すぎます: {content_length}文字 (目標: {target_range[0]}-{target_range[1]}文字)")
        
        optimized['word_count'] = content_length
        
        # 7. SEOスコア計算
        optimized['seo_score'] = self._calculate_seo_score(optimized, solution_info)
        
        logger.info(f"記事最適化完了 - SEOスコア: {optimized['seo_score']}")
        return optimized
    
    def _optimize_title(self, title: str, solution_info: Dict[str, Any]) -> str:
        """タイトルを最適化"""
        error_message = solution_info.get('error_message', '')
        
        # タイトルにエラーメッセージが含まれているかチェック
        if error_message and error_message not in title:
            # エラーメッセージを含むタイトルに変更
            title = f"{error_message}の解決方法【2025年最新版】"
        
        # タイトルの長さをチェック（30-60文字が理想）
        if len(title) > 60:
            # 長すぎる場合は短縮
            title = title[:57] + "..."
        elif len(title) < 30:
            # 短すぎる場合は補足を追加
            if "解決方法" not in title:
                title += "の解決方法"
            if "2025" not in title:
                title += "【2025年版】"
        
        return title
    
    def _generate_meta_description(self, article_data: Dict[str, Any], solution_info: Dict[str, Any]) -> str:
        """メタディスクリプションを生成"""
        error_message = solution_info.get('error_message', '')
        
        # 基本的なメタディスクリプション
        description = f"{error_message}のエラーが発生した場合の解決方法を詳しく解説します。"
        
        # 解決策の数を追加
        solutions_count = len(solution_info.get('solutions', []))
        if solutions_count > 1:
            description += f"{solutions_count}つの効果的な解決策をご紹介。"
        
        # 対象OS/ソフトウェアを追加
        error_lower = error_message.lower()
        if 'windows' in error_lower:
            description += "Windows対応。"
        elif any(keyword in error_lower for keyword in ['macos', 'mac']):
            description += "macOS対応。"
        elif 'linux' in error_lower:
            description += "Linux対応。"
        
        # 文字数制限（160文字以内）
        if len(description) > 160:
            description = description[:157] + "..."
        
        return description
    
    def _optimize_slug(self, slug: str, solution_info: Dict[str, Any]) -> str:
        """スラッグを最適化"""
        import re
        
        error_message = solution_info.get('error_message', '')
        
        # エラーメッセージからキーワードを抽出
        keywords = []
        
        # よくあるエラーキーワードを抽出
        error_patterns = [
            r'ERROR[_\s]+([A-Z_]+)',
            r'0x([0-9A-Fa-f]+)',
            r'([A-Z_]+)Exception',
            r'([A-Z_]+)Error'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, error_message, re.IGNORECASE)
            keywords.extend(matches)
        
        # スラッグを再構築
        if keywords:
            main_keyword = keywords[0].lower().replace('_', '-')
            optimized_slug = f"{main_keyword}-solution-2025"
        else:
            # フォールバック
            safe_error = re.sub(r'[^\w\s-]', '', error_message.lower())
            safe_error = re.sub(r'[-\s]+', '-', safe_error)
            optimized_slug = f"{safe_error[:30]}-solution"
        
        return optimized_slug
    
    def _optimize_tags(self, existing_tags: list, solution_info: Dict[str, Any]) -> list:
        """タグを最適化"""
        tags = set(existing_tags)
        error_message = solution_info.get('error_message', '')
        
        # 基本タグを追加
        tags.add("エラー解決")
        tags.add("トラブルシューティング")
        
        # OS/プラットフォーム別タグ
        error_lower = error_message.lower()
        if 'windows' in error_lower:
            tags.update(["Windows", "Windows エラー"])
        elif any(keyword in error_lower for keyword in ['macos', 'mac']):
            tags.update(["macOS", "Mac エラー"])
        elif 'linux' in error_lower:
            tags.update(["Linux", "Linux エラー"])
        
        # エラーコード関連
        import re
        if re.search(r'0x[0-9A-Fa-f]+', error_message):
            tags.add("エラーコード")
        
        # ソフトウェア固有のタグ
        software_keywords = {
            'chrome': 'Google Chrome',
            'firefox': 'Firefox',
            'edge': 'Microsoft Edge',
            'office': 'Microsoft Office',
            'adobe': 'Adobe',
            'steam': 'Steam'
        }
        
        for keyword, tag in software_keywords.items():
            if keyword in error_lower:
                tags.add(tag)
        
        # タグ数を制限（最大10個）
        return list(tags)[:10]
    
    def _calculate_seo_score(self, article_data: Dict[str, Any], solution_info: Dict[str, Any]) -> int:
        """SEOスコアを計算"""
        score = 0
        error_message = solution_info.get('error_message', '')
        
        # タイトル最適化チェック（20点）
        title = article_data.get('title', '')
        if error_message in title:
            score += 15
        if len(title) >= 30 and len(title) <= 60:
            score += 5
        
        # メタディスクリプションチェック（15点）
        excerpt = article_data.get('excerpt', '')
        if excerpt and len(excerpt) >= 120 and len(excerpt) <= 160:
            score += 10
        if error_message in excerpt:
            score += 5
        
        # 文字数チェック（20点）
        word_count = article_data.get('word_count', 0)
        target_range = self.content_config.get('target_length', [3000, 5000])
        if target_range[0] <= word_count <= target_range[1]:
            score += 20
        elif word_count >= target_range[0] * 0.8:
            score += 15
        elif word_count >= target_range[0] * 0.6:
            score += 10
        
        # コンテンツ構造チェック（20点）
        content = article_data.get('content', '')
        if '## ' in content:  # H2見出しの存在
            score += 10
        if '### ' in content:  # H3見出しの存在
            score += 5
        if '1. ' in content or '- ' in content:  # リストの存在
            score += 5
        
        # キーワード密度チェック（15点）
        if content:
            keyword_count = content.lower().count(error_message.lower())
            content_words = len(content.split())
            if content_words > 0:
                keyword_density = (keyword_count / content_words) * 100
                if 1 <= keyword_density <= 3:  # 1-3%の密度が理想
                    score += 15
                elif 0.5 <= keyword_density < 1 or 3 < keyword_density <= 5:
                    score += 10
        
        # タグ最適化チェック（10点）
        tags = article_data.get('tags', [])
        if len(tags) >= 3:
            score += 5
        if any(tag in ["エラー解決", "トラブルシューティング"] for tag in tags):
            score += 5
        
        return min(score, 100)  # 最大100点
    
    def _basic_quality_check(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """基本的な品質チェック"""
        issues = []
        checks_passed = 0
        total_checks = 0
        
        # 1. 文字数チェック
        total_checks += 1
        word_count = article_data.get('word_count', 0)
        min_words = self.content_config.get('target_length', [3000, 5000])[0]
        if word_count >= min_words:
            checks_passed += 1
        else:
            issues.append(f"文字数不足: {word_count}文字 (最小: {min_words}文字)")
        
        # 2. タイトルチェック
        total_checks += 1
        title = article_data.get('title', '')
        if title and len(title) >= 20:
            checks_passed += 1
        else:
            issues.append("タイトルが短すぎます")
        
        # 3. 見出し構造チェック
        total_checks += 1
        content = article_data.get('content', '')
        if '## ' in content:
            checks_passed += 1
        else:
            issues.append("H2見出しがありません")
        
        # 4. メタディスクリプションチェック
        total_checks += 1
        excerpt = article_data.get('excerpt', '')
        if excerpt and len(excerpt) >= 100:
            checks_passed += 1
        else:
            issues.append("メタディスクリプションが不十分です")
        
        # 品質スコア計算
        quality_score = (checks_passed / total_checks) * 100 if total_checks > 0 else 0
        passed = quality_score >= 70  # 70%以上で合格
        
        return {
            'passed': passed,
            'score': quality_score,
            'checks_passed': checks_passed,
            'total_checks': total_checks,
            'issues': issues
        }