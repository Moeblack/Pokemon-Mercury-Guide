# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Package frozen atlas inputs for the existing, dependency-free offline UI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas_guide_summaries import build_guide_summaries
from tm_names import TMNames


def main() -> None:
    parser = argparse.ArgumentParser(description="生成离线地图数据包（不渲染底图）")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / "data/atlas_manifest.json").read_text(encoding="utf-8"))
    points = json.loads((root / "data/atlas_points.json").read_text(encoding="utf-8"))
    if not isinstance(manifest.get("maps"), dict) or not isinstance(manifest.get("regions"), dict):
        raise ValueError("manifest.maps / regions 必须是字典")
    if not isinstance(points.get("points"), list):
        raise ValueError("atlas_points.json 必须包含 points 数组")
    tm_names = TMNames(root)
    for point in points['points']:
        raw_title = point.get('title', '')
        for key in ('title', 'detail'):
            if isinstance(point.get(key), str):
                point[key] = tm_names.plain(point[key])
        if raw_title in tm_names.aliases:
            row = tm_names.aliases[raw_title]
            point['search_aliases'] = [row['raw_name'], row['label']]
        for link in point.get('links', []):
            if isinstance(link.get('label'), str):
                link['label'] = tm_names.plain(link['label'])
    report = root / "data/atlas_render_report.json"
    render = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    target = root / "maps"
    for name in ("index.html", "atlas.css", "atlas.js", "atlas-navigation.js", "atlas-world.js", "world-data.js"):
        if not (target / name).is_file():
            raise FileNotFoundError(f"缺少前端源文件：{target / name}")
    guides = tm_names.guide(build_guide_summaries(root))
    data = json.dumps({"manifest": manifest, "points": points, "render": render, "guides": guides}, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    output = target / "atlas-data.js"
    temporary = output.with_suffix(".js.tmp")
    temporary.write_text("window.ATLAS=" + data + ";\n", encoding="utf-8")
    temporary.replace(output)
    print(f"地图UI数据已生成：{len(manifest['maps'])} 张地图，{len(points['points'])} 条地点记录，{len(guides)} 个摘要页 → {output}")


if __name__ == "__main__":
    main()
