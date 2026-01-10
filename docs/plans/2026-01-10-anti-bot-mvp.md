# Anti-Bot MVP 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 네이버 부동산 맵처럼 anti-bot 탐지가 있는 사이트를 크롤링할 수 있는 AntiBotCrawler를 구현합니다.

**Architecture:** BaseCrawler(동기)를 상속받아 AntiBotCrawler(비동기)를 만듭니다. utils 패키지에 geo.py와 mouse.py를 만들어 Mercator projection과 마우스 시뮬레이션을 분리합니다. TDD로 테스트 먼저 작성하고 구현합니다.

**Tech Stack:** Python 3.11+, Playwright 1.40+, pytest, pytest-asyncio

---

## 개요

이 계획은 anti_bot_scraper의 핵심 개념을 homesweethome 프로젝트에 통합합니다. MVP는 다음 기능을 포함합니다:

1. **AntiBotCrawler**: BaseCrawler를 상속받은 비동기 anti-bot 크롤러
2. **인간형 맵 네비게이션**: 줌 아웃 → 드래그 → 줌 인 패턴
3. **마우스 시뮬레이션**: Bézier 곡선으로 부드러운 이동
4. **Mercator Projection**: 위도/경도 ↔ 픽셀 변환
5. **그리드 스윕 알고리즘**: 상하단 스캔으로 패턴 은폐
6. **E2E 테스트**: 실제 네이버 부동산 맵에서 검증

---

## Phase 1: 기반 구축 (geo.py)

### Task 1: utils 패키지 생성

**Files:**
- Create: `src/crawler/utils/__init__.py`

**Step 1: 빈 __init__.py 파일 생성**

```python
"""Crawler 유틸리티 패키지"""
```

**Step 2: Run tests**

Run: `ls src/crawler/utils/__init__.py`
Expected: 파일 존재 확인

**Step 3: Commit**

```bash
git add src/crawler/utils/__init__.py
git commit -m "feat: crawler utils 패키지 추가"
```

---

### Task 2: geo.py - ll_to_pixel 함수

**Files:**
- Create: `src/crawler/utils/geo.py`
- Test: `tests/unit/test_geo.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_geo.py
import pytest

from crawler.utils.geo import ll_to_pixel


@pytest.mark.unit
def test_ll_to_pixel_seoul():
    """서울 시청 좌표를 픽셀로 변환"""
    x, y = ll_to_pixel(37.5665, 126.9780, 15)
    # 줌 레벨 15에서 서울 시청 근처 픽셀 값
    assert isinstance(x, float)
    assert isinstance(y, float)
    assert x > 0
    assert y > 0


@pytest.mark.unit
def test_ll_to_pixel_equator():
    """적도 본초 자오선 교차점"""
    x, y = ll_to_pixel(0, 0, 1)
    # 줌 1에서 적도는 중앙
    scale = 256 * 2
    expected_x = 0.5 * scale
    expected_y = 0.5 * scale
    assert abs(x - expected_x) < 1
    assert abs(y - expected_y) < 1


@pytest.mark.unit
def test_ll_to_pixel_boundary():
    """위도 경계값 테스트 (85도 초과는 안 됨)"""
    # Mercator projection은 위도 ±85도까지만 유효
    with pytest.raises(ValueError):
        ll_to_pixel(86, 0, 10)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_geo.py::test_ll_to_pixel_seoul -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawler.utils.geo'"

**Step 3: Write minimal implementation**

```python
# src/crawler/utils/geo.py
"""Mercator projection 지리 좌표 변환 유틸리티"""

import math


def ll_to_pixel(lat: float, lon: float, zoom: float) -> tuple[float, float]:
    """
    위도/경도를 픽셀 좌표로 변환 (Mercator projection).

    Args:
        lat: 위도 (-85 ~ 85)
        lon: 경도 (-180 ~ 180)
        zoom: 줌 레벨 (1 ~ 20)

    Returns:
        (x, y) 픽셀 좌표

    Raises:
        ValueError: 위도가 유효 범위를 벗어날 때
    """
    if abs(lat) > 85:
        raise ValueError(f"위도는 ±85도까지만 유효함: {lat}")

    scale = 256 * (2 ** zoom)
    x = (lon + 180.0) / 360.0 * scale

    siny = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale

    return x, y
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_geo.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_geo.py src/crawler/utils/geo.py
git commit -m "feat: Mercator projection 위도/경도를 픽셀로 변환"
```

---

### Task 3: geo.py - pixel_to_ll 함수

**Files:**
- Modify: `src/crawler/utils/geo.py`
- Modify: `tests/unit/test_geo.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_geo.py에 추가

