# 未归图脚本 0x09CCEAEF

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEAEF`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：[0x081A5218](../../texts/081A5218.md)

```json
{
 "addr": "0x09CCEAEF",
 "sources": [
  {
   "kind": "branch",
   "where": "0x081A6697"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEAEF",
   "opcode": "0x25",
   "name": "special",
   "names": [
    "special"
   ],
   "args": [
    {
     "width": 2,
     "value": 228,
     "addr": "0x09CCEAF0"
    }
   ],
   "raw": "25e400",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAF2",
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
     "addr": "0x09CCEAF3"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEAF5"
    }
   ],
   "raw": "2105800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAF7",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 3,
     "addr": "0x09CCEAF8"
    },
    {
     "width": 4,
     "value": 164424475,
     "addr": "0x09CCEAF9",
     "class": "script"
    }
   ],
   "raw": "07031bebcc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAFD",
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
     "addr": "0x09CCEAFE"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEB00"
    }
   ],
   "raw": "2105800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB02",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 2,
     "addr": "0x09CCEB03"
    },
    {
     "width": 4,
     "value": 164424515,
     "addr": "0x09CCEB04",
     "class": "script"
    }
   ],
   "raw": "070243ebcc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB08",
   "opcode": "0x32",
   "name": "waitfanfare",
   "names": [
    "waitfanfare"
   ],
   "args": [],
   "raw": "32",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB09",
   "opcode": "0x66",
   "name": "waitmsg",
   "names": [
    "waitmsg",
    "waitmessage"
   ],
   "args": [],
   "raw": "66",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB0A",
   "opcode": "0x0F",
   "name": "loadpointer",
   "names": [
    "loadpointer",
    "loadword",
    "msgbox"
   ],
   "args": [
    {
     "width": 1,
     "value": 0,
     "addr": "0x09CCEB0B"
    },
    {
     "width": 4,
     "value": 135942680,
     "addr": "0x09CCEB0C",
     "class": "text"
    }
   ],
   "raw": "0f0018521a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB10",
   "opcode": "0x09",
   "name": "callstd",
   "names": [
    "callstd"
   ],
   "args": [
    {
     "width": 1,
     "value": 4,
     "addr": "0x09CCEB11"
    }
   ],
   "raw": "0904",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB12",
   "opcode": "0x16",
   "name": "setvar",
   "names": [
    "setvar",
    "multichoiceoption",
    "candodailyevent",
    "setdailyevent"
   ],
   "args": [
    {
     "width": 2,
     "value": 32781,
     "addr": "0x09CCEB13"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEB15"
    }
   ],
   "raw": "160d800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB17",
   "opcode": "0x25",
   "name": "special",
   "names": [
    "special"
   ],
   "args": [
    {
     "width": 2,
     "value": 229,
     "addr": "0x09CCEB18"
    }
   ],
   "raw": "25e500",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEB1A",
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
 "bytes": 44
}
```
