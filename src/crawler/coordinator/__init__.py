"""Coordinator package for crawler operations.

크롤러 간의 조율 및 상태 관리를 담당합니다.
"""

from .progress_tracker import ProgressTracker

__all__ = ["ProgressTracker"]
