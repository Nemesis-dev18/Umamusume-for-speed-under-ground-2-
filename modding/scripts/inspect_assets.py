"""Read-only NFSU2 data inspection; only reports are written under modding/."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ('CARS', 'GLOBAL', 'NIS', 'SOUND', 'FRONTEND')
MAX_OUTPUT = 256 * 1024 * 1024


def data_path(relative):
    path = ROOT / relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Expected a relative data path')
    if not Path(relative).parts or Path(relative).parts[0] not in DATA:
        raise ValueError('Outside admitted data directories')
    for parent in (path, *path.parents):
        if parent == ROOT:
            break
        if parent.is_symlink():
            raise ValueError('Symlinks are excluded')
    if path.suffix.lower() in ('.exe', '.dll', '.asi'):
        raise ValueError('Executable/plugin excluded')
    path.resolve().relative_to(ROOT)
    return path


def save_json(relative, value):
    path = ROOT / 'modding' / relative
    for parent in (path,*path.parents):
        if parent==ROOT:break
        if parent.is_symlink():raise ValueError('Output symlink excluded')
    path.resolve().relative_to((ROOT / 'modding').resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def jdlz(data):
    if len(data) < 16 or data[:4] != b'JDLZ':
        raise ValueError('Invalid/truncated JDLZ header')
    size, compressed = struct.unpack_from('<II', data, 8)
    if size > MAX_OUTPUT or compressed < 16 or compressed > len(data):
        raise ValueError('JDLZ size out of bounds')
    if data[4:8] != b'\x02\x10\0\0':
        raise ValueError('Unsupported JDLZ version/flags')
    pos, flags1, flags2 = 16, 1, 1
    out = bytearray()
    def read():
        nonlocal pos
        if pos >= compressed:
            raise ValueError(f'Truncated JDLZ token at {pos:#x}')
        result = data[pos]
        pos += 1
        return result
    while len(out) < size:
        if flags1 == 1:
            flags1 = read() | 0x100
        if flags2 == 1:
            flags2 = read() | 0x100
        if flags1 & 1:
            a, b = read(), read()
            if flags2 & 1:
                length, distance = ((a & 0xf0) << 4 | b) + 3, (a & 15) + 1
            else:
                length, distance = (a & 31) + 3, (b | (a & 0xe0) << 3) + 17
            if distance > len(out) or length > size - len(out):
                raise ValueError('Invalid JDLZ back-reference')
            for _ in range(length):
                out.append(out[-distance])
            flags2 >>= 1
        else:
            out.append(read())
        flags1 >>= 1
    return bytes(out)


def huff(data):
    """EA order-0 Huffman, observed 0x30fb variant; no delta variants guessed."""
    if len(data)<16 or data[:8]!=b'HUFF\x01\x10\0\0':
        raise ValueError('Invalid/unsupported HUFF header')
    size, compressed=struct.unpack_from('<II',data,8)
    if size>MAX_OUTPUT or compressed>len(data)-16:
        raise ValueError('HUFF length out of bounds')
    stream=memoryview(data)[16:16+compressed];bit=0
    def read(count):
        nonlocal bit
        if bit+count>len(stream)*8: raise ValueError('Truncated HUFF bitstream')
        value=0
        for _ in range(count):
            value=(value<<1)|((stream[bit//8]>>(7-bit%8))&1);bit+=1
        return value
    def number():
        if read(1):return read(2)
        n=3
        while not read(1):
            n+=1
            if n>32:raise ValueError('Unterminated HUFF integer')
        value=read(n)+(1<<n)-4
        return value if value<2**31 else value-2**32
    kind=read(16)
    if kind!=0x30fb:raise ValueError(f'Unsupported HUFF stream type {kind:#x}')
    declared=(read(8)<<16)|read(16);clue=read(8)
    if declared!=size:raise ValueError('HUFF inner/outer length mismatch')
    counts=[];base=0;total=0
    for length in range(1,33):
        count=number()
        if not 0<=count<=256:raise ValueError('Invalid HUFF code count')
        base=base*2+count;total+=count;counts.append(count)
        if total>256 or base>1<<length:raise ValueError('Oversubscribed HUFF table')
        if base==1<<length:break
    else:raise ValueError('Incomplete HUFF table')
    symbols=[];used=set();current=255
    for _ in range(total):
        leap=number()+1
        if not 1<=leap<=256-len(used):raise ValueError('Invalid HUFF symbol leap')
        while leap:
            current=(current+1)&255
            if current not in used:leap-=1
        used.add(current);symbols.append(current)
    out=bytearray()
    while len(out)<size:
        code=0;base=0;index=0
        for count in counts:
            code=(code<<1)|read(1)
            if base<=code<base+count:
                symbol=symbols[index+code-base];break
            index+=count;base=(base+count)*2
        else:raise ValueError('Unknown HUFF code')
        if symbol!=clue:out.append(symbol);continue
        length=number()
        if length:
            if length<0 or not out or length>size-len(out):raise ValueError('Invalid HUFF run')
            out.extend(bytes([out[-1]])*length)
        elif read(1):raise ValueError('HUFF premature end')
        else:out.append(read(8))
    return bytes(out)


def chunks(data, start=0, end=None, depth=0):
    end = len(data) if end is None else end
    if depth > 32 or not 0 <= start <= end <= len(data):
        raise ValueError('Chunk nesting/range invalid')
    nodes = []
    while start < end:
        if end - start < 8:
            if any(data[start:end]):
                raise ValueError(f'Truncated chunk header at {start:#x}')
            break
        tag, size = struct.unpack_from('<II', data, start)
        stop = start + 8 + size
        if stop > end:
            raise ValueError(f'Chunk {tag:#x} at {start:#x} exceeds parent {end:#x}')
        node = {'id': f'0x{tag:08x}', 'offset': start, 'payload': start + 8,
                'size': size, 'end': stop, 'offset_mod16': start % 16,
                'payload_mod128': (start + 8) % 128}
        if tag & 0x80000000:
            node['children'] = chunks(data, start + 8, stop, depth + 1)
        nodes.append(node)
        start = stop
    return nodes


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.get('children', []))


def inventory():
    result = []
    for folder in DATA:
        for path in sorted((ROOT / folder).rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            try:
                data_path(relative)
            except ValueError:
                continue
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                head = stream.read(16)
                digest.update(head)
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            name = path.name.upper()
            role = ('geometry' if name == 'GEOMETRY.BIN' else
                    'texture_candidate' if name == 'TEXTURES.BIN' or path.suffix.lower() == '.fsh' else
                    'vehicle_parameters_candidate' if name in ('GLOBALB.BUN', 'GLOBALB.LZC') else
                    'audio_candidate' if folder == 'SOUND' else
                    'cinematic_or_animation_candidate' if folder == 'NIS' else 'unclassified')
            result.append({'path': str(relative), 'bytes': path.stat().st_size,
                           'sha256': digest.hexdigest(), 'header16': head.hex(),
                           'first_u32_le': f'0x{int.from_bytes(head[:4], "little"):08x}' if len(head) >= 4 else None,
                           'role_from_name_only': role})
    return result


def cartypes(data):
    import re
    import math
    records=[]
    for match in re.finditer(rb'CARS[\\/][A-Z0-9_]+[\\/]GEOMETRY\.BIN',data):
        begin=match.start()-0x40
        if begin<0 or begin+0x890>len(data):continue
        name=data[begin:begin+16].split(b'\0')[0]
        duplicate=data[begin+0x20:begin+0x30].split(b'\0')[0]
        if not name or name!=duplicate or not re.fullmatch(rb'[A-Z0-9_]+',name):continue
        wheels=[]
        for index in range(4):
            at=begin+0x120+index*0x30
            values=[struct.unpack_from('<f',data,at+off)[0] for off in (0,8,16,0x1c)]
            if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite wheel data')
            wheels.append(dict(zip(('longitudinal','height','radius','lateral'),values)))
        mass=struct.unpack_from('<f',data,begin+0x220)[0]
        if not math.isfinite(mass):raise ValueError('Nonfinite mass')
        records.append({'name':name.decode(),'offset':begin,'record_bytes':0x890,
                        'mass_stored':mass,'wheels':wheels,'interpretation':'Candidate units from NFSU2 format reference; no physics edits'})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--cartypes', action='store_true')
    parser.add_argument('--map', nargs='*', default=[])
    args = parser.parse_args()
    if args.cartypes:
        records=cartypes(data_path('GLOBAL/GLOBALB.BUN').read_bytes())
        save_json('cartypes.json',records)
        print(f'Located {len(records)} validated-name CarTypeInfo candidates')
    if args.inventory:
        records = inventory()
        save_json('inventory.json', records)
        print(f'Inventoried {len(records)} data files')
    if args.map:
        reports = []
        for relative in args.map:
            data = data_path(relative).read_bytes()
            report = {'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'coordinate_space': 'file'}
            if data.startswith(b'JDLZ'):
                data = jdlz(data)
                report['coordinate_space'] = 'decompressed memory'
                report['decompressed_bytes'] = len(data)
                report['decompressed_sha256'] = hashlib.sha256(data).hexdigest()
            try:
                report['chunks'] = chunks(data)
            except ValueError as error:
                report['unresolved'] = str(error)
            reports.append(report)
        save_json('containers.json', reports)
        print(f'Mapped {len(reports)} files; unknown layouts reported explicitly')


if __name__ == '__main__':
    main()