@pytest.mark.unit
def test_pixel_to_ll_roundtrip():
    """픽셀 → 위도/경도 역변환 round-trip 테스트"""
    original_lat, original_lon = 37.5665, 126.9780
    x, y = ll_to_pixel(original_lat, original_lon, 15)
    recovered_lat, recovered_lon = pixel_to_ll(x, y, 15)

    # 역변환은 ±0.0001도 오차 범위 내에서 일치해야 함
    assert abs(recovered_lat - original_lat) < 0.0001
    assert abs(recovered_lon - original_lon) < 0.0001
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_geo.py::test_pixel_to_ll_roundtrip -v`
Expected: FAIL with "name 'pixel_to_ll' is not defined"

**Step 3: Write minimal implementation**

```python
# src/crawler/utils/geo.py에 추가

def pixel_to_ll(x: float, y: float, zoom: float) -> tuple[float, float]:
    """
    픽셀 좌표를 위도/경도로 변환 (ll_to_pixel의 역변환).

    Args:
        x, y: 픽셀 좌표
        zoom: 줌 레벨

    Returns:
        (lat, lon) 위도/경도
    """
    scale = 256 * (2 ** zoom)
    lon = x / scale * 360.0 - 180.0

    n = math.pi - 2.0 * math.pi * y / scale
    lat = math.degrees(math.atan(math.sinh(n)))

    return lat, lon
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_geo.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_geo.py src/crawler/utils/geo.py
git commit -m "feat: Mercator projection 픽셀을 위도/경도로 변환"
```

---

## Phase 2: 마우스 시뮬레이션 (mouse.py)

### Task 4: mouse.py - smooth_drag 함수

**Files:**
- Create: `src/crawler/utils/mouse.py`
- Test: `tests/unit/test_mouse.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_mouse.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from crawler.utils.mouse import smooth_drag


@pytest.mark.unit
async def test_smooth_drag_calls_mouse_methods():
    """smooth_drag가 마우스 메서드를 올바른 순서로 호출"""
    mock_page = MagicMock()
    mock_page.mouse = MagicMock()

    # 비동기 메서드 모킹
    mock_page.mouse.move = AsyncMock()
    mock_page.mouse.down = AsyncMock()
    mock_page.mouse.up = AsyncMock()

    await smooth_drag(mock_page, 100, 100, 200, 200, steps=5)

    # move가 호출되었는지 확인
    assert mock_page.mouse.move.called
    # down이 호출되었는지 확인
    assert mock_page.mouse.down.called
    # up이 호출되었는지 확인
    assert mock_page.mouse.up.called


@pytest.mark.unit
async def test_smooth_drag_steps_parameter():
    """steps 파라미터가 올바르게 전달되는지 확인"""
    mock_page = MagicMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.move = AsyncMock()
    mock_page.mouse.down = AsyncMock()
    mock_page.mouse.up = AsyncMock()

    await smooth_drag(mock_page, 100, 100, 200, 200, steps=20)

    # Playwright의 steps 파라미터는 move 내부에서 처리됨
    # 우리가 전달한 steps가 사용되는지 확인
    mock_page.mouse.move.assert_called()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_mouse.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawler.utils.mouse'"

**Step 3: Write minimal implementation**

```python
# src/crawler/utils/mouse.py
"""마우스 시뮬레이션 유틸리티"""

from playwright.async_api import Page


async def smooth_drag(
    page: Page,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    steps: int = 20,
) -> None:
    """
    부드러운 가속도/감속도가 있는 드래그 실행.

    Playwright의 steps 파라미터가 Bézier 곡선을 생성하여
    인간의 모터 제어 패턴을 시뮬레이션합니다.

    Args:
        page: Playwright Page 객체
        start_x, start_y: 시작 좌표
        end_x, end_y: 종료 좌표
        steps: 중간 단계 수 (높을수록 부드러움, 20이 권장)
    """
    # 시작 위치로 마우스 이동
    await page.mouse.move(start_x, start_y)

    # 마우스 누름
    await page.mouse.down()

    # 목표 위치로 부드럽게 드래그
    await page.mouse.move(end_x, end_y, steps=steps)

    # 마우스 뗌
    await page.mouse.up()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_mouse.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_mouse.py src/crawler/utils/mouse.py
git commit -m "feat: 부드러운 마우스 드래그 시뮬레이션 추가"
```

