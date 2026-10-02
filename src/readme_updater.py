"""README.md generator — builds subscription table from config + source and merged output directories."""
from datetime import datetime
from pathlib import Path

from src.config import Config


GITHUB_BASE = "https://raw.githubusercontent.com/frederick1986/FreeNodes/refs/heads"
GITHUB_PROXY = "https://gh-proxy.com/raw.githubusercontent.com/frederick1986/FreeNodes/refs/heads"
BRANCH = "feat/ai-crawler-v2"


def build_readme(config: Config) -> str:
    """Generate README.md with subscription table from config site list."""
    today = datetime.now().strftime("%Y-%m-%d")
    nodes_dir = Path(config.output.get("dir", "nodes"))
    merged_dir = Path(config.output.get("merged_dir", "outputs"))

    lines = [
        "# FreeNodes",
        "",
        "v2ray、Clash 免费节点爬虫（AI 版），每日 UTC 04:17（北京时间 12:17）自动运行。",
        "",
        "## 免责声明",
        "",
        "订阅节点仅作学习交流使用，用于查找资料，学习知识，不做任何违法行为。",
        "所有资源均来自互联网，仅供大家交流学习使用，出现违法问题概不负责。",
        "",
        "## v2ray / Clash 订阅列表",
        "",
        "合并订阅位于 `outputs/`，原 `nodes/` 地址继续同步更新。",
        "`provider.yaml` 使用本地来源文件；使用时请将仓库根目录设为 Mihomo 工作目录（`-d`），并保留 `nodes/`。",
        "",
        "| 爬虫目标 | 订阅链接 | 镜像加速订阅链接 | 更新日期 |",
        "| --- | --- | --- | --- |",
    ]

    for site in config.sites:
        name = site.name
        url = site.start_url
        up_date = site.up_date or "—"
        node_count = site.node_count

        # Build file links — one row per available file
        txt_path = nodes_dir / f"{name}.txt"
        yaml_path = nodes_dir / f"{name}.yaml"

        links = []
        mirror_links = []

        if txt_path.exists():
            raw = f"{GITHUB_BASE}/{BRANCH}/{nodes_dir.as_posix()}/{name}.txt"
            mirror = f"{GITHUB_PROXY}/{BRANCH}/{nodes_dir.as_posix()}/{name}.txt"
            links.append(f"[{name}.txt]({raw})")
            mirror_links.append(f"[镜像]({mirror})")
        if yaml_path.exists():
            raw = f"{GITHUB_BASE}/{BRANCH}/{nodes_dir.as_posix()}/{name}.yaml"
            mirror = f"{GITHUB_PROXY}/{BRANCH}/{nodes_dir.as_posix()}/{name}.yaml"
            links.append(f"[{name}.yaml]({raw})")
            mirror_links.append(f"[镜像]({mirror})")

        count_str = f" ({node_count} nodes)" if node_count else ""
        lines.append(
            f"| [{name}]({url}) "
            f"| {'<br>'.join(links) or '—'}{count_str} "
            f"| {'<br>'.join(mirror_links) or '—'} "
            f"| {up_date} |"
        )

    # Merged files row (no blank line before — would break the table)
    merged_links = []
    merged_mirror = []
    for fname in ("merged.txt", "merged.yaml", "provider.yaml"):
        fpath = merged_dir / fname
        if fpath.exists():
            raw = f"{GITHUB_BASE}/{BRANCH}/{merged_dir.as_posix()}/{fname}"
            mirror = f"{GITHUB_PROXY}/{BRANCH}/{merged_dir.as_posix()}/{fname}"
            merged_links.append(f"[{fname}]({raw})")
            merged_mirror.append(f"[镜像]({mirror})")
    if merged_links:
        lines.append(
            f"| [merged](https://github.com/frederick1986/FreeNodes/tree/{BRANCH}) "
            f"| {'<br>'.join(merged_links)} "
            f"| {'<br>'.join(merged_mirror)} "
            f"| {today} |"
        )

    lines.extend([
        "",
        "---",
        "",
        f"*上次更新: {today} | "
        f"运行方式: GitHub Actions (feat/ai-crawler-v2)*",
        "",
    ])

    return "\n".join(lines) + "\n"


def write_readme(config: Config, path: str = "README.md"):
    """Generate and write README.md."""
    content = build_readme(config)
    Path(path).write_text(content, encoding="utf-8")
    print(f"  [readme] {path} updated ({len(content)} chars)")
