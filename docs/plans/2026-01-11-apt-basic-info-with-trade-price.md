# 아파트 기본정보 + 실거래가 CSV 내보내기 구현 계획 (수정)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ASIL 아파트 목록과 실거래가를 별도 CSV로 내보내는 기능을 구현하고 E2E 테스트로 검증한다.

**Architecture:**
1. 아파트 목록 크롤링 → CSV #1 (기본정보)
2. 실거래가 크롤링 → CSV #2 (apt_seq로 조인)
3. 두 CSV는 `apt_seq`(seq)로 관계형 DB처럼 조인 가능

**Tech Stack:** Python 3.11+, pytest, Pydantic, UTF-8 CSV

---

## 선행 조건 확인

### Task 0: 기존 기능 확인

**Files:**
- Read: `src/crawler/asil.py` (AsilAptListCrawler, AsilTradePriceCrawler)
- Read: `src/crawler/dto/asil_apt_list.py`
- Read: `src/crawler/dto/asil_trade_price.py`
- Read: `src/crawler/constants/legal_dong_codes.py`

**Step 1: 기존 아파트 목록 E2E 테스트 실행**

```bash
uv run pytest tests/e2e/test_asil_seoul_e2e.py -v -m e2e
```

Expected: 기존 테스트 통과

**Step 2: 실거래가 DTO 구조 확인**

`AsilTradePriceDTO` 필드 확인:
- `val`: 거래가 (원)
- `yyyymm`: 거래년월 (YYYYMM)
- `area`: 면적
- `deal_gubun`: 거래구분

**Step 3: legal_dong_codes 확인**

`SEOUL_SAMPLE_DONG_CODES` 또는 `SEOUL_DONG_CODES` 확인

---

## 본 구현

### Task 1: CSV 내보내기 유틸리티 구현

**Files:**
- Create: `src/crawler/export/csv_export.py`
- Create: `tests/unit/test_csv_export.py`

**Step 1: 실패하는 테스트 작성**

```python
# tests/unit/test_csv_export.py
import tempfile
from pathlib import Path

def test_export_apt_list_to_csv():
    """아파트 목록 CSV 내보내기"""
    from src.crawler.dto.asil_apt_list import AsilAptListDTO
    from src.crawler.export.csv_export import export_apt_list_to_csv

    data = [
        AsilAptListDTO(
            seq=1,
            name="테스트아파트",
            dong="1150010100",
            dongname="역삼동",
            build_year=2000,
            household=100,
            lat=37.5,
            lng=127.0,
        ),
        AsilAptListDTO(
            seq=2,
            name="무실거래아파트",
            dong="1150010200",
            dongname="삼성동",
            build_year=1995,
            household=50,
            lat=37.51,
            lng=127.01,
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "apt_list.csv"
        export_apt_list_to_csv(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 2줄
        assert len(lines) == 3
        # 헤더 검증
        assert "seq" in lines[0]
        assert "name" in lines[0]

def test_export_trade_price_to_csv():
    """실거래가 CSV 내보내기"""
    from src.crawler.dto.asil_trade_price import AsilTradePriceDTO
    from src.crawler.export.csv_export import export_trade_price_to_csv

    data = [
        AsilTradePriceDTO(
            apt_seq=1,
            val=100000,
            yyyymm="202401",
            area="84",
            deal_gubun="아파트",
        ),
        AsilTradePriceDTO(
            apt_seq=1,
            val=120000,
            yyyymm="202406",
            area="84",
            deal_gubun="아파트",
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "trade_price.csv"
        export_trade_price_to_csv(data, output_path)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # 헤더 + 데이터 2줌
        assert len(lines) == 3
        assert "apt_seq" in lines[0]
```

Run: `uv run pytest tests/unit/test_csv_export.py -v`
Expected: FAIL

**Step 2: CSV 내보내기 구현**

