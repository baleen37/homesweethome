"""로깅 설정 및 유틸리티

민감한 정보를 필터링하고 구조화된 로깅을 제공합니다.
"""

import json
import logging
import logging.handlers
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

import structlog
from structlog.stdlib import LoggerFactory

# 민감 정보 패턴 정의
SENSITIVE_PATTERNS = {
    # 이메일 주소
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    # 전화번호 (다양한 형식)
    "phone": re.compile(
        r"""
        (\+?82[-\s]?|0)?           # 국가번호 또는 0
        (1[016789]|2[0-9]?|3[0-9]?|4[0-9]?|5[0-9]?|6[0-9]?)  # 지역번호/이동통신사
        [-\s]?                     # 구분자
        (\d{3,4})[-\s]?(\d{4})    # 전화번호
        """,
        re.VERBOSE,
    ),
    # API 키 (sk-开头)
    "api_key": re.compile(r"\bsk-[a-zA-Z0-9]+\b"),
    # Bearer 토큰
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+\/]+=*\b"),
    # JWT 토큰
    "jwt": re.compile(r"\beyJ[A-Za-z0-9\-._~+\/]+=*\b"),
    # 일반적인 토큰 패턴 (16자 이상의 영숫자)
    "generic_token": re.compile(r"\b[a-zA-Z0-9]{16,}\b"),
    # 비밀번호 관련 필드
    "password": re.compile(r'["\']?(password|passwd|pwd)["\']?\s*[:=]\s*["\']?[^"\'\s]+'),
    # IP 주소
    "ip_address": re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
}


