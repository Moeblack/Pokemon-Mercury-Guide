# 未归图脚本 0x09CCEB3D

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEB3D`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：[0x081A51F6](../../texts/081A51F6.md)

```json
{
 "addr": "0x09CCEB3D",
 "sources": [
  {
   "kind": "branch",
   "where": "0x09CCEB1B"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEB3D",
   "opcode": "0x67",
   "name": "preparemsg",
   "names": [
    "preparemsg",
    "message"
   ],
   "args": [
    {
     "width": 4,
     "value": 135942646,
     "addr": "0x09CCEB3E",
     "class": "text"
    }
   ],
   "raw": "67f6511a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB42",
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
 "bytes": 6
}
```
