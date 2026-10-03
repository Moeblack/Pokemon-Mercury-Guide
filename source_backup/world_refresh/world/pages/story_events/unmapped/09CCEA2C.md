# 未归图脚本 0x09CCEA2C

来源：`maps_research/out/scripts/scripts.json`，JSON pointer `/scripts/0x09CCEA2C`。

没有从现成branch来源归图，不强行分配地图；解码本身不证明来源可信。

文字：无

```json
{
 "addr": "0x09CCEA2C",
 "sources": [
  {
   "kind": "std_script",
   "where": "gStdScripts[1]"
  }
 ],
 "instructions": [
  {
   "addr": "0x09CCEA2C",
   "opcode": "0x6A",
   "name": "lock",
   "names": [
    "lock"
   ],
   "args": [],
   "raw": "6a",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA2D",
   "opcode": "0x28",
   "name": "pause",
   "names": [
    "pause"
   ],
   "args": [
    {
     "width": 2,
     "value": 16,
     "addr": "0x09CCEA2E"
    }
   ],
   "raw": "281000",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA30",
   "opcode": "0x25",
   "name": "special",
   "names": [
    "special"
   ],
   "args": [
    {
     "width": 2,
     "value": 154,
     "addr": "0x09CCEA31"
    }
   ],
   "raw": "259a00",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA33",
   "opcode": "0x19",
   "name": "copyvar",
   "names": [
    "copyvar",
    "switch"
   ],
   "args": [
    {
     "width": 2,
     "value": 32772,
     "addr": "0x09CCEA34"
    },
    {
     "width": 2,
     "value": 32768,
     "addr": "0x09CCEA36"
    }
   ],
   "raw": "1904800080",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA38",
   "opcode": "0x19",
   "name": "copyvar",
   "names": [
    "copyvar",
    "switch"
   ],
   "args": [
    {
     "width": 2,
     "value": 32773,
     "addr": "0x09CCEA39"
    },
    {
     "width": 2,
     "value": 32769,
     "addr": "0x09CCEA3B"
    }
   ],
   "raw": "1905800180",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA3D",
   "opcode": "0x46",
   "name": "checkitemspace",
   "names": [
    "checkitemspace"
   ],
   "args": [
    {
     "width": 2,
     "value": 32768,
     "addr": "0x09CCEA3E"
    },
    {
     "width": 2,
     "value": 32769,
     "addr": "0x09CCEA40"
    }
   ],
   "raw": "4600800180",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA42",
   "opcode": "0x19",
   "name": "copyvar",
   "names": [
    "copyvar",
    "switch"
   ],
   "args": [
    {
     "width": 2,
     "value": 32775,
     "addr": "0x09CCEA43"
    },
    {
     "width": 2,
     "value": 32781,
     "addr": "0x09CCEA45"
    }
   ],
   "raw": "1907800d80",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA47",
   "opcode": "0x80",
   "name": "bufferitem",
   "names": [
    "bufferitem",
    "getitemname"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEA48"
    },
    {
     "width": 2,
     "value": 32768,
     "addr": "0x09CCEA49"
    }
   ],
   "raw": "80010080",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA4B",
   "opcode": "0x48",
   "name": "checkitemtype",
   "names": [
    "checkitemtype"
   ],
   "args": [
    {
     "width": 2,
     "value": 32768,
     "addr": "0x09CCEA4C"
    }
   ],
   "raw": "480080",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA4E",
   "opcode": "0x04",
   "name": "call",
   "names": [
    "call"
   ],
   "args": [
    {
     "width": 4,
     "value": 135947964,
     "addr": "0x09CCEA4F",
     "class": "script"
    }
   ],
   "raw": "04bc661a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA53",
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
     "value": 32775,
     "addr": "0x09CCEA54"
    },
    {
     "width": 2,
     "value": 1,
     "addr": "0x09CCEA56"
    }
   ],
   "raw": "2107800100",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA58",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEA59"
    },
    {
     "width": 4,
     "value": 164424299,
     "addr": "0x09CCEA5A",
     "class": "script"
    }
   ],
   "raw": "07016beacc09",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA5E",
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
     "value": 32775,
     "addr": "0x09CCEA5F"
    },
    {
     "width": 2,
     "value": 0,
     "addr": "0x09CCEA61"
    }
   ],
   "raw": "2107800000",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA63",
   "opcode": "0x07",
   "name": "call_if",
   "names": [
    "call_if"
   ],
   "args": [
    {
     "width": 1,
     "value": 1,
     "addr": "0x09CCEA64"
    },
    {
     "width": 4,
     "value": 135948333,
     "addr": "0x09CCEA65",
     "class": "script"
    }
   ],
   "raw": "07012d681a08",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA69",
   "opcode": "0x6C",
   "name": "release",
   "names": [
    "release"
   ],
   "args": [],
   "raw": "6c",
   "layout_source": "macro"
  },
  {
   "addr": "0x09CCEA6A",
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
 "bytes": 63
}
```
