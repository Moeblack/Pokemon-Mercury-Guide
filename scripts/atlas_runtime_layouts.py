"""Resolve default map layouts through Mercury's live GetMapLayout table."""
import struct

BASE = 0x08000000


def resolve_layouts(rom, headers):
    # Actual Mercury Thumb at 08055170; literal at 08055194 is relocated.
    expected = bytes.fromhex('0348013989000918086802bc0847')
    if rom[0x55184:0x55192] != expected:
        raise ValueError('GetMapLayout selector changed; re-derive its table consumer')
    table = struct.unpack_from('<I', rom, 0x55194)[0]

    def unpack(fmt, address):
        offset = address - BASE
        size = struct.calcsize(fmt)
        if offset < 0 or offset + size > len(rom):
            raise ValueError(f'Layout ROM range invalid: {address:08X}')
        return struct.unpack_from(fmt, rom, offset)

    def hexaddr(value):
        return f'0x{value:08X}'

    layouts, records = {}, {}
    for header in headers:
        mid = f"{header['group']}:{header['num']}"
        layout_id = unpack('<H', int(header['header_addr'], 0) + 0x12)[0]
        if layout_id != header['map_layout_id'] or not layout_id:
            raise ValueError(f'{mid}: layout ID absent or extracted header stale')
        selected = unpack('<I', table + (layout_id - 1) * 4)[0]
        width, height, border, cells, primary, secondary, bw, bh = unpack('<iiIIIIBB', selected)
        if width <= 0 or height <= 0 or width * height > len(rom) // 2:
            raise ValueError(f'{mid}: invalid selected layout dimensions')
        unpack(f'<{width * height}H', cells)
        layouts[mid] = dict(address=hexaddr(selected), width=width, height=height,
                            border=hexaddr(border), map=hexaddr(cells),
                            primary_tileset=hexaddr(primary), secondary_tileset=hexaddr(secondary),
                            border_width=bw, border_height=bh)
        records[mid] = dict(layout_id=layout_id, header_layout=header['map_layout_addr'],
                            selected_layout=hexaddr(selected),
                            changed=selected != int(header['map_layout_addr'], 0))
    return layouts, dict(table=hexaddr(table), selector='0x08055170',
                        load_consumer='0x08055274', scope='default map entry; not save-dependent setmaplayout variants',
                        changed_count=sum(r['changed'] for r in records.values()), maps=records)