```python
# src/crawler/export/csv_export.py
import csv
from pathlib import Path

from src.crawler.dto.asil_apt_list import AsilAptListDTO
from src.crawler.dto.asil_trade_price import AsilTradePriceDTO


def export_apt_list_to_csv(
    data: list[AsilAptListDTO],
    output_path: Path,
) -> None:
    """
    아파트 기본정보를 CSV로 내보냅니다.

    CSV 필드: seq, name, dong, dongname, build_year, household, lat, lng

    Args:
        data: 아파트 기본정보 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seq",
        "name",
        "dong",
        "dongname",
        "build_year",
        "household",
        "lat",
        "lng",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for apt in data:
            row = {
                "seq": apt.seq,
                "name": apt.name,
                "dong": apt.dong,
                "dongname": apt.dongname,
                "build_year": apt.build_year,
                "household": apt.household,
                "lat": apt.lat,
                "lng": apt.lng,
            }
            writer.writerow(row)


def export_trade_price_to_csv(
    data: list[AsilTradePriceDTO],
    output_path: Path,
) -> None:
    """
    실거래가 정보를 CSV로 내보냅니다.

    CSV 필드: apt_seq, yyyymm, amount_million, area, deal_gubun

    Args:
        data: 실거래가 리스트
        output_path: 출력 CSV 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "apt_seq",
        "yyyymm",
        "amount_million",
        "area",
        "deal_gubun",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for trade in data:
            row = {
                "apt_seq": trade.apt_seq,
                "yyyymm": trade.yyyymm,
                "amount_million": trade.val,
                "area": trade.area,
                "deal_gubun": trade.deal_gubun,
            }
            writer.writerow(row)
```

**Step 3: export 패키지 초기화**

```python
# src/crawler/export/__init__.py
from .csv_export import export_apt_list_to_csv, export_trade_price_to_csv
```

**Step 4: 테스트 실행**

Run: `uv run pytest tests/unit/test_csv_export.py -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/crawler/export/ tests/unit/test_csv_export.py
git commit -m "feat: 아파트 목록/실거래가 CSV 내보내기 추가"
```

---

### Task 2: 통합 크롤링 명령어 구현

**Files:**
- Create: `src/crawler/commands/apt_and_trade_crawl.py`

**Step 1: 통합 크롤링 함수 구현**

```python
# src/crawler/commands/apt_and_trade_crawl.py
from pathlib import Path
from src.crawler.asil import AsilAptListCrawler, AsilTradePriceCrawler
from src.crawler.export.csv_export import export_apt_list_to_csv, export_trade_price_to_csv


def crawl_apt_and_trade(
    dong_codes: list[str],
    apt_output_path: Path,
    trade_output_path: Path,
    area_m2: float = 84.0,
    sido_code: int = 11,
    max_per_dong: int = 10,
) -> tuple[int, int]:
    """
    아파트 기본정보와 실거래가를 각각 별도 CSV로 크롤링합니다.

    Args:
        dong_codes: 법정동 코드 리스트
        apt_output_path: 아파트 목록 출력 경로
        trade_output_path: 실거래가 출력 경로
        area_m2: 실거래가 조회 면적 (m²)
        sido_code: 시도 코드 (서울: 11)
        max_per_dong: 동별 최대 조회 수

    Returns:
        (아파트 수, 실거래가 수)
    """
    all_apts = []
    all_trades = []

    for dong_code in dong_codes:
        print(f"동 코드 {dong_code} 조회 중...")
        apt_crawler = AsilAptListCrawler(dong_code=dong_code)
        apt_list = apt_crawler.crawl()
        all_apts.extend(apt_list)

        for apt in apt_list[:max_per_dong]:
            print(f"  - {apt.name} 실거래가 조회 중...")
            trade_crawler = AsilTradePriceCrawler(
                apt_code=str(apt.seq),
                sido_code=sido_code,
                area_m2=area_m2,
            )
            trade_prices = trade_crawler.crawl()

            # 실거래가에 apt_seq 추가
            for trade in trade_prices:
                trade.apt_seq = apt.seq
            all_trades.extend(trade_prices)

    export_apt_list_to_csv(all_apts, apt_output_path)
    export_trade_price_to_csv(all_trades, trade_output_path)

    print(f"완료: {len(all_apts)}개 아파트, {len(all_trades)}개 실거래가")
    print(f"  - 아파트 목록: {apt_output_path}")
    print(f"  - 실거래가: {trade_output_path}")

    return len(all_apts), len(all_trades)
```

