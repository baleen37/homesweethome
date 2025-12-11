from pytest import MonkeyPatch

from crawler.config import CrawlerConfig


def test_config_default_values() -> None:
    config = CrawlerConfig()
    assert config.timeout == 30
    assert config.headless is True
    assert config.output_file is None
    assert config.page_size == 50  # Updated to match Hogangnono default
    assert config.retry_attempts == 3
    assert config.rate_limit_delay == 2.0  # Updated from delay_seconds
    assert config.use_threading is False
    assert config.max_workers == 4


def test_config_from_env(monkeypatch: MonkeyPatch) -> None:
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "data.csv")
        monkeypatch.setenv("CRAWLER_TIMEOUT", "60")
        monkeypatch.setenv("CRAWLER_HEADLESS", "false")
        monkeypatch.setenv("CRAWLER_OUTPUT_FILE", output_path)

        config = CrawlerConfig.from_env()
        assert config.timeout == 60
        assert config.headless is False
        assert config.output_file == output_path


def test_config_from_env_with_overrides(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLER_TIMEOUT", "60")

    config = CrawlerConfig.from_env(timeout=90)
    assert config.timeout == 90
