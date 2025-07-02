#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ管理モジュール

システム全体のログ設定と管理を担当
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logger(level: int = logging.INFO, 
                config: Optional[dict] = None) -> logging.Logger:
    """
    ログの設定を行う
    
    Args:
        level: ログレベル
        config: ログ設定（オプション）
        
    Returns:
        設定されたロガー
    """
    # ログ設定のデフォルト値
    log_config = {
        'level': level,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_output': True,
        'log_file': 'logs/auto_error_generator.log',
        'max_log_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    # 設定が提供された場合は更新
    if config:
        log_config.update(config.get('logging', {}))
    
    # ルートロガーを取得
    logger = logging.getLogger()
    
    # 既存のハンドラをクリア
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # ログレベルを設定
    logger.setLevel(log_config['level'])
    
    # フォーマッタを作成
    formatter = logging.Formatter(log_config['format'])
    
    # コンソールハンドラを追加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_config['level'])
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラを追加（設定されている場合）
    if log_config.get('file_output', False):
        try:
            # ログディレクトリを作成
            log_file_path = Path(log_config['log_file'])
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ローテーティングファイルハンドラを作成
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=log_config['max_log_size'],
                backupCount=log_config['backup_count'],
                encoding='utf-8'
            )
            file_handler.setLevel(log_config['level'])
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"ログファイルを設定: {log_file_path}")
            
        except Exception as e:
            logger.warning(f"ファイルハンドラの設定に失敗しました: {e}")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    名前付きロガーを取得
    
    Args:
        name: ロガー名
        
    Returns:
        ロガー
    """
    return logging.getLogger(name)


class LoggerMixin:
    """ロガーミックスインクラス"""
    
    @property
    def logger(self) -> logging.Logger:
        """ロガーを取得"""
        return logging.getLogger(self.__class__.__name__)


# プロジェクト固有のロガー設定
def setup_project_logger() -> None:
    """プロジェクト固有のロガー設定"""
    
    # 特定のライブラリのログレベルを調整
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    # HTTPリクエストの詳細ログを無効化
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)


# モジュールレベルでの初期設定
if __name__ != "__main__":
    setup_project_logger()