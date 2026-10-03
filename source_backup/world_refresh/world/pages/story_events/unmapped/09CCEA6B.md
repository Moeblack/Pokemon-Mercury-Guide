# 未归图脚本 0x09CCEA6B

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEA6B`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：[0x081A5218](../../texts/081A5218.md)

```json
{
 "addr": "0x09CCEA6B",
 "sources": [
  {
   "kind": "branch",
   "where": "0x09CCEA2C"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEA6B",
   "opcode": "0xC7",
   "name": "textcolor",
   "names": [
    "textcolor"
   ],
   "args": [
    {
     "width": 1,
     "value": 3,
     "addr": "0x09CCEA6C"
    }
   ],
   "raw": "c703",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA6D",
   "opcode": "0x53",
   "name": "removeobject",
   "names": [
    "removeobject",
    "hidesprite",
    "hidespriteonmap"
   ],
   "args": [
    {
     "width": 2,
     "value": 32783,
     "addr": "0x09CCEA6E"
    }
   ],
   "raw": "530f80",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA70",
   "opcode": "0x28",
   "name": "pause",
   "names": [
    "pause"
   ],
   "args": [
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEA71"
    }
   ],
   "raw": "280100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA73",
   "opcode": "0x25",
   "name": "special",
   "names": [
    "special"
   ],
   "args": [
    {
     "width": 2,
     "value": 228,
     "addr": "0x09CCEA74"
    }
   ],
   "raw": "25e400",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA76",
   "opcode": "0x44",
   "name": "additem",
   "names": [
    "additem"
   ],
   "args": [
    {
     "width": 2,
     "value": 32772,
     "addr": "0x09CCEA77"
    },
    {
     "width": 2,
     "value": 32773,
     "addr": "0x09CCEA79"
    }
   ],
   "raw": "4404800580",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA7B",
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
     "addr": "0x09CCEA7C"
    },
    {
     "width": 2,
     "value": 406,
     "addr": "0x09CCEA7E"
    }
   ],
   "raw": "260d809601",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA80",
   "opcode": "0x19",
   "name": "copyvar",
   "names": [
    "copyvar",
    "switch"
   ],
   "args": [
    {
     "width": 2,
     "value": 32776,
     "addr": "0x09CCEA81"
    },
    {
     "width": 2,
     "value": 32781,
     "addr": "0x09CCEA83"
    }
   ],
   "raw": "1908800d80",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA85",
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
     "value": 32776,
     "addr": "0x09CCEA86"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEA88"
    }
   ],
   "raw": "2108800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA8A",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEA8B"
    },
    {
     "width": 4,
     "value": 135948321,
     "addr": "0x09CCEA8C",
     "class": "script"
    }
   ],
   "raw": "070121681a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA90",
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
     "value": 32776,
     "addr": "0x09CCEA91"
    },
    {
     "width": 2,
     "value": 0,
     "addr": "0x09CCEA93"
    }
   ],
   "raw": "2108800000",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA95",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEA96"
    },
    {
     "width": 4,
     "value": 164424361,
     "addr": "0x09CCEA97",
     "class": "script"
    }
   ],
   "raw": "0701a9eacc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA9B",
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
   "addr": "0x09CCEA9C",
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
   "addr": "0x09CCEA9D",
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
     "addr": "0x09CCEA9E"
    },
    {
     "width": 4,
     "value": 135942680,
     "addr": "0x09CCEA9F",
     "class": "text"
    }
   ],
   "raw": "0f0018521a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAA3",
   "opcode": "0x09",
   "name": "callstd",
   "names": [
    "callstd"
   ],
   "args": [
    {
     "width": 1,
     "value": 4,
     "addr": "0x09CCEAA4"
    }
   ],
   "raw": "0904",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAA5",
   "opcode": "0x25",
   "name": "special",
   "names": [
    "special"
   ],
   "args": [
    {
     "width": 2,
     "value": 229,
     "addr": "0x09CCEAA6"
    }
   ],
   "raw": "25e500",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEAA8",
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
 "bytes": 62
}
```