**Step 2: 단위 테스트**

```python
# tests/unit/test_apt_and_trade_crawl.py
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile

def test_crawl_apt_and_trade():
    """통합 크롤링 함수 테스트"""
    from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
    from src.crawler.dto.asil_apt_list import AsilAptListDTO
    from src.crawler.dto.asil_trade_price import AsilTradePriceDTO

    # Mock 크롤러
    with patch('src.crawler.commands.apt_and_trade_crawl.AsilAptListCrawler') as MockAptCrawler, \
         patch('src.crawler.commands.apt_and_trade_crawl.AsilTradePriceCrawler') as MockTradeCrawler:

        # Mock 설정
        mock_apt_crawler = Mock()
        mock_apt_crawler.crawl.return_value = [
            AsilAptListDTO(
                seq=1, name="테스트", dong="1150010100", dongname="역삼동",
                build_year=2000, household=100, lat=37.5, lng=127.0,
            )
        ]
        MockAptCrawler.return_value = mock_apt_crawler

        mock_trade_crawler = Mock()
        mock_trade_crawler.crawl.return_value = [
            AsilTradePriceDTO(apt_seq=1, val=100000, yyyymm="202401", area="84", deal_gubun="아파트")
        ]
        MockTradeCrawler.return_value = mock_trade_crawler

        with tempfile.TemporaryDirectory() as tmpdir:
            apt_path = Path(tmpdir) / "apt.csv"
            trade_path = Path(tmpdir) / "trade.csv"

            apt_count, trade_count = crawl_apt_and_trade(
                dong_codes=["1150010100"],
                apt_output_path=apt_path,
                trade_output_path=trade_path,
                max_per_dong=1,
            )

            assert apt_count == 1
            assert trade_count == 1
            assert apt_path.exists()
            assert trade_path.exists()
```

Run: `uv run pytest tests/unit/test_apt_and_trade_crawl.py -v`
Expected: PASS

**Step 3: 커밋**

```bash
git add src/crawler/commands/apt_and_trade_crawl.py tests/unit/test_apt_and_trade_crawl.py
git commit -m "feat: 아파트+실거래가 통합 크롤링 함수 추가"
```

---

### Task 3: 통합 테스트 (실제 API 사용)

**Files:**
- Create: `tests/integration/test_apt_and_trade_integration.py`

**Step 1: 실패하는 테스트 작성**

```python
# tests/integration/test_apt_and_trade_integration.py
import pytest
from pathlib import Path
from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade


@pytest.mark.integration
def test_apt_and_trade_full_workflow(tmp_path):
    """
    전체 워크플로우 테스트:
    1. 아파트 목록 + 실거래가 크롤링
    2. 두 CSV 파일 생성
    3. 데이터 검증
    """
    apt_path = tmp_path / "apt_list.csv"
    trade_path = tmp_path / "trade_price.csv"

    apt_count, trade_count = crawl_apt_and_trade(
        dong_codes=["1150010100"],  # 역삼1동
        apt_output_path=apt_path,
        trade_output_path=trade_path,
        max_per_dong=3,  # 최대 3개만 테스트
    )

    # 검증
    assert apt_count > 0, "아파트 목록이 1개 이상이어야 함"
    assert apt_path.exists()
    assert trade_path.exists()

    # CSV 내용 검증
    apt_content = apt_path.read_text(encoding="utf-8")
    trade_content = trade_path.read_text(encoding="utf-8")

    apt_lines = apt_content.strip().split("\n")
    trade_lines = trade_content.strip().split("\n")

    # 헤더 + 데이터
    assert len(apt_lines) >= 2
    assert "seq" in apt_lines[0]

    # 실거래가는 없을 수도 있음
    if trade_count > 0:
        assert len(trade_lines) >= 2
        assert "apt_seq" in trade_lines[0]
```

Run: `uv run pytest tests/integration/test_apt_and_trade_integration.py -v`
Expected: PASS