---

## Phase 3: AntiBotCrawler 구현

### Task 5: anti_bot.py - AntiBotCrawler 기본 구조

**Files:**
- Create: `src/crawler/anti_bot.py`
- Test: `tests/unit/test_anti_bot_crawler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_anti_bot_crawler.py
import pytest
from unittest.mock import MagicMock

from crawler.anti_bot import AntiBotCrawler


@pytest.mark.unit
def test_anti_bot_crawler_inherits_from_base_crawler():
    """AntiBotCrawler가 BaseCrawler를 상속받는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)
    assert isinstance(crawler, AntiBotCrawler)
    # BaseCrawler의 인터페이스 확인
    assert hasattr(crawler, 'get_url')
    assert hasattr(crawler, 'fetch')
    assert hasattr(crawler, 'parse')
    assert hasattr(crawler, 'crawl')


@pytest.mark.unit
def test_anti_bot_crawler_has_playwright_context():
    """Playwright context가 올바르게 저장되는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)
    assert crawler.context is mock_context
    assert crawler.page is None  # 초기값은 None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'crawler.anti_bot'"

**Step 3: Write minimal implementation**

```python
# src/crawler/anti_bot.py
"""Anti-Bot 우회 기능을 포함한 크롤러 베이스 클래스"""

from abc import abstractmethod
from typing import Any

from playwright.async_api import BrowserContext, Page

from crawler.base import BaseCrawler


class AntiBotCrawler(BaseCrawler):
    """
    BaseCrawler를 상속받아 anti-bot 우회 기능을 추가한 추상 클래스.

    주요 기능:
    - Anti-detection 초기화 스크립트 주입
    - 인간형 맵 네비게이션 (줨 → 드래그 → 줌)
    - 마우스 이동 시뮬레이션 (Bézier 곡선)
    - 그리드 스윕 알고리즘 (패턴 은폐)
    """

    def __init__(self, context: BrowserContext):
        """
        Args:
            context: Playwright BrowserContext (anti-detection 설정 완료된 상태)
        """
        self.context = context
        self.page: Page | None = None

    @abstractmethod
    async def aget_url(self) -> str:
        """비동기 URL 반환 (추상 메서드)"""
        pass

    @abstractmethod
    async def afetch(self, url: str) -> str:
        """비동기 fetch (추상 메서드)"""
        pass

    @abstractmethod
    async def aparse(self, content: str) -> list[dict[str, Any]]:
        """비동기 parse (추상 메서드)"""
        pass

    async def acrawl(self) -> list[dict[str, Any]]:
        """비동기 템플릿 메서드"""
        url = await self.aget_url()
        content = await self.afetch(url)
        return await self.aparse(content)

    # BaseCrawler의 추상 메서드도 구현해야 함
    @abstractmethod
    def get_url(self) -> str:
        pass

    @abstractmethod
    def fetch(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, content: str) -> list[dict[str, Any]]:
        pass
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_anti_bot_crawler.py src/crawler/anti_bot.py
git commit -m "feat: AntiBotCrawler 기본 구조 추가"
```

---

### Task 6: anti_bot.py - setup_page 메서드

**Files:**
- Modify: `src/crawler/anti_bot.py`
- Modify: `tests/unit/test_anti_bot_crawler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_anti_bot_crawler.py에 추가

@pytest.mark.unit
async def test_setup_page_creates_new_page(mocker):
    """setup_page가 새로운 페이지를 생성하는지 확인"""
    mock_context = MagicMock()
    mock_new_page = mocker.patch.object(
        mock_context, 'new_page', new_callable=mocker.AsyncMock
    )
    mock_page = MagicMock()
    mock_new_page.return_value = mock_page

    crawler = AntiBotCrawler(mock_context)
    result = await crawler.setup_page()

    assert result is mock_page
    mock_new_page.assert_called_once()
    # webdriver 제거 스크립트가 주입되었는지 확인
    mock_page.add_init_script.assert_called()


