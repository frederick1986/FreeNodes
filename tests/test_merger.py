"""Tests for Merger: txt merge, yaml merge, proxy dedup, region detection.

Run: pytest tests/test_merger.py -v
"""
import yaml
from pathlib import Path
from src.merger import Merger, MergeResult, REGION_KEYWORDS


# ═══════════════════════════════════════════════════════════════
# _dedup_proxies
# ═══════════════════════════════════════════════════════════════

class TestDedupProxies:

    def test_dedup_by_server_port_type(self):
        proxies = [
            {"name": "HK 01", "server": "1.1.1.1", "port": 443, "type": "vmess"},
            {"name": "HK 01 dup", "server": "1.1.1.1", "port": 443, "type": "vmess"},
        ]
        result = Merger._dedup_proxies(proxies)
        assert len(result) == 1

    def test_preserves_different_proxies(self):
        proxies = [
            {"name": "HK 01", "server": "1.1.1.1", "port": 443, "type": "vmess"},
            {"name": "JP 01", "server": "2.2.2.2", "port": 443, "type": "trojan"},
        ]
        result = Merger._dedup_proxies(proxies)
        assert len(result) == 2

    def test_renames_name_conflict(self):
        proxies = [
            {"name": "HK 01", "server": "1.1.1.1", "port": 443, "type": "vmess"},
            {"name": "HK 01", "server": "2.2.2.2", "port": 443, "type": "trojan"},
        ]
        result = Merger._dedup_proxies(proxies)
        names = [p["name"] for p in result]
        assert "HK 01" in names
        assert "HK 01_2" in names

    def test_empty_list(self):
        assert Merger._dedup_proxies([]) == []

    def test_skips_non_dict_items(self):
        deduped = Merger._dedup_proxies([{}, None])
        assert len(deduped) == 0


# ═══════════════════════════════════════════════════════════════
# _detect_regions
# ═══════════════════════════════════════════════════════════════

class TestDetectRegions:

    @staticmethod
    def _detect(names):
        """Helper to call the static method."""
        return Merger._detect_regions(names)

    def test_hk_match(self):
        names = ["HK 01", "香港 02", "HongKong 03", "US 01"]
        regions = self._detect(names)
        assert "🇭🇰 HK 香港" in regions
        assert len(regions["🇭🇰 HK 香港"]) == 3

    def test_us_match(self):
        names = ["US 01", "美国 02", "America 03"]
        regions = self._detect(names)
        assert "🇺🇸 US 美国" in regions
        assert len(regions["🇺🇸 US 美国"]) == 3

    def test_unmatched_goes_to_other(self):
        names = ["zzz-top", "aaaa-bb"]
        regions = self._detect(names)
        assert "🌍 其他" in regions
        assert len(regions["🌍 其他"]) == 2

    def test_case_insensitive(self):
        names = ["hk_01", "Hk_02", "us_03"]
        regions = self._detect(names)
        assert "🇭🇰 HK 香港" in regions
        assert len(regions["🇭🇰 HK 香港"]) == 2

    def test_empty_names(self):
        assert self._detect([]) == {}

    def test_jp_match_via_tokyo(self):
        names = ["Tokyo 01", "TYO 02"]
        regions = self._detect(names)
        assert "🇯🇵 JP 日本" in regions
        assert len(regions["🇯🇵 JP 日本"]) == 2


# ═══════════════════════════════════════════════════════════════
# REGION_KEYWORDS integrity
# ═══════════════════════════════════════════════════════════════

class TestRegionKeywords:

    def test_no_duplicate_keywords_across_regions(self):
        """Each keyword should belong to exactly one region to avoid ambiguity."""
        all_keywords: list[str] = []
        for keywords in REGION_KEYWORDS.values():
            all_keywords.extend(k.lower() for k in keywords)
        assert len(all_keywords) == len(set(all_keywords)), \
            f"duplicate keywords found: {[k for k in all_keywords if all_keywords.count(k) > 1]}"


# ═══════════════════════════════════════════════════════════════
# Integration with real files (requires nodes/ directory)
# ═══════════════════════════════════════════════════════════════

class TestFileIntegration:

    def test_merge_creates_output_files(self, tmp_path):
        """Run merger against a temp directory with sample yaml/txt files."""
        nodes = tmp_path / "nodes"
        nodes.mkdir()

        # Create a sample txt file (base64 encoded V2Ray sub)
        import base64
        txt_content = base64.b64encode(
            b"vless://418048af-a293-4b99-9b0c-98ca3580dd24@example.com:443\n"
            b"vless://518048af-a293-4b99-9b0c-98ca3580dd24@example.org:8443\n"
        ).decode()
        (nodes / "site1.txt").write_text(txt_content, encoding="utf-8")

        # Create a sample yaml file
        yaml_content = """proxies:
  - {name: HK 01, server: 1.1.1.1, port: 443, type: vmess, uuid: 418048af-a293-4b99-9b0c-98ca3580dd24}
  - {name: JP 01, server: 2.2.2.2, port: 443, type: trojan, password: secret}
"""
        (nodes / "site1.yaml").write_text(yaml_content, encoding="utf-8")

        merger = Merger(nodes_dir=str(nodes))
        result = merger.run()

        assert (nodes / "merged.txt").exists()
        assert (nodes / "merged.yaml").exists()
        assert (nodes / "provider.yaml").exists()
        assert result.total_nodes == 2

    def test_merge_empty_dir(self, tmp_path):
        nodes = tmp_path / "nodes"
        nodes.mkdir()
        merger = Merger(nodes_dir=str(nodes))
        result = merger.run()
        assert result.total_nodes == 0
        assert result.merged_txt == ""
        assert result.merged_yaml == ""
        assert result.provider_yaml == ""


