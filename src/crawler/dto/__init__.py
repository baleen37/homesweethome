"""Data Transfer Objects for crawler module."""

from crawler.dto.asil_agent import AsilAgentDTO, AsilAgentInfoResponse
from crawler.dto.asil_apt_list import AsilAptListDTO
from crawler.dto.asil_bunyang import AsilBunyangListDTO
from crawler.dto.asil_bunyang_map import (
    AsilBunyangMapResponse,
    AsilSiguInfoDTO,
)
from crawler.dto.asil_dong_info import AsilDongInfoDTO
from crawler.dto.asil_education_map import AsilEducationMapDTO
from crawler.dto.asil_map_search import AsilMapSearchDTO
from crawler.dto.asil_movein import AsilMoveinDTO
from crawler.dto.asil_offer import AsilOfferDTO, AsilOffersListResponse
from crawler.dto.asil_offer_detail import (
    AsilOfferDetailAdminCostDTO,
    AsilOfferDetailDTO,
    AsilOfferDetailImageDTO,
    AsilOfferDetailOptionDTO,
    AsilOfferDetailRelatedDTO,
    AsilOfferDetailResponse,
)
from crawler.dto.asil_population import AsilPopulationDTO
from crawler.dto.asil_price_index import (
    AsilPriceIndexRegionDTO,
    AsilPriceIndexResponse,
    AsilPriceIndexSummaryDTO,
)
from crawler.dto.asil_ranking import AsilRankingDTO
from crawler.dto.asil_school import AsilSchoolInfoDTO
from crawler.dto.asil_trade_price import AsilTradePriceDTO
from crawler.dto.asil_traffic import AsilTrafficInfoDTO
from crawler.dto.asil_transfer import AsilTransferDTO
from crawler.dto.asil_visitor_stats import AsilVisitorStatsDTO

__all__ = [
    "AsilAgentDTO",
    "AsilAgentInfoResponse",
    "AsilBunyangMapResponse",
    "AsilBunyangListDTO",
    "AsilSiguInfoDTO",
    "AsilAptListDTO",
    "AsilDongInfoDTO",
    "AsilEducationMapDTO",
    "AsilMapSearchDTO",
    "AsilMoveinDTO",
    "AsilOfferDTO",
    "AsilOffersListResponse",
    "AsilOfferDetailDTO",
    "AsilOfferDetailOptionDTO",
    "AsilOfferDetailImageDTO",
    "AsilOfferDetailAdminCostDTO",
    "AsilOfferDetailRelatedDTO",
    "AsilOfferDetailResponse",
    "AsilPopulationDTO",
    "AsilPriceIndexRegionDTO",
    "AsilPriceIndexResponse",
    "AsilPriceIndexSummaryDTO",
    "AsilRankingDTO",
    "AsilSchoolInfoDTO",
    "AsilTrafficInfoDTO",
    "AsilTradePriceDTO",
    "AsilTransferDTO",
    "AsilVisitorStatsDTO",
]
