"""Presentation-only TM/HM names; do not rewrite URLs or raw code spans."""
import json
import re


class TMNames:
    def __init__(self, root):
        rows = json.loads((root / 'data/tm_names.json').read_text(encoding='utf-8'))['items']
        self.by_item = {row['item_index']: row for row in rows}
        self.aliases = {}
        for row in rows:
            for alias in (row['label'], row['raw_name']):
                self.aliases[alias] = row
        alternatives = '|'.join(re.escape(alias) for alias in sorted(self.aliases, key=len, reverse=True))
        self.pattern = re.compile(r'(?<![A-Za-z0-9_])(?:' + alternatives + r')(?![A-Za-z0-9_])')
        self.protected = re.compile(r'(```[\s\S]*?```|`[^`]*`|\]\([^)]*\)|<[^>]*>)')

    def plain(self, text):
        def replace(match):
            row = self.aliases[match[0]]
            # Idempotent when a source already contains the corresponding move.
            following = text[match.end():]
            if re.match(r'[ \t·:：、（(]*' + re.escape(row['move_name']), following):
                return match[0]
            return row['display_name']
        return self.pattern.sub(replace, text)

    def markdown(self, text):
        parts = self.protected.split(text)
        return ''.join(part if i % 2 else self.plain(part) for i, part in enumerate(parts))

    def guide(self, value):
        if isinstance(value, list):
            return [self.guide(item) for item in value]
        if isinstance(value, dict):
            return {key: self.plain(item) if key in {'title', 'text'} and isinstance(item, str) else self.guide(item) for key, item in value.items()}
        return value

    def search_aliases(self, index):
        row = self.by_item.get(index)
        return ' '.join([row['raw_name'], row['label']]) if row else ''
