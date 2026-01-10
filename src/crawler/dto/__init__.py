"""Data Transfer Objects for crawler module."""

from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_education_map import AsilEducationMapDTO
from crawler.dto.asil_school import AsilSchoolInfoDTO
from crawler.dto.asil_trade_price import AsilTradePriceDTO
from crawler.dto.asil_traffic import AsilTrafficInfoDTO
from crawler.dto.asil_visitor_stats import AsilVisitorStatsDTO

__all__ = [
    "AsilAptListDTO",
    "AsilEducationMapDTO",
    "AsilSchoolInfoDTO",
    "AsilTrafficInfoDTO",
    "AsilTradePriceDTO",
    "AsilVisitorStatsDTO",
]
