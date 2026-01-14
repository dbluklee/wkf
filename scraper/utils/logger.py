"""
로깅 설정 유틸리티

컬러 로그 및 파일 로그를 지원합니다.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import colorlog


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    name: Optional[str] = None
) -> logging.Logger:
    """
    로거 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (선택사항)
        name: 로거 이름 (선택사항)

    Returns:
        설정된 Logger 객체
    """
    logger = logging.getLogger(name or __name__)

    # 이미 핸들러가 설정되어 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    logger.setLevel(getattr(logging, log_level.upper()))
    # 모든 로거가 루트 로거의 핸들러를 사용하도록 propagate = True로 설정
    if name:  # 이름이 지정된 로거인 경우
        logger.propagate = True
    else:  # 루트 로거인 경우
        logger.propagate = False

    # 간단한 포맷터 (colorlog 대신 기본 포맷터 사용)
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러 (unbuffered stream 사용)
    # sys.stderr를 사용하여 버퍼링 문제 해결
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)

    # 강제 flush
    logging.getLogger().handlers[0].flush() if logging.getLogger().handlers else None

    # 파일 핸들러 (옵션)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    이름으로 로거 가져오기

    Args:
        name: 로거 이름

    Returns:
        Logger 객체
    """
    return logging.getLogger(name)
