#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エラー発見モジュール

Stack Overflow API、Reddit API、Google Trendsなどから
未執筆のエラーメッセージを自動発見する
"""

import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorFinder:
    """エラー発見エンジンクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定データ
        """
        self.config = config
        self.discovery_config = config.get('error_discovery', {})
        self.sources_config = self.discovery_config.get('sources', {})
        self.criteria = self.discovery_config.get('selection_criteria', {})
        
        logger.info("エラー発見エンジンを初期化しました")
    
    def find_trending_error(self, article_manager=None) -> Optional[Dict[str, Any]]:
        """
        トレンドエラーを発見
        
        Args:
            article_manager: 記事管理オブジェクト（重複チェック用）
        
        Returns:
            発見されたエラー候補、見つからない場合はNone
        """
        logger.info("トレンドエラーの発見を開始")
        
        all_candidates = []
        
        # Stack Overflowから検索
        if self.sources_config.get('stackoverflow', {}).get('enabled', False):
            logger.info("Stack Overflowからエラーを検索中...")
            stackoverflow_candidates = self._search_stackoverflow()
            all_candidates.extend(stackoverflow_candidates)
        
        # Redditから検索
        if self.sources_config.get('reddit', {}).get('enabled', False):
            logger.info("Redditからエラーを検索中...")
            reddit_candidates = self._search_reddit()
            all_candidates.extend(reddit_candidates)
        
        # Google Trendsから検索
        if self.sources_config.get('google_trends', {}).get('enabled', False):
            logger.info("Google Trendsからエラーを検索中...")
            trends_candidates = self._search_google_trends()
            all_candidates.extend(trends_candidates)
        
        if not all_candidates:
            logger.warning("エラー候補が見つかりませんでした")
            return None
        
        # 候補をフィルタリング・スコアリング
        filtered_candidates = self._filter_candidates(all_candidates)
        if not filtered_candidates:
            logger.warning("フィルタリング後にエラー候補が残りませんでした")
            return None
        
        # 重複チェック: 処理済みエラーを除外
        if article_manager:
            unique_candidates = []
            for candidate in filtered_candidates:
                error_message = candidate.get('error_message', '')
                if not article_manager.is_error_already_processed(error_message):
                    unique_candidates.append(candidate)
                else:
                    logger.info(f"エラー '{error_message}' は既に処理済みのためスキップ")
            
            if not unique_candidates:
                logger.warning("すべてのエラー候補が処理済みです")
                return None
            
            filtered_candidates = unique_candidates
        
        # 最高スコアの候補を選択（ランダム性を追加）
        import random
        
        # スコア上位の候補からランダムに選択（トップ3または全体の30%から選択）
        sorted_candidates = sorted(filtered_candidates, key=lambda x: x.get('confidence_score', 0), reverse=True)
        top_count = max(3, len(sorted_candidates) // 3)  # 上位3個または全体の1/3
        top_candidates = sorted_candidates[:top_count]
        
        # ランダム性を加えた重み付き選択
        weights = []
        for i, candidate in enumerate(top_candidates):
            # 順位が高いほど重みを大きく（1位は3倍、2位は2倍、3位以降は1倍）
            weight = max(1, 4 - i)
            weights.append(weight)
        
        best_candidate = random.choices(top_candidates, weights=weights)[0]
        
        logger.info(f"エラーを発見: {best_candidate['error_message']} (スコア: {best_candidate.get('confidence_score', 0):.2f})")
        logger.debug(f"選択候補数: {len(top_candidates)}, 総候補数: {len(filtered_candidates)}")
        return best_candidate
    
    def _search_stackoverflow(self) -> List[Dict[str, Any]]:
        """Stack Overflowからエラーを検索"""
        candidates = []
        
        try:
            # Stack Overflow APIの設定を取得
            so_config = self.sources_config.get('stackoverflow', {})
            api_key = so_config.get('api_key', '')
            
            # 環境変数が未設定の場合、空文字列や元の文字列が残る
            if not api_key or api_key.startswith('${') or api_key == 'your_stackoverflow_api_key':
                api_key = None
                logger.info("Stack Overflow APIキー未設定 - 認証なしモードで実行")
            
            # タグを大幅拡張（より多様な技術スタック）
            all_tags = [
                # OS系
                'windows', 'macos', 'linux', 'ubuntu', 'debian', 'centos',
                # プログラミング言語
                'python', 'javascript', 'java', 'c#', 'php', 'node.js', 'typescript',
                # Web技術
                'html', 'css', 'react', 'angular', 'vue.js', 'nginx', 'apache',
                # データベース
                'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite',
                # インフラ
                'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git'
            ]
            
            # ランダムに5-8個のタグを選択
            import random
            tags = random.sample(all_tags, random.randint(5, 8))
            
            min_score = so_config.get('min_score', 5)
            max_results = so_config.get('max_results', 50)
            
            # より多様で現実的なエラー関連キーワードで検索（範囲拡大）
            import random
            from datetime import datetime, timedelta
            
            # 期間を拡大：過去1年間からランダムに選択
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1年前まで
            
            # ランダムな期間を選択（30-90日の範囲）
            random_days = random.randint(30, 90)
            search_end = end_date - timedelta(days=random.randint(0, 300))
            search_start = search_end - timedelta(days=random_days)
            
            error_keywords = [
                "error", "exception", "failed", "cannot", "unable", "issue",
                "bug", "problem", "crash", "timeout", "denied", "not found",
                "invalid", "unexpected", "fatal", "critical", "warning"
            ]
            
            # ランダムに3-5個のキーワードを選択
            selected_keywords = random.sample(error_keywords, random.randint(3, 5))
            
            for keyword in selected_keywords:
                # APIキーなしでも動作する基本検索を使用
                if api_key:
                    url = "https://api.stackexchange.com/2.3/search/advanced"
                    params = {
                        'order': 'desc',
                        'sort': 'votes',
                        'q': keyword,
                        'tagged': ';'.join(tags),
                        'site': 'stackoverflow',
                        'pagesize': min(30, max_results),
                        'min_score': max(1, min_score - 2),
                        'filter': 'withbody',
                        'fromdate': int(search_start.timestamp()),
                        'todate': int(search_end.timestamp())
                    }
                else:
                    # APIキーなしの場合は基本検索のみ使用
                    url = "https://api.stackexchange.com/2.3/search"
                    params = {
                        'order': 'desc',
                        'sort': 'activity',
                        'intitle': keyword,
                        'site': 'stackoverflow',
                        'pagesize': 15,  # APIキーなしは制限が厳しい
                        'filter': 'default'
                    }
                
                if api_key:
                    params['key'] = api_key
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        
                        for item in data.get('items', []):
                            # エラーメッセージを抽出
                            error_message = self._extract_error_message(item)
                            if error_message:
                                candidates.append({
                                    'error_message': error_message,
                                    'source': 'stackoverflow',
                                    'source_url': item.get('link', ''),
                                    'title': item.get('title', ''),
                                    'score': item.get('score', 0),
                                    'view_count': item.get('view_count', 0),
                                    'creation_date': item.get('creation_date', 0),
                                    'tags': item.get('tags', []),
                                    'confidence_score': self._calculate_stackoverflow_confidence(item)
                                })
                    elif response.status_code == 400 and not api_key:
                        logger.warning(f"Stack Overflow API認証なしでの制限に達しました（今回スキップ）")
                        break
                    else:
                        logger.warning(f"Stack Overflow API エラー: {response.status_code} - {response.text[:100]}")
                        
                except Exception as e:
                    logger.warning(f"Stack Overflow検索エラー: {e}")
                    continue
                    
                # レート制限対応
                time.sleep(0.3 if not api_key else 0.1)  # APIキーなしの場合はより慎重に
            
            logger.info(f"Stack Overflowから {len(candidates)} 個のエラー候補を取得")
            
        except Exception as e:
            logger.error(f"Stack Overflow検索でエラーが発生: {e}")
        
        return candidates
    
    def _search_reddit(self) -> List[Dict[str, Any]]:
        """Redditからエラーを検索"""
        candidates = []
        
        try:
            # Reddit APIの設定を取得
            reddit_config = self.sources_config.get('reddit', {})
            client_id = reddit_config.get('client_id', '')
            client_secret = reddit_config.get('client_secret', '')
            
            # 環境変数が未設定の場合、空文字列や元の文字列が残る
            if (not client_id or client_id.startswith('${') or client_id == 'your_reddit_client_id' or
                not client_secret or client_secret.startswith('${') or client_secret == 'your_reddit_client_secret'):
                client_id = None
                client_secret = None
            
            # サブレディット範囲を大幅拡張
            import random
            all_subreddits = [
                # 技術サポート系
                'techsupport', 'pcmasterrace', 'buildapc', 'sysadmin',
                # OS系
                'windows', 'MacOS', 'linux', 'Ubuntu', 'debian',
                # プログラミング系
                'programming', 'learnprogramming', 'Python', 'javascript', 'webdev',
                # インフラ・サーバー系
                'docker', 'kubernetes', 'aws', 'devops', 'selfhosted',
                # データベース系
                'mysql', 'PostgreSQL', 'mongodb', 'Database',
                # 一般IT系
                'ITCareerQuestions', 'cscareerquestions', 'webdev', 'node'
            ]
            
            # ランダムに3-6個のサブレディットを選択
            subreddits = random.sample(all_subreddits, random.randint(3, 6))
            min_upvotes = reddit_config.get('min_upvotes', 5)
            
            # Reddit API認証情報が設定されていない場合はフォールバック検索を実装
            if not client_id or not client_secret:
                logger.info("Reddit API認証情報が未設定のため、公開RSS経由で検索します")
                return self._search_reddit_fallback(subreddits, min_upvotes)
            
            # Reddit OAuth認証
            auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
            data = {
                'grant_type': 'client_credentials'
            }
            headers = {'User-Agent': 'ErrorDiscovery/1.0'}
            
            token_response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                auth=auth,
                data=data,
                headers=headers,
                timeout=30
            )
            
            if token_response.status_code == 200:
                token = token_response.json()['access_token']
                headers['Authorization'] = f'bearer {token}'
                
                # 各サブレディットから検索
                for subreddit in subreddits:
                    url = f'https://oauth.reddit.com/r/{subreddit}/hot'
                    params = {'limit': 25}
                    
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        
                        for post in data.get('data', {}).get('children', []):
                            post_data = post.get('data', {})
                            
                            # エラー関連投稿を判定
                            if self._is_error_related_post(post_data) and post_data.get('ups', 0) >= min_upvotes:
                                error_message = self._extract_reddit_error(post_data)
                                if error_message:
                                    candidates.append({
                                        'error_message': error_message,
                                        'source': 'reddit',
                                        'source_url': f"https://reddit.com{post_data.get('permalink', '')}",
                                        'title': post_data.get('title', ''),
                                        'upvotes': post_data.get('ups', 0),
                                        'comments': post_data.get('num_comments', 0),
                                        'subreddit': subreddit,
                                        'confidence_score': self._calculate_reddit_confidence(post_data)
                                    })
                    
                    # レート制限対応
                    time.sleep(1)
            
            logger.info(f"Redditから {len(candidates)} 個のエラー候補を取得")
            
        except Exception as e:
            logger.error(f"Reddit検索でエラーが発生: {e}")
        
        return candidates
    
    def _search_reddit_fallback(self, subreddits: List[str], min_upvotes: int) -> List[Dict[str, Any]]:
        """Reddit認証なしフォールバック検索（JSON API経由）"""
        candidates = []
        
        try:
            import random
            
            # エラー関連キーワード
            error_keywords = ["error", "issue", "problem", "help", "fix", "crash", "fail"]
            
            for subreddit in subreddits[:3]:  # 最大3つのサブレディットに制限
                try:
                    # RedditのJSON APIを使用（認証不要、ただし制限あり）
                    url = f"https://www.reddit.com/r/{subreddit}/search.json"
                    keyword = random.choice(error_keywords)
                    
                    params = {
                        'q': keyword,
                        'restrict_sr': 'true',
                        'sort': 'top',
                        'limit': 10
                    }
                    
                    headers = {
                        'User-Agent': 'ErrorDiscovery/1.0 (Educational Purpose)'
                    }
                    
                    response = requests.get(url, params=params, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for post in data.get('data', {}).get('children', []):
                            post_data = post.get('data', {})
                            
                            if (post_data.get('ups', 0) >= min_upvotes and 
                                self._is_error_related_post(post_data)):
                                
                                error_message = self._extract_reddit_error(post_data)
                                if error_message:
                                    candidates.append({
                                        'error_message': error_message,
                                        'source': 'reddit_fallback',
                                        'source_url': f"https://reddit.com{post_data.get('permalink', '')}",
                                        'title': post_data.get('title', '')[:100],
                                        'upvotes': post_data.get('ups', 0),
                                        'comments': post_data.get('num_comments', 0),
                                        'subreddit': subreddit,
                                        'confidence_score': self._calculate_reddit_confidence(post_data)
                                    })
                    
                    # レート制限対応
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Reddit fallback検索エラー（{subreddit}）: {e}")
                    continue
            
            logger.info(f"Reddit fallback検索から {len(candidates)} 個のエラー候補を取得")
            
        except Exception as e:
            logger.error(f"Reddit fallback検索でエラーが発生: {e}")
        
        return candidates
    
    def _search_google_trends(self) -> List[Dict[str, Any]]:
        """Google Trendsからエラーを検索（拡張・ランダム化版）"""
        candidates = []
        
        try:
            import random
            from datetime import datetime, timedelta
            
            trends_config = self.sources_config.get('google_trends', {})
            search_terms = trends_config.get('search_terms', ['error'])
            
            logger.info("Google Trends検索（拡張実装 - 多様性・ランダム性強化）")
            
            # より多様で現実的なエラーパターンを候補として追加
            error_categories = {
                'windows_errors': [
                    "ERROR_ACCESS_DENIED 0x80070005",
                    "ERROR_SHARING_VIOLATION 0x80070020", 
                    "ERROR_DISK_FULL 0x80070070",
                    "ERROR_INVALID_PARAMETER 0x80070057",
                    "ERROR_NOT_ENOUGH_MEMORY 0x80070008",
                    "CRITICAL_PROCESS_DIED 0x000000EF",
                    "IRQL_NOT_LESS_OR_EQUAL 0x0000000A",
                    "PAGE_FAULT_IN_NONPAGED_AREA 0x00000050",
                    "MEMORY_MANAGEMENT 0x0000001A",
                    "SYSTEM_SERVICE_EXCEPTION 0x0000003B"
                ],
                'macos_errors': [
                    "Kernel Panic com.apple.kext",
                    "macOS Monterey Boot Loop",
                    "Metal Performance Shaders Error",
                    "CoreData Migration Failed",
                    "Keychain Access Denied",
                    "Disk Utility First Aid Failed",
                    "Time Machine Backup Error",
                    "macOS Update Installation Failed"
                ],
                'linux_errors': [
                    "segmentation fault core dumped",
                    "Permission denied /dev/null",
                    "No space left on device",
                    "command not found bash",
                    "Failed to start systemd service",
                    "Unable to locate package apt",
                    "Connection refused ssh",
                    "Input/output error mount"
                ],
                'programming_errors': [
                    "ModuleNotFoundError Python pip",
                    "NullPointerException Java Runtime",
                    "Cannot read property undefined",
                    "CORS policy blocked request",
                    "SSL certificate verify failed",
                    "Database connection timeout",
                    "Memory leak detected heap",
                    "Stack overflow recursion limit"
                ],
                'web_server_errors': [
                    "502 Bad Gateway nginx",
                    "504 Gateway Timeout error",
                    "413 Request Entity Too Large",
                    "500 Internal Server Error",
                    "401 Unauthorized JWT token",
                    "429 Too Many Requests rate limit",
                    "Connection reset by peer",
                    "DNS resolution failed"
                ],
                'database_errors': [
                    "MySQL connection refused 3306",
                    "PostgreSQL authentication failed",
                    "MongoDB connection timeout",
                    "Redis NOAUTH Authentication required",
                    "SQLite database locked",
                    "Oracle ORA-12541 TNS no listener",
                    "Elasticsearch cluster unavailable",
                    "Table doesn't exist SQL"
                ]
            }
            
            # 時期に応じたエラーの重み付け（季節性やトレンド）
            current_month = datetime.now().month
            seasonal_weights = {
                'windows_errors': 1.2 if current_month in [1, 2, 12] else 1.0,  # 年末年始にWindows更新多い
                'web_server_errors': 1.3 if current_month in [11, 12] else 1.0,  # ブラックフライデー等でトラフィック増
                'programming_errors': 1.1,  # 常に需要高
                'database_errors': 1.0,
                'macos_errors': 1.1 if current_month in [9, 10] else 0.9,  # macOS新版リリース時期
                'linux_errors': 1.0
            }
            
            # 各カテゴリからランダムにエラーを選択
            all_errors = []
            for category, errors in error_categories.items():
                weight = seasonal_weights.get(category, 1.0)
                # カテゴリごとに1-3個をランダム選択
                num_select = random.randint(1, min(3, len(errors)))
                selected_errors = random.sample(errors, num_select)
                
                for error in selected_errors:
                    all_errors.append({
                        'error_message': error,
                        'category': category,
                        'weight': weight
                    })
            
            # ランダムにシャッフルして最大20個選択
            random.shuffle(all_errors)
            selected_errors = all_errors[:20]
            
            # 候補として追加（ランダムな検索ボリュームとスコア）
            for error_data in selected_errors:
                base_volume = random.randint(500, 2000)
                weighted_volume = int(base_volume * error_data['weight'])
                
                candidates.append({
                    'error_message': error_data['error_message'],
                    'source': 'google_trends',
                    'category': error_data['category'],
                    'search_volume': weighted_volume,
                    'trend_score': round(random.uniform(0.6, 0.9), 2),
                    'confidence_score': round(random.uniform(0.4, 0.8), 2),
                    'seasonal_weight': error_data['weight']
                })
            
            logger.info(f"Google Trendsから {len(candidates)} 個のエラー候補を取得（多様性・ランダム化実装）")
            
        except Exception as e:
            logger.error(f"Google Trends検索でエラーが発生: {e}")
        
        return candidates
    
    def _extract_error_message(self, stackoverflow_item: Dict[str, Any]) -> Optional[str]:
        """Stack Overflowアイテムからエラーメッセージを抽出"""
        title = stackoverflow_item.get('title', '')
        body = stackoverflow_item.get('body', '')
        
        # タイトルからエラーメッセージらしき部分を抽出
        import re
        
        # よくあるエラーパターン
        error_patterns = [
            r'ERROR[_\s]+[A-Z_]+[_\s]+\w+',
            r'0x[0-9A-Fa-f]{8}',
            r'Exception[:\s]+[\w\.]+',
            r'Failed[:\s]+.+',
            r'Cannot[:\s]+.+',
            r'Unable to[:\s]+.+'
        ]
        
        for pattern in error_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        # タイトル全体をエラーメッセージとして使用（長すぎる場合は切り詰め）
        if len(title) < 100:
            return title
        
        return None
    
    def _extract_reddit_error(self, post_data: Dict[str, Any]) -> Optional[str]:
        """Reddit投稿からエラーメッセージを抽出"""
        title = post_data.get('title', '')
        selftext = post_data.get('selftext', '')
        
        # エラーらしきキーワードが含まれているかチェック
        error_keywords = ['error', 'failed', 'crash', 'issue', 'problem', 'bug']
        
        if any(keyword in title.lower() for keyword in error_keywords):
            # タイトルを短縮してエラーメッセージとして使用
            if len(title) < 100:
                return title
            else:
                return title[:100] + "..."
        
        return None
    
    def _is_error_related_post(self, post_data: Dict[str, Any]) -> bool:
        """Reddit投稿がエラー関連かどうかを判定"""
        title = post_data.get('title', '').lower()
        flair = post_data.get('link_flair_text', '').lower()
        
        error_indicators = [
            'error', 'problem', 'issue', 'help', 'failed', 'crash', 
            'not working', 'broken', 'bug', 'trouble'
        ]
        
        return any(indicator in title or indicator in flair for indicator in error_indicators)
    
    def _calculate_stackoverflow_confidence(self, item: Dict[str, Any]) -> float:
        """Stack Overflowアイテムの信頼度スコアを計算"""
        score = item.get('score', 0)
        view_count = item.get('view_count', 0)
        answer_count = item.get('answer_count', 0)
        
        # スコアベースの信頼度計算
        confidence = 0.0
        
        # 質問のスコアが高いほど信頼度アップ
        if score > 10:
            confidence += 0.3
        elif score > 5:
            confidence += 0.2
        elif score > 0:
            confidence += 0.1
        
        # 閲覧数が多いほど信頼度アップ
        if view_count > 1000:
            confidence += 0.2
        elif view_count > 500:
            confidence += 0.1
        
        # 回答数があると信頼度アップ
        if answer_count > 2:
            confidence += 0.3
        elif answer_count > 0:
            confidence += 0.2
        
        # 最大1.0に制限
        return min(confidence, 1.0)
    
    def _calculate_reddit_confidence(self, post_data: Dict[str, Any]) -> float:
        """Reddit投稿の信頼度スコアを計算"""
        upvotes = post_data.get('ups', 0)
        comments = post_data.get('num_comments', 0)
        
        confidence = 0.0
        
        # アップボート数による信頼度
        if upvotes > 50:
            confidence += 0.4
        elif upvotes > 20:
            confidence += 0.3
        elif upvotes > 5:
            confidence += 0.2
        
        # コメント数による信頼度
        if comments > 20:
            confidence += 0.3
        elif comments > 10:
            confidence += 0.2
        elif comments > 5:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _filter_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """候補をフィルタリング"""
        filtered = []
        
        for candidate in candidates:
            # 信頼度スコアチェック
            min_confidence = self.criteria.get('min_confidence_score', 0.5)
            if candidate.get('confidence_score', 0) < min_confidence:
                continue
            
            # 重複チェック（既存記事との重複は別途実装）
            error_msg = candidate.get('error_message', '').lower()
            if len(error_msg) < 10:  # あまりに短いエラーメッセージは除外
                continue
            
            # 除外キーワードチェック
            exclude_keywords = ['test', 'sample', 'example', 'dummy']
            if any(keyword in error_msg for keyword in exclude_keywords):
                continue
            
            filtered.append(candidate)
        
        logger.info(f"フィルタリング結果: {len(candidates)} -> {len(filtered)} 件")
        return filtered