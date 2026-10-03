# 未归图脚本 0x09CCEAA9

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEAA9`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：[0x081A5231](../../texts/081A5231.md)

```json
{
 "addr": "0x09CCEAA9",
 "sources": [
  {
   "kind": "branch",
   "where": "0x09CCEA6B"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEAA9",
   "opcode": "0x21",
   "name": "comparevartovalue",
   "names": [
    "comparevartovalue",
    "compare",
    "case"
   ],
   "args": [
    {
     "width": 2,
     "value": 32773,
     "addr": "0x09CCEAAA"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEAAC"
    }
   ],
   "raw": "2105800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAAE",
   "opcode": "0x06",
   "name": "goto_if",
   "names": [
    "goto_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 2,
     "addr": "0x09CCEAAF"
    },
    {
     "width": 4,
     "value": 164424378,
     "addr": "0x09CCEAB0",
     "class": "script"
    }
   ],
   "raw": "0602baeacc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAB4",
   "opcode": "0x67",
   "name": "preparemsg",
   "names": [
    "preparemsg",
    "message"
   ],
   "args": [
    {
     "width": 4,
     "value": 135942705,
     "addr": "0x09CCEAB5",
     "class": "text"
    }
   ],
   "raw": "6731521a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAB9",
   "opcode": "0x03",
   "name": "return",
   "names": [
    "return"
   ],
   "args": [],
   "raw": "03",
   "layout_source": "macro"
  }
 ],
 "unknown_at": null,
 "bytes": 17
}
```
