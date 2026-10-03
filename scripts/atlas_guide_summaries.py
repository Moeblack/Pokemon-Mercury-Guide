"""Build page-keyed atlas summaries from existing guide records only."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是字符串，实际为 {type(value).__name__}")
    return value


def _texts(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} 必须是数组，实际为 {type(value).__name__}")
    return [_text(item, field) for item in value]


def _section(title: str, texts: list[str]) -> dict[str, Any]:
    return {"title": title, "items": [{"text": text} for text in texts if text]}


def _party_text(member: dict[str, Any]) -> str:
    species = _text(member["species"], "party.species")
    level = member["level"]
    if type(level) is not int:
        raise ValueError(f"party.level 必须是整数，实际为 {type(level).__name__}")
    raw_moves = member["moves"]
    if not isinstance(raw_moves, list) or not all(isinstance(move, dict) for move in raw_moves):
        raise ValueError("party.moves 必须是对象数组")
    moves = [_text(move["name"], "party.moves.name") for move in raw_moves]
    held_item = _text(member["held_item"], "party.held_item")
    text = f"{species} Lv.{level}"
    if held_item and held_item != "无":
        text += f" 携带{held_item}"
    if moves:
        text += " 招式" + " / ".join(moves)
    return text


def build_guide_summaries(root: Path) -> dict[str, dict[str, Any]]:
    guides: dict[str, dict[str, Any]] = {}
    sources = (
        ("quests", "quests", "id", 3, "quest", "title"),
        ("items", "items", "index", 4, "item", "name"),
        ("pokemon", "records", "species_id", 4, "pokemon", "name"),
        ("trainers", "trainers", "id", 4, "trainer", "display_name"),
    )
    for directory, collection, id_field, width, kind, title_field in sources:
        records = json.loads((root / "data" / f"{directory}.json").read_text(encoding="utf-8"))[collection]
        for record in records:
            page = record.get("page") or f"{directory}/{record[id_field]:0{width}d}.md"
            page = PurePosixPath(_text(page, "page").replace("\\", "/")).with_suffix(".md")
            if page.is_absolute() or ".." in page.parts or not (root / str(page)).is_file():
                continue
            sections: list[dict[str, Any]] = []
            guide: dict[str, Any] = {
                "title": _text(record[title_field], title_field),
                "kind": kind,
                "sections": sections,
            }
            if kind == "quest":
                sections.append(_section("准备与条件", _texts(record["requirements"], "requirements")))
                steps = []
                for step in record["steps"]:
                    item = {"text": _text(step["text"], "steps.text")}
                    if "map_id" in step:
                        item["map_id"] = step["map_id"]
                    steps.append(item)
                sections.append({"title": "行动步骤", "items": steps})
                for field, title in (("rewards", "报酬"), ("pitfalls", "注意事项"), ("open_questions", "尚未整理的条件")):
                    sections.append(_section(title, _texts(record[field], field)))
                guide["status"] = record["status"]
            elif kind == "item":
                sections.append(_section("用途", [_text(record["description"], "description")]))
            elif kind == "pokemon":
                sections.append(_section("属性", [" / ".join(_texts(record["types"], "types"))]))
            else:
                party = record["party"]
                if not isinstance(party, list) or not all(isinstance(member, dict) for member in party):
                    raise ValueError("party 必须是对象数组")
                sections.append(_section("对手队伍", [_party_text(member) for member in party]))
            guide["sections"] = [section for section in sections if section["items"]]
            key = str(page)
            if key in guides:
                raise ValueError(f"攻略页面键重复：{key}")
            guides[key] = guide
    return guides
