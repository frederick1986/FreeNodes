"""Tests for canonical outputs links and source directory compatibility."""
from pathlib import Path
import yaml
from src.config import Config, CrawlConfig, LLMConfig, SiteConfig, load_config, save_config
from src.readme_updater import build_readme


def make_config(output=None):
    return Config(
        sites=[SiteConfig(name="site1", start_url="https://example.com", up_date="2026-09-30")],
        crawl=CrawlConfig(),
        output=output or {"dir": "nodes", "merged_dir": "outputs"},
        llm=LLMConfig(),
    )


def test_source_links_stay_in_nodes_and_merged_links_use_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for folder in ("nodes", "outputs"):
        Path(folder).mkdir()
    Path("nodes/site1.txt").write_text("source fixture", encoding="utf-8")
    for name in ("merged.txt", "merged.yaml", "provider.yaml"):
        Path("outputs", name).write_text("file-presence fixture", encoding="utf-8")
        Path("nodes", name).write_text("compatibility fixture", encoding="utf-8")
    text = build_readme(make_config())
    assert "/nodes/site1.txt" in text
    for name in ("merged.txt", "merged.yaml", "provider.yaml"):
        assert f"/outputs/{name}" in text
        assert f"/nodes/{name}" not in text
    assert "仓库根目录" in text
    assert "2026-09-30" in text


def test_merged_directory_defaults_to_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("outputs").mkdir()
    Path("outputs/merged.txt").write_text("fixture", encoding="utf-8")
    assert "/outputs/merged.txt" in build_readme(make_config({"dir": "nodes"}))


def test_missing_outputs_are_not_linked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("nodes").mkdir()
    Path("nodes/merged.txt").write_text("legacy fixture", encoding="utf-8")
    assert "| [merged]" not in build_readme(make_config())


def test_custom_config_directories_are_used(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("source-data").mkdir()
    Path("public").mkdir()
    Path("source-data/site1.yaml").write_text("fixture", encoding="utf-8")
    Path("public/provider.yaml").write_text("fixture", encoding="utf-8")
    text = build_readme(make_config({"dir": "source-data", "merged_dir": "public"}))
    assert "/source-data/site1.yaml" in text
    assert "/public/provider.yaml" in text


def test_merged_directory_survives_config_save(tmp_path):
    path = tmp_path / "config.yaml"
    config = make_config()
    save_config(config, str(path))
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["output"] == config.output
    assert load_config(str(path)).output["merged_dir"] == "outputs"