**Step 2: 커밋**

```bash
git add tests/integration/test_apt_and_trade_integration.py
git commit -m "test: 아파트+실거래가 통합 테스트 추가"
```

---

### Task 4: E2E 테스트 (실제 서울 데이터)

**Files:**
- Create: `tests/e2e/test_apt_and_trade_e2e.py`

**Step 1: E2E 테스트 작성**

```python
# tests/e2e/test_apt_and_trade_e2e.py
import pytest
from pathlib import Path
from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade


@pytest.mark.e2e
def test_seoul_sample_apt_and_trade_e2e(tmp_path):
    """
    서울 샘플 동 코드에 대한 E2E 테스트
    """
    apt_path = tmp_path / "seoul_apt_list_e2e.csv"
    trade_path = tmp_path / "seoul_trade_price_e2e.csv"

    # 샘플 동 코드 (역삼1동, 삼성동 등)
    dong_codes = ["1150010100", "1150010200"]

    apt_count, trade_count = crawl_apt_and_trade(
        dong_codes=dong_codes,
        apt_output_path=apt_path,
        trade_output_path=trade_path,
        max_per_dong=5,
    )

    # 검증
    assert apt_count > 0
    assert apt_path.exists()

    apt_content = apt_path.read_text(encoding="utf-8")
    lines = apt_content.strip().split("\n")
    assert len(lines) >= 2

    print(f"E2E 결과: {apt_count}개 아파트, {trade_count}개 실거래가")
    print(f"  - 아파트: {apt_path}")
    print(f"  - 실거래가: {trade_path}")
```

Run: `uv run pytest tests/e2e/test_apt_and_trade_e2e.py -v -m e2e`
Expected: PASS

**Step 2: 커밋**

```bash
git add tests/e2e/test_apt_and_trade_e2e.py
git commit -m "test: 아파트+실거래가 E2E 테스트 추가"
```

---

### Task 5: CLI 명령어 추가

**Files:**
- Modify: `src/crawler/commands/cli.py`

**Step 1: CLI에 명령어 추가**

```python
# src/crawler/commands/cli.py (기존 코드에 추가)
@click.command()
@click.option("--dong-code", multiple=True, help="법정동 코드")
@click.option("--apt-output", default="output/apt_list.csv", help="아파트 목록 출력 경로")
@click.option("--trade-output", default="output/trade_price.csv", help="실거래가 출력 경로")
@click.option("--area", default=84.0, help="면적 (m²)")
@click.option("--max-per-dong", default=10, help="동별 최대 조회 수")
def crawl_apt_trade(dong_code, apt_output, trade_output, area, max_per_dong):
    """아파트 기본정보 + 실거래가 크롤링 (별도 CSV)"""
    from src.crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
    from src.crawler.constants.legal_dong_codes import SEOUL_DONG_CODES

    codes = list(dong_code) if dong_code else list(SEOUL_DONG_CODES.keys())[:5]
    crawl_apt_and_trade(
        dong_codes=codes,
        apt_output_path=Path(apt_output),
        trade_output_path=Path(trade_output),
        area_m2=area,
        max_per_dong=max_per_dong,
    )
```

**Step 2: 수동 테스트 및 커밋**

```bash
# 수동 테스트
uv run python -m crawler.commands.cli crawl-apt-trade --dong-code 1150010100 --apt-output /tmp/apt.csv --trade-output /tmp/trade.csv

git add src/crawler/commands/cli.py
git commit -m "feat: 아파트+실거래가 CLI 명령어 추가"
```

---

## 완료 체크리스트

- [ ] CSV 내보내기 함수 구현 완료 (export_apt_list_to_csv, export_trade_price_to_csv)
- [ ] 단위 테스트 통과
- [ ] 통합 크롤링 함수 구현 완료 (crawl_apt_and_trade)
- [ ] 통합 테스트 통과
- [ ] E2E 테스트 통과
- [ ] CLI 명령어 동작 확인
- [ ] CSV 출력 파일 검증 (두 파일이 apt_seq로 조인 가능)
