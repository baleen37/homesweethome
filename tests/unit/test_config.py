from crawler.config import CrawlerConfig


def test_config_default_values():
    config = CrawlerConfig()
    assert config.timeout == 30
    assert config.headless is True
    assert config.output_dir == "output"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("TIMEOUT", "60")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("OUTPUT_DIR", "results")

    config = CrawlerConfig.from_env()
    assert config.timeout == 60
    assert config.headless is False
    assert config.output_dir == "results"


def test_config_from_env_with_overrides(monkeypatch):
    monkeypatch.setenv("TIMEOUT", "60")

    config = CrawlerConfig.from_env(timeout=90)
    assert config.timeout == 90