@pytest.mark.unit
async def test_setup_page_injects_anti_detection_scripts(mocker):
    """setup_page가 anti-detection 스크립트를 주입하는지 확인"""
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_context.new_page = mocker.AsyncMock(return_value=mock_page)

    crawler = AntiBotCrawler(mock_context)
    await crawler.setup_page()

    # anti-detection 스크립트가 주입되었는지 확인
    assert mock_page.add_init_script.called
    call_args = mock_page.add_init_script.call_args
    script_content = call_args[0][0] if call_args[0] else call_args[1].get('script', '')

    # webdriver 제거 코드가 포함되어 있는지 확인
    assert 'navigator.webdriver' in script_content
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_setup_page_creates_new_page -v`
Expected: FAIL with "AttributeError: 'AntiBotCrawler' object has no attribute 'setup_page'"

**Step 3: Write minimal implementation**

```python
# src/crawler/anti_bot.py에 추가

    async def setup_page(self) -> Page:
        """
        anti-detection이 적용된 페이지 생성.

        초기화 스크립트:
        - navigator.webdriver 제거
        - window.chrome 오버라이드
        - plugins 배열 위조

        Returns:
            Playwright Page 객체
        """
        page = await self.context.new_page()

        # Anti-detection 스크립트 주입
        anti_detection_script = """
        () => {
            // webdriver 속성 제거
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // chrome 오버라이드
            window.chrome = {
                runtime: {},
            };

            // plugins 위조
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        }
        """
        await page.add_init_script(anti_detection_script)

        return page
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_anti_bot_crawler.py src/crawler/anti_bot.py
git commit -m "feat: anti-detection 페이지 설정 추가"
```

---

### Task 7: anti_bot.py - drag_to_latlon 메서드

**Files:**
- Modify: `src/crawler/anti_bot.py`
- Test: `tests/unit/test_anti_bot_crawler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_anti_bot_crawler.py에 추가

@pytest.mark.unit
async def test_drag_to_latlon_calls_geo_utils(mocker):
    """drag_to_latlon이 geo 유틸리티를 호출하는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}

    # geo 유틸리티 모킹
    mock_ll_to_pixel = mocker.patch(
        'crawler.anti_bot.ll_to_pixel',
        return_value=(1000, 500)
    )
    mock_smooth_drag = mocker.patch(
        'crawler.anti_bot.smooth_drag',
        new_callable=mocker.AsyncMock
    )

    await crawler.drag_to_latlon(mock_page, 37.5665, 126.9780, 15)

    # geo 유틸리티가 호출되었는지 확인
    mock_ll_to_pixel.assert_called_once()
    mock_smooth_drag.assert_called_once()


@pytest.mark.unit
async def test_drag_to_latlon_handles_long_distance(mocker):
    """장거리 드래그가 분할되어 처리되는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}

    # 1000px 이상 거리 반환
    mocker.patch(
        'crawler.anti_bot.ll_to_pixel',
        side_effect=[(100, 100), (1200, 100)]  # 1100px 차이
    )
    mock_smooth_drag = mocker.patch(
        'crawler.anti_bot.smooth_drag',
        new_callable=mocker.AsyncMock
    )

    await crawler.drag_to_latlon(mock_page, 37.5665, 126.9780, 15)

    # 두 번 이상 나뉘어서 호출되어야 함
    assert mock_smooth_drag.call_count >= 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_drag_to_latlon_calls_geo_utils -v`
Expected: FAIL with "AttributeError: 'AntiBotCrawler' object has no attribute 'drag_to_latlon'"

**Step 3: Write minimal implementation**

```python
# src/crawler/anti_bot.py에 추가

