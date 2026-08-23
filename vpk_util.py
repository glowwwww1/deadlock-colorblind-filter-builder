import hashlib
import os
import struct
import zlib

SIGNATURE = 0x55AA1234
EMBEDDED = 0x7FFF


def _read_cstr(f):
    out = bytearray()
    while True:
        c = f.read(1)
        if not c or c == b'\x00':
            break
        out += c
    return out.decode('utf-8', 'replace')


def list_vpk(path):
    entries = []
    with open(path, 'rb') as f:
        sig, ver = struct.unpack('<II', f.read(8))
        if sig != SIGNATURE:
            raise ValueError('not a vpk: %s' % path)
        tree_size = struct.unpack('<I', f.read(4))[0]
        if ver == 2:
            f.read(16)
        elif ver != 1:
            raise ValueError('unsupported vpk version %d' % ver)
        tree_start = f.tell()
        while True:
            ext = _read_cstr(f)
            if ext == '':
                break
            while True:
                folder = _read_cstr(f)
                if folder == '':
                    break
                while True:
                    name = _read_cstr(f)
                    if name == '':
                        break
                    crc, preload, arch, off, ln = struct.unpack('<IHHII', f.read(16))
                    struct.unpack('<H', f.read(2))
                    f.read(preload)
                    full = '%s/%s.%s' % (folder, name, ext) if folder != ' ' else '%s.%s' % (name, ext)
                    entries.append((full, arch, off, ln))
            if f.tell() - tree_start >= tree_size:
                break
    return entries


def data_section_offset(path):
    with open(path, 'rb') as f:
        sig, ver, tree_size = struct.unpack('<III', f.read(12))
    if sig != SIGNATURE:
        raise ValueError('not a vpk: %s' % path)
    header_size = 28 if ver == 2 else 12
    return header_size + tree_size


def extract(dir_vpk, wanted):
    base = dir_vpk[:-len('_dir.vpk')]
    for full, arch, off, ln in list_vpk(dir_vpk):
        if full.lower() != wanted.lower():
            continue
        if arch == EMBEDDED:
            src, off = dir_vpk, off + data_section_offset(dir_vpk)
        else:
            src = '%s_%03d.vpk' % (base, arch)
        with open(src, 'rb') as f:
            f.seek(off)
            return f.read(ln)
    raise KeyError(wanted)


def build_vpk(out_path, files):
    tree = {}
    blobs, offset = [], 0
    meta = {}
    for internal, data in sorted(files.items()):
        folder, _, filename = internal.rpartition('/')
        name, _, ext = filename.rpartition('.')
        tree.setdefault(ext, {}).setdefault(folder or ' ', []).append(name)
        meta[internal] = (offset, len(data), zlib.crc32(data) & 0xFFFFFFFF)
        blobs.append(data)
        offset += len(data)
    data_section = b''.join(blobs)

    out = bytearray()
    for ext in sorted(tree):
        out += ext.encode() + b'\x00'
        for folder in sorted(tree[ext]):
            out += folder.encode() + b'\x00'
            for name in sorted(tree[ext][folder]):
                internal = '%s/%s.%s' % (folder, name, ext) if folder != ' ' else '%s.%s' % (name, ext)
                off, ln, crc = meta[internal]
                out += name.encode() + b'\x00'
                out += struct.pack('<IHHII', crc, 0, EMBEDDED, off, ln)
                out += struct.pack('<H', 0xFFFF)
            out += b'\x00'
        out += b'\x00'
    out += b'\x00'
    tree_bytes = bytes(out)

    header = struct.pack('<IIIIIII', SIGNATURE, 2, len(tree_bytes),
                         len(data_section), 0, 48, 0)

    body = header + tree_bytes + data_section
    tree_md5 = hashlib.md5(tree_bytes).digest()
    archive_md5 = hashlib.md5(b'').digest()
    whole = hashlib.md5(body + tree_md5 + archive_md5).digest()

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(body + tree_md5 + archive_md5 + whole)
    return len(body) + 48
