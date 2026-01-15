"""
로깅 유틸리티
"""
import logging
import colorlog
from pathlib import Path


def get_logger(name: str, log_file: str = "logs/disclosure-scraper.log", level: str = "INFO") -> logging.Logger:
    """
    컬러 로거 생성

    Args:
        name: 로거 이름
        log_file: 로그 파일 경로
        level: 로그 레벨

    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 반환
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper()))

    # 로그 디렉토리 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 파일 핸들러 (컬러 없음)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # 콘솔 핸들러 (컬러 포맷)
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