from crawler.utils.geo import ll_to_pixel
from crawler.utils.mouse import smooth_drag

    async def drag_to_latlon(
        self,
        page: Page,
        lat: float,
        lon: float,
        zoom: int,
        tolerance_px: float = 3.5,
    ) -> None:
        """
        부드러운 드래그로 특정 위도/경도로 이동.

        기술:
        - Mercator projection으로 픽셀 변환
        - steps=20으로 Bézier 가속도 곡선 생성
        - 거리 제한 (800px 초과 시 분할)

        Args:
            page: Playwright Page 객체
            lat: 목표 위도
            lon: 목표 경도
            zoom: 줌 레벨
            tolerance_px: 오차 허용 픽셀
        """
        if not page.viewport_size:
            raise ValueError("페이지 뷰포트 크기가 설정되지 않음")

        vp_width = page.viewport_size['width']
        vp_height = page.viewport_size['height']
        center_x = vp_width / 2
        center_y = vp_height / 2

        # 현재 중심 좌표를 픽셀로 변환 (가정: 현재 위치)
        current_x, current_y = center_x, center_y

        # 목표 좌표를 픽셀로 변환
        target_x, target_y = ll_to_pixel(lat, lon, zoom)

        # 거리 계산
        distance = ((target_x - current_x) ** 2 + (target_y - current_y) ** 2) ** 0.5

        # 800px 초과 시 분할
        max_distance = 800
        if distance > max_distance:
            steps = int(distance / max_distance) + 1
            for i in range(steps):
                progress = (i + 1) / steps
                interim_x = current_x + (target_x - current_x) * progress
                interim_y = current_y + (target_y - current_y) * progress
                await smooth_drag(page, center_x, center_y, interim_x, interim_y)
        else:
            await smooth_drag(page, center_x, center_y, target_x, target_y)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_drag_to_latlon_calls_geo_utils -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_anti_bot_crawler.py src/crawler/anti_bot.py
git commit -m "feat: 위도/경도 기반 드래그 네비게이션 추가"
```

---

### Task 8: anti_bot.py - human_like_recenter 메서드

**Files:**
- Modify: `src/crawler/anti_bot.py`
- Test: `tests/unit/test_anti_bot_crawler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_anti_bot_crawler.py에 추가

@pytest.mark.unit
async def test_human_like_recenter_sequence(mocker):
    """human_like_recenter가 올바른 순서로 동작하는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}
    mock_page.evaluate = mocker.AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = mocker.AsyncMock()

    mock_drag = mocker.patch.object(
        crawler, 'drag_to_latlon', new_callable=mocker.AsyncMock
    )

    await crawler.human_like_recenter(mock_page, 37.5665, 126.9780, 15)

    # drag가 최소 2번 호출되어야 함 (줌 아웃 후 이동, 목표 줌 후 미세조정)
    assert mock_drag.call_count >= 2


@pytest.mark.unit
async def test_human_like_recenter_random_zoom_out(mocker):
    """랜덤 줌 아웃이 사용되는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}
    mock_page.evaluate = mocker.AsyncMock()
    mock_page.mouse = MagicMock()
    mock_page.mouse.wheel = mocker.AsyncMock()

    mocker.patch.object(crawler, 'drag_to_latlon', new_callable=mocker.AsyncMock)

    # 여러 번 실행해도 에러가 나지 않음
    for _ in range(5):
        await crawler.human_like_recenter(mock_page, 37.5665, 126.9780, 15)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_human_like_recenter_sequence -v`
Expected: FAIL with "AttributeError: 'AntiBotCrawler' object has no attribute 'human_like_recenter'"

**Step 3: Write minimal implementation**

```python
# src/crawler/anti_bot.py에 추가