class SensitiveDataFilter(logging.Filter):
    """로그에서 민감한 정보를 마스킹하는 필터"""

    def __init__(self):
        super().__init__()
        self.patterns = SENSITIVE_PATTERNS

    def _mask_value(self, match: re.Match) -> str:
        """매치된 값에 적절한 마스킹 적용"""
        value = match.group(0)

        # 토큰/키인 경우 [REDACTED]로 완전히 교체
        if any(
            pattern in match.group(0)
            for pattern in ["Bearer", "sk-", "eyJ", "password", "passwd", "pwd"]
        ):
            return "[REDACTED]"

        # 이메일인 경우 사용자명 부분 마스킹
        if "@" in value:
            local, domain = value.split("@", 1)
            if len(local) <= 3:
                return f"***@{domain}"
            return f"{local[0]}***@{domain}"

        # 전화번호인 경우 중간 번호 마스킹
        if re.match(r"^\+?\d", value):
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 10:
                # 010-1234-5678 -> 010-****-5678
                return re.sub(r"(\d{2,4})[-\s]?(\d{3,4})[-\s]?(\d{4})", r"\1-****-\3", value)

        # 일반 토큰의 경우 일부만 표시
        if len(value) > 8:
            return f"{value[:4]}***{value[-4:]}"

        return "***"

    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드에서 민감 정보 필터링"""
        # 메시지 처리
        if hasattr(record, "msg"):
            for name, pattern in self.patterns.items():
                record.msg = pattern.sub(self._mask_value, str(record.msg))

        # 인자 처리
        if hasattr(record, "args") and record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for name, pattern in self.patterns.items():
                        arg = pattern.sub(self._mask_value, arg)
                    new_args.append(arg)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        return True


def sensitive_data_processor(logger, method_name: str, event_dict: dict) -> dict:
    """structlog용 민감 데이터 처리 프로세서"""
    # dict 값들에서 민감 정보 찾아서 마스킹
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern in SENSITIVE_PATTERNS.values():
                if pattern.search(value):
                    # 간단한 마스킹 적용
                    if "@" in value and pattern == SENSITIVE_PATTERNS["email"]:
                        local, domain = value.split("@", 1)
                        value = f"{local[0]}***@{domain}"
                    elif any(k in value.lower() for k in ["password", "token", "key"]):
                        value = "[REDACTED]"
                    else:
                        value = "***"
                    event_dict[key] = value
                    break

    return event_dict


def configure_logging(
    log_dir: Optional[str] = None,
    level: str = "INFO",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """로깅 시스템 설정

    Args:
        log_dir: 로그 파일 저장 디렉토리 (None이면 파일 로깅 비활성화)
        level: 로그 레벨
        max_file_size: 로그 파일 최대 크기 (bytes)
        backup_count: 보관할 백업 파일 수
    """
    # 기본 로깅 설정
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        handlers=[],
    )

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.addFilter(SensitiveDataFilter())

    # structlog 설정
    processors = [
        # 타임스탬프 추가
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # 민감 정보 필터링
        sensitive_data_processor,
    ]

    # 로그 파일이 설정된 경우 JSON 포매터 추가
    if log_dir:
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        # 파일 핸들러 설정 (RotatingFileHandler)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir_path / "crawler.log",
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        file_handler.addFilter(SensitiveDataFilter())

        # JSON 포매터를 파일 출력에만 사용
        processors.append(structlog.processors.JSONRenderer())

        # 파일 핸들러를 루트 로거에 추가
        logging.getLogger().addHandler(file_handler)
    else:
        # 콘솔은 가독성 좋은 포매터 사용
        processors.append(structlog.dev.ConsoleRenderer())

    # structlog 설정
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 기본 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(console_handler)


class CrawlLogger:
    """크롤링 전용 로거"""

    def __init__(self, crawler_name: str):
        """크롤러 로거 초기화

        Args:
            crawler_name: 크롤러 이름 (로그에 포함됨)
        """
        self.logger = structlog.get_logger()
        self.crawler_name = crawler_name
        self.request_count = 0
        self.start_time = time.time()
        self.last_request_time = 0

    def log_api_call(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        response_time: Optional[float] = None,
        status_code: Optional[int] = None,
        response_size: Optional[int] = None,
    ):
        """API 호출 로깅

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터
            response_time: 응답 시간 (초)
            status_code: HTTP 상태 코드
            response_size: 응답 크기 (bytes)
        """
        self.request_count += 1

        log_data = {
            "crawler": self.crawler_name,
            "event": "api_call",
            "endpoint": endpoint,
            "request_count": self.request_count,
        }

        if params:
            log_data["params"] = params
        if response_time is not None:
            log_data["response_time"] = round(response_time, 3)
        if status_code is not None:
            log_data["status_code"] = status_code
        if response_size is not None:
            log_data["response_size"] = response_size

        # 요청 간격 계산
        if self.last_request_time > 0:
            log_data["interval_since_last"] = round(time.time() - self.last_request_time, 3)
        self.last_request_time = time.time()

        # 로그 레벨 결정
        if status_code and status_code >= 400:
            self.logger.warning("API call failed", **log_data)
        else:
            self.logger.info("API call", **log_data)

    def log_retry(
        self,
        attempt: int,
        max_attempts: int,
        error: str,
        delay: float,
        context: Optional[dict] = None,
    ):
        """재시도 로깅

        Args:
            attempt: 현재 시도 횟수
            max_attempts: 최대 시도 횟수
            error: 에러 메시지
            delay: 다음 시도까지의 대기 시간 (초)
            context: 추가 컨텍스트 정보
        """
        log_data = {
            "crawler": self.crawler_name,
            "event": "retry",
            "attempt": attempt,
            "max_attempts": max_attempts,
            "error": error,
            "delay": delay,
        }

        if context:
            log_data.update(context)

        self.logger.warning("Retrying operation", **log_data)

    def log_progress(
        self,
        current: int,
        total: int,
        item_type: str = "items",
        elapsed_time: Optional[float] = None,
        eta: Optional[float] = None,
    ):
        """진행률 로깅

        Args:
            current: 현재 처리된 수
            total: 전체 수
            item_type: 아이템 타입 이름
            elapsed_time: 경과 시간 (초)
            eta: 예상 완료 시간 (초)
        """
        percentage = (current / total * 100) if total > 0 else 0

        log_data = {
            "crawler": self.crawler_name,
            "event": "progress",
            "current": current,
            "total": total,
            "percentage": round(percentage, 2),
            "item_type": item_type,
        }

        if elapsed_time is not None:
            log_data["elapsed_time"] = round(elapsed_time, 1)
            # 평균 처리 속도 계산
            if elapsed_time > 0 and current > 0:
                log_data["items_per_second"] = round(current / elapsed_time, 2)

        if eta is not None:
            log_data["eta_seconds"] = round(eta, 1)

        self.logger.info("Progress update", **log_data)

    def log_resource_usage(
        self,
        memory_mb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        requests_made: Optional[int] = None,
        avg_response_time: Optional[float] = None,
    ):
        """리소스 사용량 로깅

        Args:
            memory_mb: 메모리 사용량 (MB)
            cpu_percent: CPU 사용률 (%)
            requests_made: 총 요청 수
            avg_response_time: 평균 응답 시간 (초)
        """
        log_data = {
            "crawler": self.crawler_name,
            "event": "resource_usage",
            "uptime": round(time.time() - self.start_time, 1),
        }

        if memory_mb is not None:
            log_data["memory_mb"] = round(memory_mb, 2)
        if cpu_percent is not None:
            log_data["cpu_percent"] = round(cpu_percent, 2)
        if requests_made is not None:
            log_data["requests_made"] = requests_made
        if avg_response_time is not None:
            log_data["avg_response_time"] = round(avg_response_time, 3)

        self.logger.info("Resource usage", **log_data)

    def error_with_context(
        self,
        error: Exception,
        context: Optional[dict] = None,
        critical: bool = False,
    ):
        """에러와 컨텍스트 정보 함께 로깅

        Args:
            error: 발생한 에러
            context: 추가 컨텍스트 정보
            critical: critical 에러 여부
        """
        log_data = {
            "crawler": self.crawler_name,
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "critical": critical,
        }

        if context:
            # 컨텍스트에서 민감 정보 필터링
            filtered_context = {}
            for key, value in context.items():
                if isinstance(value, str):
                    for pattern in SENSITIVE_PATTERNS.values():
                        if pattern.search(value):
                            value = "[REDACTED]"
                            break
                filtered_context[key] = value
            log_data.update(filtered_context)

        if critical:
            self.logger.critical("Critical error occurred", **log_data)
        else:
            self.logger.error("Error occurred", **log_data)

    def log_crawl_start(self, total_items: Optional[int] = None, **kwargs):
        """크롤링 시작 로깅"""
        log_data = {
            "crawler": self.crawler_name,
            "event": "crawl_start",
        }
        if total_items is not None:
            log_data["total_items"] = total_items
        log_data.update(kwargs)

        self.logger.info("Starting crawl", **log_data)

    def log_crawl_end(
        self,
        items_processed: int,
        success: bool = True,
        summary: Optional[dict] = None,
    ):
        """크롤링 종료 로깅"""
        elapsed_time = time.time() - self.start_time

        log_data = {
            "crawler": self.crawler_name,
            "event": "crawl_end",
            "items_processed": items_processed,
            "success": success,
            "elapsed_time": round(elapsed_time, 1),
            "total_requests": self.request_count,
        }

        if elapsed_time > 0 and items_processed > 0:
            log_data["items_per_second"] = round(items_processed / elapsed_time, 2)

        if summary:
            log_data.update(summary)

        if success:
            self.logger.info("Crawl completed successfully", **log_data)
        else:
            self.logger.warning("Crawl completed with issues", **log_data)