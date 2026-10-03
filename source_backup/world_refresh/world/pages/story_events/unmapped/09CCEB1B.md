# 未归图脚本 0x09CCEB1B

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEB1B`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：无

```json
{
 "addr": "0x09CCEB1B",
 "sources": [
  {
   "kind": "branch",
   "where": "0x09CCEAEF"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEB1B",
   "opcode": "0x26",
   "name": "special2",
   "names": [
    "special2",
    "specialvar"
   ],
   "args": [
    {
     "width": 2,
     "value": 32781,
     "addr": "0x09CCEB1C"
    },
    {
     "width": 2,
     "value": 406,
     "addr": "0x09CCEB1E"
    }
   ],
   "raw": "260d809601",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB20",
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
     "value": 32781,
     "addr": "0x09CCEB21"
    },
    {
     "width": 2,
     "value": 0,
     "addr": "0x09CCEB23"
    }
   ],
   "raw": "210d800000",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB25",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEB26"
    },
    {
     "width": 4,
     "value": 164424509,
     "addr": "0x09CCEB27",
     "class": "script"
    }
   ],
   "raw": "07013debcc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB2B",
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
     "value": 32781,
     "addr": "0x09CCEB2C"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEB2E"
    }
   ],
   "raw": "210d800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB30",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEB31"
    },
    {
     "width": 4,
     "value": 164424503,
     "addr": "0x09CCEB32",
     "class": "script"
    }
   ],
   "raw": "070137ebcc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB36",
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
 "bytes": 28
}
```