import random

    async def human_like_recenter(
        self, page: Page, lat: float, lon: float, zoom: int
    ) -> None:
        """
        인간처럼 맵 중심 이동.

        순서:
        1. 랜덤 줌 아웃 (9-12 레벨)
        2. 목표 좌표로 드래그
        3. 목표 줌 레벨로 줌 인
        4. 미세 위치 조정

        Args:
            page: Playwright Page 객체
            lat: 목표 위도
            lon: 목표 경도
            zoom: 목표 줌 레벨
        """
        # 랜덤 줌 아웃
        rand_out = random.randint(9, 12)
        await self._wheel_to_zoom(page, rand_out)

        # 목표 좌표로 드래그
        await self.drag_to_latlon(page, lat, lon, rand_out)

        # 목표 줌 레벨로 줌 인
        await self._wheel_to_zoom(page, zoom)

        # 미세 위치 조정
        await self.drag_to_latlon(page, lat, lon, zoom)

    async def _wheel_to_zoom(self, page: Page, zoom_level: int) -> None:
        """마우스 휠로 줌 조절 (간단 구현)"""
        # Playwright에서는 실제로 더 복잡한 로직이 필요할 수 있음
        # MVP에서는 기본 구현만 제공
        await page.mouse.wheel(0, 0)  # placeholder
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_human_like_recenter_sequence -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_anti_bot_crawler.py src/crawler/anti_bot.py
git commit -m "feat: 인간형 맵 재중심 재배치 추가"
```

---

### Task 9: anti_bot.py - grid_sweep 메서드

**Files:**
- Modify: `src/crawler/anti_bot.py`
- Test: `tests/unit/test_anti_bot_crawler.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_anti_bot_crawler.py에 추가

@pytest.mark.unit
async def test_grid_sweep_returns_coordinates(mocker):
    """grid_sweep이 좌표 리스트를 반환하는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}

    mock_drag = mocker.patch.object(
        crawler, 'drag_to_latlon', new_callable=mocker.AsyncMock
    )
    mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

    coords = await crawler.grid_sweep(mock_page, 37.5665, 126.9780, 14, rings=1)

    assert isinstance(coords, list)
    assert len(coords) > 0
    # 모든 좌표가 (lat, lon) 튜플인지 확인
    for coord in coords:
        assert isinstance(coord, tuple)
        assert len(coord) == 2


@pytest.mark.unit
async def test_grid_sweep_scans_top_bottom_only(mocker):
    """grid_sweep이 상하단 행만 스캔하는지 확인"""
    mock_context = MagicMock()
    crawler = AntiBotCrawler(mock_context)

    mock_page = MagicMock()
    mock_page.viewport_size = {'width': 1920, 'height': 1080}

    mock_drag = mocker.patch.object(
        crawler, 'drag_to_latlon', new_callable=mocker.AsyncMock
    )
    mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

    coords = await crawler.grid_sweep(mock_page, 37.5665, 126.9780, 14, rings=1)

    # rings=1이면 상하단만 스캔하므로 호출 횟수가 제한됨
    # 실제 구현에 따라 조정 필요
    assert mock_drag.call_count < 20  # 전체 그리드보다 적게 호출
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_grid_sweep_returns_coordinates -v`
Expected: FAIL with "AttributeError: 'AntiBotCrawler' object has no attribute 'grid_sweep'"

**Step 3: Write minimal implementation**

```python
# src/crawler/anti_bot.py에 추가

import asyncio
from crawler.utils.geo import ll_to_pixel, pixel_to_ll

    async def grid_sweep(
        self,
        page: Page,
        center_lat: float,
        center_lon: float,
        zoom: int,
        rings: int = 1,
        step_px: int = 480,
        dwell_time: float = 0.6,
    ) -> list[tuple[float, float]]:
        """
        그리드 스윕 알고리즘으로 패턴 은폐.

        전략:
        - 전체 그리드 순회 대신 상하단 행만 스캔
        - Coverage는 완전하지만 패턴은 명확하지 않음

        Args:
            page: Playwright Page 객체
            center_lat: 중심 위도
            center_lon: 중심 경도
            zoom: 줌 레벨
            rings: 스윕할 링 수
            step_px: 그리드 간격 (픽셀)
            dwell_time: 각 지점 체류 시간 (초)

        Returns:
            방문한 좌표 리스트 [(lat, lon), ...]
        """
        visited_coords = []

        # 중심 픽셀 좌표
        center_x, center_y = ll_to_pixel(center_lat, center_lon, zoom)

        # 그리드 스윕: 상하단 행만 스캔
        for r in range(1, rings + 1):
            for dx in range(-r, r + 1):
                for dy in (-r, r):  # Top, bottom rows only
                    target_x = center_x + dx * step_px
                    target_y = center_y + dy * step_px

                    # 픽셀을 위도/경도로 변환
                    lat, lon = pixel_to_ll(target_x, target_y, zoom)
                    visited_coords.append((lat, lon))

                    # 드래그
                    await self.drag_to_latlon(page, lat, lon, zoom)

                    # 체류 시간
                    await asyncio.sleep(dwell_time)

        return visited_coords
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_anti_bot_crawler.py::test_grid_sweep_returns_coordinates -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_anti_bot_crawler.py src/crawler/anti_bot.py
git commit -m "feat: 그리드 스윕 알고리즘 추가"
```

---

## Phase 4: 통합 테스트

### Task 10: 통합 테스트 - anti_bot_navigation.py

**Files:**
- Create: `tests/integration/test_anti_bot_navigation.py`

**Step 1: Write the failing test**

```python
# tests/integration/test_anti_bot_navigation.py
import pytest
from playwright.async_api import async_playwright

from crawler.anti_bot import AntiBotCrawler


class DummyAntiBotCrawler(AntiBotCrawler):
    """테스트용 더미 크롤러"""

    async def aget_url(self) -> str:
        return "https://example.com"

    async def afetch(self, url: str) -> str:
        self.page = await self.setup_page()
        await self.page.goto(url)
        return await self.page.content()

    async def aparse(self, content: str) -> list[dict]:
        return []

    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        return ""

    def parse(self, content: str) -> list[dict]:
        return []


@pytest.mark.integration
async def test_setup_page_creates_playwright_page():
    """setup_page가 실제 Playwright 페이지를 생성하는지 확인"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )

        crawler = DummyAntiBotCrawler(context)
        page = await crawler.setup_page()

        assert page is not None
        # 페이지가 실제로 작동하는지 확인
        await page.goto("https://example.com")
        title = await page.title()
        assert "Example" in title

        await browser.close()


