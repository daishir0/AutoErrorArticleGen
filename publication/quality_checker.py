#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
品質チェックモジュール

生成された記事の品質をチェックし、SEOスコアや読みやすさを評価
"""

import re
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class QualityChecker:
    """記事品質チェッククラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.quality_config = config.get('quality', {})
        self.checks_config = self.quality_config.get('checks', {})
        self.thresholds = self.quality_config.get('thresholds', {})
        
        logger.info("品質チェッカーを初期化しました")
    
    def check_quality(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        記事の品質をチェック
        
        Args:
            article_data: 記事データ
            
        Returns:
            品質チェック結果
        """
        logger.info(f"品質チェックを開始: {article_data.get('title', '')}")
        
        try:
            check_results = {}
            issues = []
            total_score = 0
            max_score = 0
            
            # 1. 基本品質チェック
            basic_result = self._check_basic_quality(article_data)
            check_results['basic_quality'] = basic_result
            total_score += basic_result['score']
            max_score += basic_result['max_score']
            issues.extend(basic_result['issues'])
            
            # 2. SEOチェック
            seo_result = self._check_seo_quality(article_data)
            check_results['seo_quality'] = seo_result
            total_score += seo_result['score']
            max_score += seo_result['max_score']
            issues.extend(seo_result['issues'])
            
            # 3. コンテンツ構造チェック
            structure_result = self._check_content_structure(article_data)
            check_results['content_structure'] = structure_result
            total_score += structure_result['score']
            max_score += structure_result['max_score']
            issues.extend(structure_result['issues'])
            
            # 4. 読みやすさチェック
            readability_result = self._check_readability(article_data)
            check_results['readability'] = readability_result
            total_score += readability_result['score']
            max_score += readability_result['max_score']
            issues.extend(readability_result['issues'])
            
            # 5. 重複チェック（有効な場合）
            if self.checks_config.get('duplicate_detection', False):
                duplicate_result = self._check_duplicates(article_data)
                check_results['duplicate_check'] = duplicate_result
                if not duplicate_result['passed']:
                    issues.extend(duplicate_result['issues'])
            
            # 6. リンク検証（有効な場合）
            if self.checks_config.get('link_validation', False):
                link_result = self._check_links(article_data)
                check_results['link_validation'] = link_result
                if not link_result['passed']:
                    issues.extend(link_result['issues'])
            
            # 全体スコアを計算
            overall_score = (total_score / max_score * 100) if max_score > 0 else 0
            
            # 合格/不合格を判定
            min_score = self.thresholds.get('min_seo_score', 70)
            passed = overall_score >= min_score and len([i for i in issues if i.get('severity') == 'high']) == 0
            
            result = {
                'passed': passed,
                'overall_score': round(overall_score, 1),
                'seo_score': round(seo_result['score'] / seo_result['max_score'] * 100, 1) if seo_result['max_score'] > 0 else 0,
                'readability_score': round(readability_result['score'] / readability_result['max_score'] * 100, 1) if readability_result['max_score'] > 0 else 0,
                'issues': issues,
                'detailed_results': check_results,
                'summary': {
                    'total_issues': len(issues),
                    'high_severity_issues': len([i for i in issues if i.get('severity') == 'high']),
                    'medium_severity_issues': len([i for i in issues if i.get('severity') == 'medium']),
                    'low_severity_issues': len([i for i in issues if i.get('severity') == 'low'])
                }
            }
            
            logger.info(f"品質チェック完了 - スコア: {overall_score:.1f}, 合格: {passed}")
            return result
            
        except Exception as e:
            logger.error(f"品質チェック中にエラーが発生: {e}")
            return {
                'passed': False,
                'overall_score': 0,
                'seo_score': 0,
                'readability_score': 0,
                'issues': [{'message': f'品質チェックエラー: {e}', 'severity': 'high'}]
            }
    
    def _check_basic_quality(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """基本品質チェック"""
        score = 0
        max_score = 100
        issues = []
        
        # 文字数チェック
        word_count = article_data.get('word_count', 0)
        min_words = self.thresholds.get('min_word_count', 2000)
        max_words = self.thresholds.get('max_word_count', 8000)
        
        if word_count < min_words:
            issues.append({
                'message': f'文字数不足: {word_count}文字 (最小: {min_words}文字)',
                'severity': 'high'
            })
        elif word_count > max_words:
            issues.append({
                'message': f'文字数過多: {word_count}文字 (最大: {max_words}文字)',
                'severity': 'medium'
            })
        else:
            score += 30
        
        # タイトルチェック
        title = article_data.get('title', '')
        if not title:
            issues.append({'message': 'タイトルがありません', 'severity': 'high'})
        elif len(title) < 20:
            issues.append({'message': 'タイトルが短すぎます', 'severity': 'medium'})
        elif len(title) > 70:
            issues.append({'message': 'タイトルが長すぎます', 'severity': 'medium'})
        else:
            score += 25
        
        # コンテンツ存在チェック
        content = article_data.get('content', '')
        if not content:
            issues.append({'message': 'コンテンツがありません', 'severity': 'high'})
        else:
            score += 20
        
        # メタディスクリプションチェック
        excerpt = article_data.get('excerpt', '')
        if not excerpt:
            issues.append({'message': 'メタディスクリプションがありません', 'severity': 'medium'})
        elif len(excerpt) < 100 or len(excerpt) > 160:
            issues.append({'message': 'メタディスクリプションの長さが不適切です', 'severity': 'low'})
        else:
            score += 25
        
        return {
            'score': score,
            'max_score': max_score,
            'issues': issues,
            'passed': score >= 70
        }
    
    def _check_seo_quality(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """SEO品質チェック"""
        score = 0
        max_score = 100
        issues = []
        
        title = article_data.get('title', '')
        content = article_data.get('content', '')
        excerpt = article_data.get('excerpt', '')
        error_message = article_data.get('error_message', '')
        
        # キーワード（エラーメッセージ）の配置チェック
        if error_message:
            # タイトルにキーワードが含まれているか
            if error_message.lower() in title.lower():
                score += 20
            else:
                issues.append({
                    'message': 'タイトルにメインキーワードが含まれていません',
                    'severity': 'high'
                })
            
            # メタディスクリプションにキーワードが含まれているか
            if error_message.lower() in excerpt.lower():
                score += 15
            else:
                issues.append({
                    'message': 'メタディスクリプションにキーワードが含まれていません',
                    'severity': 'medium'
                })
            
            # コンテンツ内のキーワード密度チェック
            if content:
                keyword_count = content.lower().count(error_message.lower())
                content_words = len(content.split())
                if content_words > 0:
                    keyword_density = (keyword_count / content_words) * 100
                    
                    if 1 <= keyword_density <= 3:
                        score += 25
                    elif 0.5 <= keyword_density < 1:
                        score += 15
                        issues.append({
                            'message': f'キーワード密度が低すぎます: {keyword_density:.2f}%',
                            'severity': 'low'
                        })
                    elif keyword_density > 3:
                        issues.append({
                            'message': f'キーワード密度が高すぎます: {keyword_density:.2f}%',
                            'severity': 'medium'
                        })
                    else:
                        issues.append({
                            'message': 'キーワードがコンテンツに十分含まれていません',
                            'severity': 'medium'
                        })
        
        # スラッグの品質チェック
        slug = article_data.get('slug', '')
        if slug:
            if re.match(r'^[a-z0-9\-]+$', slug):
                score += 10
            else:
                issues.append({
                    'message': 'スラッグの形式が不適切です',
                    'severity': 'low'
                })
        
        # タグの存在チェック
        tags = article_data.get('tags', [])
        if len(tags) >= 3:
            score += 15
        elif len(tags) >= 1:
            score += 10
            issues.append({
                'message': 'タグの数が少なすぎます',
                'severity': 'low'
            })
        else:
            issues.append({
                'message': 'タグが設定されていません',
                'severity': 'medium'
            })
        
        # 画像のALTテキストチェック（HTMLコンテンツがある場合）
        html_content = article_data.get('html_content', '')
        if html_content:
            img_tags = re.findall(r'<img[^>]*>', html_content)
            img_without_alt = [img for img in img_tags if 'alt=' not in img]
            if img_without_alt:
                issues.append({
                    'message': f'{len(img_without_alt)}個の画像にALTテキストがありません',
                    'severity': 'medium'
                })
            else:
                score += 15
        
        return {
            'score': score,
            'max_score': max_score,
            'issues': issues,
            'passed': score >= 60
        }
    
    def _check_content_structure(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """コンテンツ構造チェック"""
        score = 0
        max_score = 100
        issues = []
        
        content = article_data.get('content', '')
        
        # 見出し構造チェック
        h1_count = len(re.findall(r'^# ', content, re.MULTILINE))
        h2_count = len(re.findall(r'^## ', content, re.MULTILINE))
        h3_count = len(re.findall(r'^### ', content, re.MULTILINE))
        
        # H1チェック
        if h1_count == 1:
            score += 20
        elif h1_count == 0:
            issues.append({
                'message': 'H1見出しがありません',
                'severity': 'high'
            })
        else:
            issues.append({
                'message': f'H1見出しが複数あります: {h1_count}個',
                'severity': 'medium'
            })
        
        # H2チェック
        if h2_count >= 3:
            score += 25
        elif h2_count >= 1:
            score += 15
            issues.append({
                'message': 'H2見出しの数が少なすぎます',
                'severity': 'low'
            })
        else:
            issues.append({
                'message': 'H2見出しがありません',
                'severity': 'medium'
            })
        
        # H3チェック
        if h3_count >= 2:
            score += 15
        elif h3_count >= 1:
            score += 10
        
        # リストの存在チェック
        list_count = len(re.findall(r'^[-*+] |^\d+\. ', content, re.MULTILINE))
        if list_count >= 3:
            score += 20
        elif list_count >= 1:
            score += 10
            issues.append({
                'message': 'リストアイテムが少なすぎます',
                'severity': 'low'
            })
        else:
            issues.append({
                'message': 'リストが含まれていません',
                'severity': 'low'
            })
        
        # コードブロックの存在チェック（技術記事の場合）
        code_blocks = len(re.findall(r'```', content))
        if code_blocks >= 2:  # 開始と終了で2個以上
            score += 10
        
        # 段落の長さチェック
        paragraphs = content.split('\n\n')
        long_paragraphs = [p for p in paragraphs if len(p) > 500]
        if long_paragraphs:
            issues.append({
                'message': f'{len(long_paragraphs)}個の段落が長すぎます',
                'severity': 'low'
            })
        else:
            score += 10
        
        return {
            'score': score,
            'max_score': max_score,
            'issues': issues,
            'passed': score >= 60
        }
    
    def _check_readability(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """読みやすさチェック"""
        score = 0
        max_score = 100
        issues = []
        
        content = article_data.get('content', '')
        if not content:
            return {'score': 0, 'max_score': max_score, 'issues': [{'message': 'コンテンツがありません', 'severity': 'high'}]}
        
        # 文の長さチェック
        sentences = re.split(r'[。！？]', content)
        long_sentences = [s for s in sentences if len(s.strip()) > 100]
        if len(long_sentences) / len(sentences) < 0.2:
            score += 25
        else:
            issues.append({
                'message': '長すぎる文が多すぎます',
                'severity': 'medium'
            })
        
        # 漢字密度チェック（日本語の場合）
        kanji_count = len(re.findall(r'[\u4e00-\u9faf]', content))
        total_chars = len(re.sub(r'\s', '', content))
        if total_chars > 0:
            kanji_density = kanji_count / total_chars
            if 0.2 <= kanji_density <= 0.4:
                score += 25
            else:
                issues.append({
                    'message': f'漢字密度が不適切です: {kanji_density:.2f}',
                    'severity': 'low'
                })
        
        # 専門用語の説明チェック（簡易版）
        technical_terms = ['API', 'SQL', 'HTTP', 'URL', 'OS', 'CPU', 'RAM']
        explained_terms = 0
        for term in technical_terms:
            if term in content:
                # 用語の後に説明らしき文があるかチェック
                pattern = rf'{term}[（\(].*?[）\)]'
                if re.search(pattern, content):
                    explained_terms += 1
        
        if explained_terms > 0:
            score += 15
        
        # 接続詞の使用チェック
        connectives = ['しかし', 'ただし', 'また', 'さらに', 'そのため', 'つまり', 'なお']
        connective_count = sum(content.count(conn) for conn in connectives)
        if connective_count >= 3:
            score += 15
        elif connective_count >= 1:
            score += 10
        else:
            issues.append({
                'message': '接続詞の使用が少なすぎます',
                'severity': 'low'
            })
        
        # 改行・空白行の適切な使用
        empty_lines = len(re.findall(r'\n\s*\n', content))
        if empty_lines >= 5:
            score += 20
        elif empty_lines >= 2:
            score += 15
        else:
            issues.append({
                'message': '改行や空白行が少なすぎます',
                'severity': 'low'
            })
        
        return {
            'score': score,
            'max_score': max_score,
            'issues': issues,
            'passed': score >= 60
        }
    
    def _check_duplicates(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """重複チェック（簡易版）"""
        # 実際の実装では既存の記事データベースと比較
        # ここでは基本的なチェックのみ
        
        issues = []
        title = article_data.get('title', '')
        
        # タイトルの重複パターンチェック
        if title.count('解決方法') > 1:
            issues.append({
                'message': 'タイトルに重複表現があります',
                'severity': 'low'
            })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def _check_links(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """リンク検証（簡易版）"""
        issues = []
        content = article_data.get('content', '')
        
        # Markdownリンクを抽出
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        
        for link_text, url in links:
            # URLの形式チェック
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                issues.append({
                    'message': f'無効なURL形式: {url}',
                    'severity': 'medium'
                })
        
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }