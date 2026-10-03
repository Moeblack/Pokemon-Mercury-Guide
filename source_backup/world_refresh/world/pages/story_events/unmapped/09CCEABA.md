# 未归图脚本 0x09CCEABA

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEABA`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：[0x09D9A47B](../../texts/09D9A47B.md)

```json
{
 "addr": "0x09CCEABA",
 "sources": [
  {
   "kind": "branch",
   "where": "0x09CCEAA9"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEABA",
   "opcode": "0x83",
   "name": "buffernumber",
   "names": [
    "buffernumber",
    "getnumberstring"
   ],
   "args": [
    {
     "width": 1,
     "value": 0,
     "addr": "0x09CCEABB"
    },
    {
     "width": 2,
     "value": 32773,
     "addr": "0x09CCEABC"
    }
   ],
   "raw": "83000580",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEABE",
   "opcode": "0x23",
   "name": "callasm",
   "names": [
    "callasm",
    "callnative"
   ],
   "args": [
    {
     "width": 4,
     "value": 164994521,
     "addr": "0x09CCEABF",
     "class": "raw"
    }
   ],
   "raw": "23d99dd509",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAC3",
   "opcode": "0x67",
   "name": "preparemsg",
   "names": [
    "preparemsg",
    "message"
   ],
   "args": [
    {
     "width": 4,
     "value": 165258363,
     "addr": "0x09CCEAC4",
     "class": "text"
    }
   ],
   "raw": "677ba4d909",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAC8",
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
 "bytes": 15
}
```