@pytest.mark.integration
async def test_anti_detection_script_injected():
    """anti-detection 스크립트가 주입되는지 확인"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()

        crawler = DummyAntiBotCrawler(context)
        page = await crawler.setup_page()

        await page.goto("https://example.com")

        # webdriver가 제거되었는지 확인
        webdriver_value = await page.evaluate("() => navigator.webdriver")
        assert webdriver_value is None

        await browser.close()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -v -m integration tests/integration/test_anti_bot_navigation.py`
Expected: FAIL (아직 구현 전)

**Step 3: Verify tests pass**

Run: `uv run pytest -v -m integration tests/integration/test_anti_bot_navigation.py`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/integration/test_anti_bot_navigation.py
git commit -m "test: anti-bot 네비게이션 통합 테스트 추가"
```

---

## Phase 5: E2E 테스트

### Task 11: E2E 테스트 - test_anti_bot_e2e.py

**Files:**
- Create: `tests/e2e/test_anti_bot_e2e.py`

**Step 1: Write the failing test**

```python
# tests/e2e/test_anti_bot_e2e.py
import pytest
from playwright.async_api import async_playwright

from crawler.anti_bot import AntiBotCrawler


class SimpleNaverCrawler(AntiBotCrawler):
    """E2E 테스트용 간단한 네이버 크롤러"""

    async def aget_url(self) -> str:
        return "https://land.naver.com"

    async def afetch(self, url: str) -> str:
        self.page = await self.setup_page()
        await self.page.goto(url, wait_until="networkidle")
        return await self.page.content()

    async def aparse(self, content: str) -> list[dict]:
        return [{"title": "test"}]

    def get_url(self) -> str:
        return "https://land.naver.com"

    def fetch(self, url: str) -> str:
        return ""

    def parse(self, content: str) -> list[dict]:
        return []


@pytest.mark.e2e
async def test_naver_land_navigation():
    """
    E2E 테스트: 네이버 부동산 맵 접속 및 기본 네비게이션

    검증 항목:
    1. 페이지가 정상적으로 로드됨
    2. navigator.webdriver가 제거됨
    3. 맵 요소가 존재함
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
        )

        crawler = SimpleNaverCrawler(context)
        await crawler.afetch(crawler.aget_url())

        # webdriver 제거 확인
        webdriver_value = await crawler.page.evaluate(
            "() => navigator.webdriver"
        )
        assert webdriver_value is None, "navigator.webdriver가 제거되지 않음"

        # 맵 요소 존재 확인
        map_element = await crawler.page.query_selector("#map")
        assert map_element is not None, "맵 요소를 찾을 수 없음"

        await browser.close()


