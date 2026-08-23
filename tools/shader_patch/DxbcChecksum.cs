using System.Buffers.Binary;

static class DxbcChecksum
{
    private static readonly int[] Shifts =
    [
        7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
        5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
        4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
        6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21,
    ];

    private static readonly uint[] Constants =
    [
        0xd76aa478, 0xe8c7b756, 0x242070db, 0xc1bdceee,
        0xf57c0faf, 0x4787c62a, 0xa8304613, 0xfd469501,
        0x698098d8, 0x8b44f7af, 0xffff5bb1, 0x895cd7be,
        0x6b901122, 0xfd987193, 0xa679438e, 0x49b40821,
        0xf61e2562, 0xc040b340, 0x265e5a51, 0xe9b6c7aa,
        0xd62f105d, 0x02441453, 0xd8a1e681, 0xe7d3fbc8,
        0x21e1cde6, 0xc33707d6, 0xf4d50d87, 0x455a14ed,
        0xa9e3e905, 0xfcefa3f8, 0x676f02d9, 0x8d2a4c8a,
        0xfffa3942, 0x8771f681, 0x6d9d6122, 0xfde5380c,
        0xa4beea44, 0x4bdecfa9, 0xf6bb4b60, 0xbebfbc70,
        0x289b7ec6, 0xeaa127fa, 0xd4ef3085, 0x04881d05,
        0xd9d4d039, 0xe6db99e5, 0x1fa27cf8, 0xc4ac5665,
        0xf4292244, 0x432aff97, 0xab9423a7, 0xfc93a039,
        0x655b59c3, 0x8f0ccc92, 0xffeff47d, 0x85845dd1,
        0x6fa87e4f, 0xfe2ce6e0, 0xa3014314, 0x4e0811a1,
        0xf7537e82, 0xbd3af235, 0x2ad7d2bb, 0xeb86d391,
    ];

    public static byte[] Compute(ReadOnlySpan<byte> dxbc)
    {
        if (dxbc.Length < 32 || !dxbc[..4].SequenceEqual("DXBC"u8))
        {
            throw new InvalidDataException("Not a DXBC container.");
        }

        var declaredSize = BinaryPrimitives.ReadInt32LittleEndian(dxbc[24..]);
        if (declaredSize != dxbc.Length)
        {
            throw new InvalidDataException(
                $"DXBC declares {declaredSize} bytes but contains {dxbc.Length}.");
        }

        var state = new uint[] { 0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476 };
        var payload = dxbc[20..];
        var fullLength = payload.Length & ~63;
        for (var offset = 0; offset < fullLength; offset += 64)
        {
            Transform(state, payload.Slice(offset, 64));
        }

        var bitCount = checked((uint)payload.Length * 8u);
        var remainder = payload[fullLength..];
        Span<byte> block = stackalloc byte[64];
        block.Clear();

        if (remainder.Length >= 56)
        {
            remainder.CopyTo(block);
            block[remainder.Length] = 0x80;
            Transform(state, block);

            block.Clear();
            BinaryPrimitives.WriteUInt32LittleEndian(block, bitCount);
            BinaryPrimitives.WriteUInt32LittleEndian(block[60..], (bitCount >> 2) | 1u);
            Transform(state, block);
        }
        else
        {
            BinaryPrimitives.WriteUInt32LittleEndian(block, bitCount);
            remainder.CopyTo(block[4..]);
            block[4 + remainder.Length] = 0x80;
            BinaryPrimitives.WriteUInt32LittleEndian(block[60..], (bitCount >> 2) | 1u);
            Transform(state, block);
        }

        var digest = new byte[16];
        for (var index = 0; index < state.Length; index++)
        {
            BinaryPrimitives.WriteUInt32LittleEndian(digest.AsSpan(index * 4), state[index]);
        }
        return digest;
    }

    private static void Transform(uint[] state, ReadOnlySpan<byte> block)
    {
        Span<uint> words = stackalloc uint[16];
        for (var index = 0; index < words.Length; index++)
        {
            words[index] = BinaryPrimitives.ReadUInt32LittleEndian(block[(index * 4)..]);
        }

        var a = state[0];
        var b = state[1];
        var c = state[2];
        var d = state[3];

        for (var index = 0; index < 64; index++)
        {
            uint function;
            int wordIndex;
            if (index < 16)
            {
                function = (b & c) | (~b & d);
                wordIndex = index;
            }
            else if (index < 32)
            {
                function = (d & b) | (~d & c);
                wordIndex = (5 * index + 1) & 15;
            }
            else if (index < 48)
            {
                function = b ^ c ^ d;
                wordIndex = (3 * index + 5) & 15;
            }
            else
            {
                function = c ^ (b | ~d);
                wordIndex = (7 * index) & 15;
            }

            var previousD = d;
            d = c;
            c = b;
            b = unchecked(b + uint.RotateLeft(
                unchecked(a + function + Constants[index] + words[wordIndex]),
                Shifts[index]));
            a = previousD;
        }

        state[0] = unchecked(state[0] + a);
        state[1] = unchecked(state[1] + b);
        state[2] = unchecked(state[2] + c);
        state[3] = unchecked(state[3] + d);
    }
}
