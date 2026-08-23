def lz4_decompress(src, max_out=1 << 26):
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]; i += 1
        lit = token >> 4
        if lit == 15:
            while i < n:
                b = src[i]; i += 1
                lit += b
                if b != 255:
                    break
        if i + lit > n:
            out += src[i:n]
            break
        out += src[i:i + lit]
        i += lit
        if i + 2 > n:
            break
        offset = src[i] | (src[i + 1] << 8)
        i += 2
        if offset == 0:
            break
        mlen = (token & 0x0F)
        if mlen == 15:
            while i < n:
                b = src[i]; i += 1
                mlen += b
                if b != 255:
                    break
        mlen += 4
        start = len(out) - offset
        if start < 0:
            break
        for k in range(mlen):
            out.append(out[start + k])
        if len(out) > max_out:
            break
    return bytes(out)
