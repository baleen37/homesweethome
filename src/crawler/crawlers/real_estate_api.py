import json
import urllib.parse
from datetime import datetime
from typing import Any

import requests
import structlog

from crawler.config import CrawlerConfig
from crawler.crawlers.base import BaseCrawler


class RealEstateAPICrawler(BaseCrawler):
    """
    공공데이터 포털 API 기반 부동산 정보 크롤러
    - 국토교통부 아파트 매매 신고 조회 API 사용
    """

    def __init__(self, config: CrawlerConfig) -> None:
        super().__init__(config)
        self.base_url = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
        self.service_key = config.api_key or ""
        self.logger = structlog.get_logger()

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        # 기본 파라미터 설정
        params = {
            "serviceKey": self.service_key,
            "pageNo": "1",
            "numOfRows": "1000",  # 최대 1000개까지 조회 가능
        }

        # 지역 코드가 설정된 경우 추가
        if hasattr(self.config, 'region_code') and self.config.region_code:
            params["LAWD_CD"] = self.config.region_code

        # 날짜 범위가 설정된 경우 추가
        if hasattr(self.config, 'start_date') and self.config.start_date:
            params["DEAL_YMD"] = self.config.start_date.replace("-", "")
        else:
            # 기본값: 현재 월
            params["DEAL_YMD"] = datetime.now().strftime("%Y%m")

        # URL에 파라미터 추가
        url_with_params = f"{self.base_url}?{urllib.parse.urlencode(params)}"

        self.logger.info("generated_api_url", url=url_with_params, params=params)
        return url_with_params

    def fetch(self, url: str) -> str:
        """API 호출 및 응답 반환"""
        try:
            self.logger.info("fetching_api_data", url=url)
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 응답이 XML이므로 그대로 반환
            return response.text

        except requests.exceptions.RequestException as e:
            self.logger.error("api_request_failed", error=str(e), url=url)
            raise

    def parse(self, response: str) -> list[dict[str, Any]]:
        """XML 응답을 파싱하여 데이터 추출"""
        try:
            import xml.etree.ElementTree as ET

            # XML 파싱
            root = ET.fromstring(response)

            # 네임스페이스 처리
            namespaces = {
                'ns': root.tag.split('}')[0][1:] if '}' in root.tag else ''
            }

            items = []

            # response.body.items.item 경로에서 데이터 추출
            items_elements = root.findall('.//items/item', namespaces)

            for item in items_elements:
                # 각 필드 추출
                item_data = {}
                for child in item:
                    tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    item_data[tag_name] = child.text if child.text else None

                # 필수 필드 확인 및 데이터 정제
                if item_data.get('아파트'):  # 아파트 이름이 있는 경우만
                    # 단일 데이터 구조로 변환
                    parsed_item = {
                        'transaction_id': item_data.get('일련번호', ''),
                        'apartment_name': item_data.get('아파트', ''),
                        'building_name': item_data.get('아파트', ''),
                        'exclusive_area': float(item_data.get('전용면적', 0)),
                        'jeonse_price': self._parse_price(item_data.get('보증금액')),
                        'monthly_rent_fee': self._parse_price(item_data.get('월세금액')),
                        'sale_price': self._parse_price(item_data.get('거래금액')),
                        'trade_type': self._determine_trade_type(item_data),
                        'floor': item_data.get('층', ''),
                        'construct_year': item_data.get('건축년도', ''),
                        'address': self._build_address(item_data),
                        'address_road': self._build_road_address(item_data),
                        'description': f"{item_data.get('아파트', '')} {item_data.get('전용면적', '')}㎡",
                        'tags': self._extract_tags(item_data),
                        'is_new_deal': item_data.get('신규여부') == 'Y',
                        'manage_cost': None,
                        'complex_id': None,
                        'building_id': None,
                        'agent_name': item_data.get('중개사소재지', ''),
                        'agent_phone': None,
                        'images': [],
                        'image_urls': [],
                        'supply_area': None,
                        'direction': None,
                        'parking_count': None,
                        'household_count': None,
                        'heating_type': None,
                        'entrance_type': None,
                        'bathroom_count': None,
                        'room_count': None,
                        'verified_date': item_data.get('확인일자', ''),
                        'deal_ymd': item_data.get('거래일자', ''),
                        'cancel_ymd': item_data.get('취소일자', ''),
                        'buyer_gbn': item_data.get('부동산매매업계약서여부', ''),
                        'seller_gbn': item_data.get('매도자', ''),
                        'broker_office_name': item_data.get('중개사소재지', ''),
                        'building_use': None,
                        'planned_use': None,
                        'current_use': None,
                        'building_structure': None,
                        'roof_structure': None,
                        'total_floor_count': None,
                        'ground_floor_count': None,
                        'underground_floor_count': None,
                        'building_area': None,
                        'total_area': None,
                        'main_building_area': None,
                        'parcel_area': None,
                        'total_premium_rate': None,
                        'road_frontage': None,
                        'front_road': item_data.get('도로조건', ''),
                        'latitude': None,
                        'longitude': None,
                        'is_earthquake_resistant': None,
                        'elevator_count': None,
                        'parking_possible_count': None,
                        'household_count_by_supply_type': None,
                        'heating_fuel_type': None,
                        'is_all_day_care': None,
                        'is_internally_managed': None,
                        'is_management_office_present': None,
                        'front_road_structure': None,
                        'is_management_fee_reduction': None,
                        'management_fee_reduction_rate': None,
                        'special_supply_proportion': None,
                        'general_supply_proportion': None,
                        'parking_coownership_count': None,
                        'parking_exclusive_count': None,
                        'parking_visit_count': None,
                        'storage_cnt': None,
                        'balcony_area': None,
                        'total_floor_core_ratio': None,
                        'building_to_land_ratio': None,
                        'volume_ratio': None,
                        'main_floor_plan': None,
                        'main_floor_plan_img': None,
                        'floor_plan_img': None,
                        'site_img': None,
                        'brochure_img': None,
                        'certificate_img': None,
                        'building_register_img': None,
                        'land_register_img': None,
                        'use_permission_img': None,
                        'is_deal_activated': item_data.get('신규여부') == 'Y',
                        'listing_date': None,
                        'approval_date': None,
                        'deed_date': None,
                        'move_in_date': None,
                        'recommend_price': None,
                        'lowest_price': None,
                        'highest_price': None,
                        'price_per_pyeong': None,
                        'price_per_sqm': None,
                        'price_change': None,
                        'price_change_rate': None,
                        'has_premium': False,
                        'premium_reason': None,
                        'premium_content': None,
                        'item_struct': None,
                        'item_option': None,
                        'option_desc': None,
                        'security_desc': None,
                        'community_desc': None,
                        'etc_desc': None,
                        'deposit_details': None,
                        'loan_info': None,
                        'tax_info': None,
                        'school_info': None,
                        'traffic_info': None,
                        'living_info': None,
                        'special_info': None,
                        'danger_info': None,
                        'complex_name': None,
                        'short_complex_name': None,
                        'complex_name_eng': None,
                        'brand': None,
                        'serial_no': None,
                        'corp_name': None,
                        'is_deactivation_available': None,
                        'subject_title': None,
                        'post_code': None,
                        'sido': None,
                        'sigungu': None,
                        'eupmyeon': None,
                        'ri': None,
                        'san_yn': None,
                        'bonbun': None,
                        'bubun': None,
                        'manage_corp': None,
                        'manage_corp_type': None,
                        'total_households': None,
                        'heating_type_desc': None,
                        'electric_all_day_care_center_cnt': None,
                        'student_all_day_care_center_cnt': None,
                        'teacher_all_day_care_center_cnt': None,
                        'cctv_cnt': None,
                        'playground_cnt': None,
                        'security_company_cnt': None,
                        'auto_fire_detection_sensor_cnt': None,
                        'fire_extinguisher_cnt': None,
                        'emergency_broadcast_cnt': None,
                        'subway_info': None,
                        'bus_info': None,
                        'road_nearby': None,
                        'facility_nearby': None,
                        'education_nearby': None,
                        'financing_available_yn': None,
                        'short_term_rental_yn': None,
                        'full_option_yn': None,
                        'living_option_yn': None,
                        'bathroom_option_yn': None,
                        'kitchen_option_yn': None,
                        'built_in_option_yn': None,
                        'airconditioner_yn': None,
                        'washing_machine_yn': None,
                        'refrigerator_yn': None,
                        'closet_yn': None,
                        'gas_range_yn': None,
                        'induction_yn': None,
                        'microwave_yn': None,
                        'shoe_closet_yn': None,
                        'dressing_table_yn': None,
                        'veranda_extend_yn': None,
                        'wallpaper_yn': None,
                        'flooring_yn': None,
                        'door_window_repair_yn': None,
                        'kitchen_sink_repair_yn': None,
                        'bathroom_sink_repair_yn': None,
                        'utility_bill_type': None,
                        'parking_fee': None,
                        'parking_lot_type': None,
                        'parking_sharing_type': None,
                        'elevator_yn': None,
                        'internet_yn': None,
                        'moving_date_available_yn': None,
                        'moving_date_type': None,
                        'resident_type': None,
                        'structure_desc': None,
                        'present_purpose_desc': None,
                        'direction_desc': None,
                        'front_road_type_desc': None,
                        'total_floor_cnt': None,
                        'contract_type': None,
                        'contract_term': None,
                        'deposit_return_yn': None,
                        'first_rent_date': None,
                        'rent_free_period': None,
                        'rent_amount': None,
                        'total_rent_amount': None,
                        'total_fees': None,
                        'deposit_amount': None,
                        'admin_cost': None,
                        'is_admin_cost_public': None,
                        'admin_fee_desc': None,
                        'parking_fee_desc': None,
                        'etc_fee_desc': None,
                        'interior_maintenance_fee': None,
                        'external_maintenance_fee': None,
                        'general_maintenance_fee': None,
                        'contingency_reserve_fee': None,
                        'longterm_repair_fee': None,
                        'inspection_fee': None,
                        'insurance_fee': None,
                        'common_utility_fee': None,
                        'cleaning_fee': None,
                        'security_fee': None,
                        'disinfection_fee': None,
                        'trash_disposal_fee': None,
                        'management_fee_rent_type': None,
                        'complex_number': None,
                        'dong_number': None,
                        'ho_number': None,
                        'building_number': None,
                        'land_number': None,
                        'complex_address': None,
                        'region_code': None,
                        'region_name': None,
                        'sub_region_code': None,
                        'sub_region_name': None,
                        'district_code': None,
                        'district_name': None,
                        'legal_dong_code': item_data.get('법정동시군구코드', ''),
                        'legal_dong_name': item_data.get('법정동읍면동코드', ''),
                        'admin_dong_code': None,
                        'admin_dong_name': None,
                        'land_lot_number': None,
                        'land_section_number': None,
                        'coordinates': None,
                        'deal_year': item_data.get('년', ''),
                        'deal_month': item_data.get('월', ''),
                        'deal_day': item_data.get('일', ''),
                        'is_deactivated': None,
                        'deactivation_date': None,
                        'deactivation_reason': None,
                        'created_at': None,
                        'updated_at': None,
                        'source': 'RTMS_API',
                        'crawl_timestamp': datetime.now().isoformat(),
                    }

                    items.append(parsed_item)

            self.logger.info("parsed_api_response", items_count=len(items))
            return items

        except Exception as e:
            self.logger.error("failed_to_parse_api_response", error=str(e))
            raise

    def _parse_price(self, price_str: str | None) -> int | None:
        """가격 문자열을 정수로 변환"""
        if not price_str or price_str == '':
            return None

        # 쉼표와 공백 제거
        cleaned = price_str.replace(',', '').replace(' ', '')

        try:
            return int(cleaned)
        except ValueError:
            self.logger.warning("failed_to_parse_price", price_str=price_str)
            return None

    def _determine_trade_type(self, item_data: dict) -> str:
        """거래 유형 결정"""
        if item_data.get('거래금액'):
            return '매매'
        elif item_data.get('보증금액') and item_data.get('월세금액'):
            return '월세'
        elif item_data.get('보증금액'):
            return '전세'
        else:
            return '기타'

    def _build_address(self, item_data: dict) -> str:
        """주소 정보 조합"""
        parts = [
            item_data.get('시도명'),
            item_data.get('시군구명'),
            item_data.get('법정동읍면동명') or item_data.get('법정동'),
        ]

        # 지본번 추가 (여러 필드명 지원)
        base_num = item_data.get('지번본번') or item_data.get('본번')
        sub_num = item_data.get('지번부번') or item_data.get('부번')

        if base_num:
            base_num = str(base_num)
            # 지부번이 0이 아닌 경우만 추가
            if sub_num and sub_num != '0' and sub_num != 0:
                base_num += f"-{sub_num}"
            parts.append(base_num)

        # None 값 제거하고 조합
        return ' '.join(part for part in parts if part)

    def _build_road_address(self, item_data: dict) -> str | None:
        """도로명 주소 정보 조합"""
        parts = [
            item_data.get('도로명시도명'),
            item_data.get('도로명시군구명'),
            item_data.get('도로명'),
            item_data.get('도로명건물본번호코드') and f"{item_data.get('도로명건물본번호코드')}",
            item_data.get('도로명건물부번호코드') and f"-{item_data.get('도로명건물부번호코드')}",
        ]

        # None 값 제거하고 조합
        result = ' '.join(part for part in parts if part)
        return result if result else None

    def _extract_tags(self, item_data: dict) -> list[str]:
        """추가 태그 정보 추출"""
        tags = []

        # 건축년도 기반 태그
        construct_year = item_data.get('건축년도')
        if construct_year:
            try:
                year = int(construct_year)
                current_year = datetime.now().year
                age = current_year - year

                if age <= 5:
                    tags.append('신축')
                elif age <= 15:
                    tags.append('준신축')
                else:
                    tags.append('구축')
            except ValueError:
                pass

        # 신규 거래 여부
        if item_data.get('신규여부') == 'Y':
            tags.append('신규거래')

        return tags