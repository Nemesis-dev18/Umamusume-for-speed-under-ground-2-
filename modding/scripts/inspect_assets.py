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
    if path.is_symlink():
        raise ValueError('Output symlink excluded')
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--map', nargs='*', default=[])
    args = parser.parse_args()
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
