#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動エラー解決記事生成システム - メインエントリーポイント

未執筆のエラーメッセージを自動発見し、英語圏の解決情報を収集・翻訳して、
SEO最適化された日本語WordPress記事を完全自動生成・投稿するシステム
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from utils.logger import setup_logger
from utils.article_manager import ArticleManager
from discovery.error_finder import ErrorFinder
from collection.info_collector import InfoCollector
from generation.article_generator import ArticleGenerator
from publication.wordpress_publisher import WordPressPublisher
from publication.quality_checker import QualityChecker

logger = logging.getLogger(__name__)


class AutoErrorArticleGenerator:
    """自動エラー解決記事生成システム メインクラス"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # 各モジュールの初期化
        self.article_manager = ArticleManager()
        self.error_finder = ErrorFinder(self.config)
        self.info_collector = InfoCollector(self.config)
        self.article_generator = ArticleGenerator(self.config)
        self.wordpress_publisher = WordPressPublisher(self.config)
        self.quality_checker = QualityChecker(self.config)
        
        logger.info("自動エラー解決記事生成システムを初期化しました")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        import yaml
        import re
        from dotenv import load_dotenv
        
        # .envファイルから環境変数を読み込む
        env_file = project_root / "config" / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"環境変数ファイルを読み込みました: {env_file}")
        
        config_file = project_root / self.config_path
        if not config_file.exists():
            logger.error(f"設定ファイルが見つかりません: {config_file}")
            sys.exit(1)
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 環境変数の展開
            def replace_env_vars(match):
                env_var = match.group(1)
                return os.environ.get(env_var, match.group(0))
            
            content = re.sub(r'\$\{([^}]+)\}', replace_env_vars, content)
            config = yaml.safe_load(content)
            
            logger.info(f"設定ファイルを読み込みました: {config_file}")
            return config
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
            sys.exit(1)
    
    def run_full_cycle(self) -> Dict[str, Any]:
        """
        完全な自動実行サイクルを実行
        
        Returns:
            実行結果
        """
        logger.info("=== 自動エラー解決記事生成システム 開始 ===")
        
        try:
            # Phase 1: エラー発見
            logger.info("Phase 1: エラー発見を開始")
            error_candidate = self.error_finder.find_trending_error(self.article_manager)
            if not error_candidate:
                logger.warning("新しいエラーが見つかりませんでした")
                return {"status": "no_error_found"}
            
            logger.info(f"発見したエラー: {error_candidate['error_message']}")
            
            # Phase 2: 情報収集
            logger.info("Phase 2: 情報収集を開始")
            solution_info = self.info_collector.collect_solution_info(error_candidate)
            if not solution_info:
                logger.error("解決情報の収集に失敗しました")
                return {"status": "info_collection_failed"}
            
            # Phase 3: 記事生成
            logger.info("Phase 3: 記事生成を開始")
            article_data = self.article_generator.generate_article(solution_info)
            if not article_data:
                logger.error("記事生成に失敗しました")
                return {"status": "article_generation_failed"}
            
            # Phase 4: 品質チェック
            logger.info("Phase 4: 品質チェックを開始")
            quality_result = self.quality_checker.check_quality(article_data)
            if not quality_result['passed']:
                logger.warning(f"品質チェックに合格しませんでした: {quality_result['issues']}")
                # 品質が低い場合でも続行するかはconfigで設定
                if not self.config.get('quality', {}).get('allow_low_quality', False):
                    return {"status": "quality_check_failed", "issues": quality_result['issues']}
            
            # Phase 5: 連番ディレクトリ作成・データ保存
            logger.info("Phase 5: 記事データ保存を開始")
            article_dir = self.article_manager.create_article_directory(error_candidate['error_message'])
            self.article_manager.save_article_data(article_dir, {
                'article': article_data,
                'sources': solution_info,
                'quality': quality_result,
                'error_candidate': error_candidate
            })
            
            # Phase 6: WordPress投稿
            logger.info("Phase 6: WordPress投稿を開始") 
            if self.config.get('wordpress', {}).get('auto_publish', True):
                publication_result = self.wordpress_publisher.publish_article(article_data)
                if publication_result:
                    logger.info(f"WordPress投稿成功: {publication_result['link']}")
                    # 投稿結果を保存
                    self.article_manager.save_wordpress_result(article_dir, publication_result)
                else:
                    logger.error("WordPress投稿に失敗しました")
                    return {"status": "wordpress_publish_failed"}
            else:
                logger.info("WordPress自動投稿は無効化されています")
                publication_result = None
            
            # 成功結果を返す
            result = {
                "status": "success",
                "article_directory": str(article_dir),
                "error_message": error_candidate['error_message'],
                "article_title": article_data['title'],
                "quality_score": quality_result.get('seo_score', 0),
                "wordpress_url": publication_result['link'] if publication_result else None
            }
            
            logger.info("=== 処理完了 ===")
            return result
            
        except Exception as e:
            logger.error(f"システム実行中にエラーが発生しました: {e}")
            return {"status": "system_error", "error": str(e)}
    
    def discover_error_only(self) -> Optional[Dict[str, Any]]:
        """エラー発見のみ実行（テスト用）"""
        logger.info("エラー発見のみ実行")
        return self.error_finder.find_trending_error()
    
    def generate_article_from_error(self, error_message: str) -> Dict[str, Any]:
        """
        指定されたエラーメッセージから記事を生成
        
        Args:
            error_message: エラーメッセージ
            
        Returns:
            実行結果
        """
        logger.info(f"指定エラーから記事生成: {error_message}")
        
        # 手動エラー候補を作成
        error_candidate = {
            'error_message': error_message,
            'source': 'manual',
            'confidence_score': 1.0,
            'search_volume': 0,
            'competition_level': 'unknown'
        }
        
        # 情報収集以降の処理を実行
        solution_info = self.info_collector.collect_solution_info(error_candidate)
        if not solution_info:
            return {"status": "info_collection_failed"}
        
        article_data = self.article_generator.generate_article(solution_info)
        if not article_data:
            return {"status": "article_generation_failed"}
        
        # 記事データ保存
        article_dir = self.article_manager.create_article_directory(error_message)
        self.article_manager.save_article_data(article_dir, {
            'article': article_data,
            'sources': solution_info,
            'error_candidate': error_candidate
        })
        
        return {
            "status": "success",
            "article_directory": str(article_dir),
            "article_title": article_data['title']
        }


def setup_argument_parser() -> argparse.ArgumentParser:
    """コマンドライン引数パーサーを設定"""
    parser = argparse.ArgumentParser(
        description='自動エラー解決記事生成システム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py                                    # 完全自動実行
  python main.py --discover                         # エラー発見のみ
  python main.py --error "FILE_NOT_FOUND 0x80070002"  # 指定エラーから記事生成
  python main.py --config custom_config.yaml       # カスタム設定で実行
  python main.py --debug                            # デバッグモードで実行
        """
    )
    
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='設定ファイルパス'
    )
    
    parser.add_argument(
        '--discover',
        action='store_true',
        help='エラー発見のみ実行（テスト用）'
    )
    
    parser.add_argument(
        '--error',
        help='指定されたエラーメッセージから記事を生成'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='デバッグモードで実行'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='詳細ログを出力'
    )
    
    return parser