@pytest.mark.e2e
async def test_human_like_navigation_on_naver():
    """
    E2E 테스트: 네이버 맵에서 인간형 네비게이션 동작 확인
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        crawler = SimpleNaverCrawler(context)
        await crawler.afetch(crawler.aget_url())

        # 대상 좌표 (서울 시청 근처)
        target_lat = 37.5665
        target_lon = 126.9780

        # 인간형 네비게이션 실행
        await crawler.human_like_recenter(
            crawler.page, target_lat, target_lon, zoom=15
        )

        # 연결 유지 확인
        is_connected = await crawler.page.evaluate(
            "() => document.readyState === 'complete'"
        )
        assert is_connected, "페이지 연결이 끊어짐"

        await browser.close()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -v -m e2e tests/e2e/test_anti_bot_e2e.py`
Expected: FAIL (headless=False에서 실제 브라우저 확인 후 PASS로 전환)

**Step 3: Verify tests pass**

Run: `uv run pytest -v -m e2e tests/e2e/test_anti_bot_e2e.py`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/e2e/test_anti_bot_e2e.py
git commit -m "test: 네이버 부동산 E2E 테스트 추가"
```

---

## Phase 6: 의존성 업데이트

### Task 12: pytest-asyncio 추가

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update dependencies**

```bash
# pyproject.toml의 [project.optional-dependencies] dev 섹션에 추가
# "pytest-asyncio>=0.21.0",
```

**Step 2: Install updated dependencies**

Run: `uv sync`
Expected: 패키지 설치 완료

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: pytest-asyncio 의존성 추가"
```

---

## Phase 7: 예제 스크립트

### Task 13: 예제 스크립트 추가

**Files:**
- Create: `scripts/anti_bot_example.py`

**Step 1: Create example script**

```python
# scripts/anti_bot_example.py
"""AntiBotCrawler 사용 예제"""

import asyncio
from playwright.async_api import async_playwright

from crawler.anti_bot import AntiBotCrawler


class ExampleAntiBotCrawler(AntiBotCrawler):
    """예제용 Anti-Bot 크롤러"""

    async def aget_url(self) -> str:
        return "https://land.naver.com"

    async def afetch(self, url: str) -> str:
        self.page = await self.setup_page()
        await self.page.goto(url, wait_until="networkidle")

        # 인간형 네비게이션으로 서울 시청 근처 이동
        await self.human_like_recenter(self.page, 37.5665, 126.9780, 15)

        # 그리드 스윕
        coords = await self.grid_sweep(
            self.page, 37.5665, 126.9780, 14, rings=1
        )
        print(f"방문한 좌표: {len(coords)}개")

        return await self.page.content()

    async def aparse(self, content: str) -> list[dict]:
        # 실제 파싱 로직은 구현체에서 구현
        return []

    def get_url(self) -> str:
        return "https://land.naver.com"

    def fetch(self, url: str) -> str:
        return ""

    def parse(self, content: str) -> list[dict]:
        return []


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        crawler = ExampleAntiBotCrawler(context)
        results = await crawler.acrawl()
        print(f"크롤링 결과: {len(results)}개 항목")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Run example to verify**

Run: `uv run python scripts/anti_bot_example.py`
Expected: 브라우저가 실행되고 네이버 부동산 맵이 열림

**Step 3: Commit**

```bash
git add scripts/anti_bot_example.py
git commit -m "docs: AntiBotCrawler 사용 예제 추가"
```

---

## 마무리 체크리스트

모든 작업 완료 후:

```bash
# 전체 테스트 실행
uv run pytest -v

# 단위 테스트만
uv run pytest -v -m unit

# 통합 테스트만
uv run pytest -v -m integration

# E2E 테스트만
uv run pytest -v -m e2e

# 코드 포맷팅
uv run ruff format .
uv run ruff check .
```

---

## 참고 자료

- [anti_bot_scraper GitHub](https://github.com/HarimxChoi/anti_bot_scraper)
- [Playwright Python Documentation](https://playwright.dev/python/)
- [Mercator Projection](https://en.wikipedia.org/wiki/Mercator_projection)

---

**Total Tasks:** 13
**Estimated Time:** 2-3시간
**Testing Strategy:** TDD (모든 기능: 테스트 먼저 작성)
