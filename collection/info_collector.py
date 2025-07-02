#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情報収集モジュール

エラー候補に対して英語圏から解決情報を収集し、
翻訳・統合処理を行う
"""

import time
import logging
import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class InfoCollector:
    """情報収集エンジンクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.timeouts = config.get('external_services', {}).get('timeouts', {})
        self.rate_limits = config.get('external_services', {}).get('rate_limits', {})
        
        logger.info("情報収集エンジンを初期化しました")
    
    def collect_solution_info(self, error_candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        エラー候補に対する解決情報を収集
        
        Args:
            error_candidate: エラー候補データ
            
        Returns:
            収集された解決情報、失敗時はNone
        """
        error_message = error_candidate.get('error_message', '')
        logger.info(f"解決情報の収集を開始: {error_message}")
        
        try:
            all_solutions = []
            all_sources = []
            
            # Microsoft Learn から検索
            logger.info("Microsoft Learn から情報収集中...")
            ms_solutions, ms_sources = self._search_microsoft_learn(error_message)
            all_solutions.extend(ms_solutions)
            all_sources.extend(ms_sources)
            
            # Stack Overflow から検索（既存のエラー候補以外）
            logger.info("Stack Overflow から追加情報収集中...")
            so_solutions, so_sources = self._search_stackoverflow_solutions(error_message)
            all_solutions.extend(so_solutions)
            all_sources.extend(so_sources)
            
            # Apple Support から検索（macOS関連の場合）
            if self._is_macos_error(error_message):
                logger.info("Apple Support から情報収集中...")
                apple_solutions, apple_sources = self._search_apple_support(error_message)
                all_solutions.extend(apple_solutions)
                all_sources.extend(apple_sources)
            
            # 収集した情報を統合・評価
            if not all_solutions:
                logger.warning("解決情報が見つかりませんでした")
                return None
            
            # 情報を統合
            integrated_info = self._integrate_information(
                error_candidate, all_solutions, all_sources
            )
            
            logger.info(f"解決情報の収集完了: {len(all_solutions)}個の解決策を収集")
            return integrated_info
            
        except Exception as e:
            logger.error(f"情報収集中にエラーが発生: {e}")
            return None
    
    def _search_microsoft_learn(self, error_message: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Microsoft Learn から情報を検索"""
        solutions = []
        sources = []
        
        try:
            # Microsoft Learn の検索URL
            search_url = "https://docs.microsoft.com/en-us/search/"
            params = {
                'search': error_message,
                'scope': 'Windows'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(
                search_url, 
                params=params, 
                headers=headers,
                timeout=self.timeouts.get('web_scraping', 60)
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 検索結果を解析（実際のHTMLに応じて調整が必要）
                results = soup.find_all('div', class_='search-result')
                
                for result in results[:5]:  # 上位5件を取得
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    snippet_elem = result.find('p')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        # 詳細ページから解決策を抽出
                        solution = self._extract_solution_from_page(url, 'microsoft')
                        if solution:
                            solution['source_title'] = title
                            solution['source_url'] = url
                            solutions.append(solution)
                        
                        # ソース情報を追加
                        sources.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet,
                            'type': 'official',
                            'reliability': 1.0
                        })
            
            logger.info(f"Microsoft Learn から {len(solutions)} 個の解決策を取得")
            
        except Exception as e:
            logger.warning(f"Microsoft Learn 検索でエラー: {e}")
        
        return solutions, sources
    
    def _search_stackoverflow_solutions(self, error_message: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Stack Overflow から解決策を検索"""
        solutions = []
        sources = []
        
        try:
            # Stack Overflow API で解決済み質問を検索
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                'order': 'desc',
                'sort': 'votes',
                'q': error_message,
                'site': 'stackoverflow',
                'pagesize': 10,
                'filter': 'withbody',
                'accepted': 'True'  # 解決済みのみ
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    # 回答を取得
                    answers_url = f"https://api.stackexchange.com/2.3/questions/{item['question_id']}/answers"
                    answers_params = {
                        'order': 'desc',
                        'sort': 'votes',
                        'site': 'stackoverflow',
                        'filter': 'withbody'
                    }
                    
                    answers_response = requests.get(answers_url, params=answers_params, timeout=30)
                    if answers_response.status_code == 200:
                        answers_data = answers_response.json()
                        
                        for answer in answers_data.get('items', [])[:3]:  # 上位3件の回答
                            if answer.get('is_accepted') or answer.get('score', 0) > 5:
                                solution = {
                                    'description': f"Stack Overflow解決策 (スコア: {answer.get('score', 0)})",
                                    'steps': self._extract_steps_from_html(answer.get('body', '')),
                                    'reliability': min(0.9, 0.5 + answer.get('score', 0) * 0.05),
                                    'source_url': item.get('link', ''),
                                    'source_title': item.get('title', ''),
                                    'answer_score': answer.get('score', 0)
                                }
                                solutions.append(solution)
                    
                    # ソース情報を追加
                    sources.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': self._extract_snippet_from_html(item.get('body', '')),
                        'type': 'community',
                        'reliability': 0.8,
                        'score': item.get('score', 0)
                    })
                    
                    # レート制限対応
                    time.sleep(0.1)
            
            logger.info(f"Stack Overflow から {len(solutions)} 個の解決策を取得")
            
        except Exception as e:
            logger.warning(f"Stack Overflow 検索でエラー: {e}")
        
        return solutions, sources
    
    def _search_apple_support(self, error_message: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Apple Support から情報を検索"""
        solutions = []
        sources = []
        
        try:
            # Apple Support Communities の検索
            search_url = "https://discussions.apple.com/search"
            params = {
                'q': error_message
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(
                search_url,
                params=params,
                headers=headers,
                timeout=self.timeouts.get('web_scraping', 60)
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 検索結果を解析（実際のHTMLに応じて調整）
                results = soup.find_all('div', class_='search-result-item')
                
                for result in results[:3]:  # 上位3件
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        # Apple公式の情報か判定
                        is_official = 'support.apple.com' in url
                        reliability = 1.0 if is_official else 0.7
                        
                        sources.append({
                            'title': title,
                            'url': url,
                            'type': 'official' if is_official else 'community',
                            'reliability': reliability
                        })
            
            logger.info(f"Apple Support から {len(sources)} 個のソースを取得")
            
        except Exception as e:
            logger.warning(f"Apple Support 検索でエラー: {e}")
        
        return solutions, sources
    
    def _extract_solution_from_page(self, url: str, source_type: str) -> Optional[Dict[str, Any]]:
        """Webページから解決策を抽出"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # ページタイトルを取得
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else ''
                
                # 本文を取得（サイトごとに要調整）
                content_selectors = {
                    'microsoft': ['.content', 'main', 'article'],
                    'apple': ['.content', '.article-content'],
                    'default': ['main', 'article', '.content']
                }
                
                selectors = content_selectors.get(source_type, content_selectors['default'])
                content_text = ''
                
                for selector in selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        content_text = content_elem.get_text(strip=True)
                        break
                
                if content_text and len(content_text) > 100:
                    return {
                        'description': f"Webページからの解決策: {title_text}",
                        'steps': content_text[:1000],  # 最初の1000文字
                        'reliability': 0.8 if source_type == 'microsoft' else 0.6,
                        'source_url': url,
                        'source_title': title_text
                    }
            
        except Exception as e:
            logger.warning(f"ページからの解決策抽出でエラー: {e}")
        
        return None
    
    def _extract_steps_from_html(self, html_content: str) -> str:
        """HTMLコンテンツから手順を抽出"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # コードブロック、リスト、段落から手順を抽出
            steps = []
            
            # コードブロックを取得
            code_blocks = soup.find_all(['code', 'pre'])
            for code in code_blocks:
                code_text = code.get_text(strip=True)
                if code_text:
                    steps.append(f"コマンド: {code_text}")
            
            # リストアイテムを取得
            list_items = soup.find_all(['li', 'ol', 'ul'])
            for item in list_items:
                item_text = item.get_text(strip=True)
                if item_text and len(item_text) < 200:
                    steps.append(item_text)
            
            # 段落を取得（短いもののみ）
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if p_text and 20 < len(p_text) < 200:
                    steps.append(p_text)
            
            return '\n'.join(steps[:10])  # 最大10ステップ
            
        except Exception as e:
            logger.warning(f"HTML手順抽出でエラー: {e}")
            return html_content[:500] if html_content else ''
    
    def _extract_snippet_from_html(self, html_content: str) -> str:
        """HTMLから要約を抽出"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(strip=True)
            
            # 最初の200文字を返す
            return text[:200] + '...' if len(text) > 200 else text
            
        except Exception:
            return html_content[:200] if html_content else ''
    
    def _is_macos_error(self, error_message: str) -> bool:
        """エラーメッセージがmacOS関連かどうかを判定"""
        macos_keywords = [
            'macos', 'mac os', 'darwin', 'kernel panic', 
            'cocoa', 'xcode', 'safari', 'finder'
        ]
        
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in macos_keywords)
    
    def _integrate_information(
        self, 
        error_candidate: Dict[str, Any], 
        solutions: List[Dict[str, Any]], 
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """収集した情報を統合"""
        
        # 解決策を信頼度でソート
        solutions.sort(key=lambda x: x.get('reliability', 0), reverse=True)
        
        # 重複除去（URLベース）
        seen_urls = set()
        unique_sources = []
        for source in sources:
            url = source.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(source)
        
        # 統合結果を生成
        integrated_info = {
            'error_message': error_candidate.get('error_message', ''),
            'error_candidate': error_candidate,
            'solutions': solutions[:10],  # 上位10個の解決策
            'sources': unique_sources[:15],  # 上位15個のソース
            'collection_summary': {
                'total_solutions': len(solutions),
                'total_sources': len(unique_sources),
                'collection_time': time.time(),
                'reliability_scores': [s.get('reliability', 0) for s in solutions],
                'avg_reliability': sum(s.get('reliability', 0) for s in solutions) / len(solutions) if solutions else 0
            }
        }
        
        return integrated_info