def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # ログの設定
    log_level = logging.DEBUG if args.debug or args.verbose else logging.INFO
    setup_logger(log_level)
    
    logger.info("=== 自動エラー解決記事生成システム 開始 ===")
    
    try:
        # システムの初期化
        generator = AutoErrorArticleGenerator(args.config)
        
        # 実行モードに応じて処理
        if args.discover:
            # エラー発見のみ
            result = generator.discover_error_only()
            if result:
                print(f"発見したエラー: {result['error_message']}")
                print(f"信頼度スコア: {result.get('confidence_score', 'N/A')}")
            else:
                print("新しいエラーは見つかりませんでした")
                
        elif args.error:
            # 指定エラーから記事生成
            result = generator.generate_article_from_error(args.error)
            print(f"実行結果: {result['status']}")
            if result['status'] == 'success':
                print(f"記事ディレクトリ: {result['article_directory']}")
                print(f"記事タイトル: {result['article_title']}")
                
        else:
            # 完全自動実行
            result = generator.run_full_cycle()
            print(f"実行結果: {result['status']}")
            
            if result['status'] == 'success':
                print(f"記事ディレクトリ: {result['article_directory']}")
                print(f"エラーメッセージ: {result['error_message']}")
                print(f"記事タイトル: {result['article_title']}")
                print(f"品質スコア: {result['quality_score']}")
                if result['wordpress_url']:
                    print(f"WordPress URL: {result['wordpress_url']}")
            else:
                print(f"エラー詳細: {result.get('error', 'N/A')}")
        
        logger.info("=== 処理完了 ===")
        
    except KeyboardInterrupt:
        logger.info("ユーザーによって処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()