# ═══════════════════════════════════════════════════════════════
# MergeResult dataclass
# ═══════════════════════════════════════════════════════════════

class TestMergeResult:

    def test_defaults(self):
        r = MergeResult()
        assert r.merged_txt == ""
        assert r.total_nodes == 0
        assert r.region_count == {}

class TestPublishedOutputs:
    @staticmethod
    def _sources(tmp_path):
        nodes = tmp_path / "nodes"
        nodes.mkdir()
        (nodes / "site1.txt").write_text(
            "vless://418048af-a293-4b99-9b0c-98ca3580dd24@example.com:443",
            encoding="utf-8",
        )
        (nodes / "site1.yaml").write_text(
            "proxies:\n  - {name: HK 01, server: example.com, port: 443, type: vmess, "
            "uuid: 418048af-a293-4b99-9b0c-98ca3580dd24}\n",
            encoding="utf-8",
        )
        return nodes

    def test_outputs_and_compatibility_are_identical(self, tmp_path, monkeypatch):
        self._sources(tmp_path)
        monkeypatch.chdir(tmp_path)
        before = {p.name: p.read_bytes() for p in Path("nodes").iterdir()}
        result = Merger(nodes_dir="nodes", output_dir="outputs").run()
        for generated in (result.merged_txt, result.merged_yaml, result.provider_yaml):
            path = Path(generated)
            assert path.parent == Path("outputs")
            assert path.stat().st_size > 0
            assert path.read_bytes() == (Path("nodes") / path.name).read_bytes()
        for name, content in before.items():
            assert (Path("nodes") / name).read_bytes() == content
        provider = yaml.safe_load(Path(result.provider_yaml).read_text(encoding="utf-8"))
        assert provider["proxy-providers"]["site1"]["path"] == "./nodes/site1.yaml"
        # Relative provider paths resolve from Mihomo HomeDir (the repository).
        for item in provider["proxy-providers"].values():
            assert (tmp_path / item["path"]).is_file()

    def test_later_runs_refresh_both_locations(self, tmp_path, monkeypatch):
        self._sources(tmp_path)
        monkeypatch.chdir(tmp_path)
        merger = Merger(nodes_dir="nodes", output_dir="outputs")
        merger.run()
        old = Path("outputs/merged.txt").read_bytes()
        Path("nodes/site1.txt").write_text(
            "vless://518048af-a293-4b99-9b0c-98ca3580dd24@next.example:8443",
            encoding="utf-8",
        )
        # Previous aggregate files in nodes are never inputs to the next merge.
        result = merger.run()
        assert result.total_nodes == 1
        assert Path("outputs/merged.txt").read_bytes() != old
        assert "next.example" in Path("outputs/merged.txt").read_text(encoding="utf-8")
        for name in ("merged.txt", "merged.yaml", "provider.yaml"):
            assert Path("outputs", name).read_bytes() == Path("nodes", name).read_bytes()

    def test_custom_source_and_nested_output_paths(self, tmp_path, monkeypatch):
        nodes = self._sources(tmp_path)
        nodes.rename(tmp_path / "source-data")
        monkeypatch.chdir(tmp_path)
        result = Merger(nodes_dir="source-data", output_dir="public/final").run()
        assert Path(result.merged_txt) == Path("public/final/merged.txt")
        provider = yaml.safe_load(Path(result.provider_yaml).read_text(encoding="utf-8"))
        assert provider["proxy-providers"]["site1"]["path"] == "./source-data/site1.yaml"
        for name in ("merged.txt", "merged.yaml", "provider.yaml"):
            assert Path("public/final", name).read_bytes() == Path("source-data", name).read_bytes()

    def test_reproducible_from_same_inputs(self, tmp_path, monkeypatch):
        self._sources(tmp_path)
        monkeypatch.chdir(tmp_path)
        # Freeze only the timestamp header; node processing remains real.
        monkeypatch.setattr(Merger, "_header", staticmethod(lambda desc: "# fixed header\n"))
        Merger(nodes_dir="nodes", output_dir="outputs").run()
        before = {p.name: p.read_bytes() for p in Path("outputs").iterdir()}
        Merger(nodes_dir="nodes", output_dir="outputs").run()
        assert before == {p.name: p.read_bytes() for p in Path("outputs").iterdir()}
