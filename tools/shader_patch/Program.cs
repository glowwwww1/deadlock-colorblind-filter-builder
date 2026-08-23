using System.Globalization;
using System.Reflection;
using System.Security.Cryptography;
using ValveResourceFormat;
using ValveResourceFormat.CompiledShader;
using ZstdSharp;
using ZstdSharp.Unsafe;

const int OutlinePhase = 2;
const int NegativeScaleOffset = 0x2B4;
const int PositiveScaleOffset = 0x2BC;
const int ExternalHeaderSize = 12;
const int ZstdDictionaryType = -3;

try
{
if (args.Length == 2 && args[1] == "--inspect")
{
    var inspectedScale = ReadWidthScale(Path.GetFullPath(args[0]));
    Console.WriteLine($"outline distance scale: {inspectedScale:F6}x");
    return 0;
}

if (args.Length != 3
    || !float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture,
        out var widthScale)
    || !float.IsFinite(widthScale)
    || widthScale <= 0.0f)
{
    Console.Error.WriteLine(
        "Usage: ShaderPatch <input generate_outlines_pc_50_ps.vcs> "
        + "<output.vcs> <width-scale>");
    return 2;
}

var inputPath = Path.GetFullPath(args[0]);
var outputPath = Path.GetFullPath(args[1]);
if (string.Equals(inputPath, outputPath, StringComparison.OrdinalIgnoreCase))
{
    throw new ArgumentException("Input and output paths must differ.");
}

var originalBytes = File.ReadAllBytes(inputPath);
if (originalBytes.Length < ExternalHeaderSize + 4)
{
    throw new InvalidDataException("Shader resource is truncated.");
}
var resourceSize = checked((int)BitConverter.ToUInt32(originalBytes, 0));
if (resourceSize < 4 || resourceSize + ExternalHeaderSize > originalBytes.Length)
{
    throw new InvalidDataException("Shader resource size is invalid.");
}
if (BitConverter.ToInt32(originalBytes, resourceSize) != ZstdDictionaryType)
{
    throw new InvalidDataException("Expected Valve shader Zstd dictionary type 3.");
}
var originalRawSize = BitConverter.ToInt32(originalBytes, resourceSize + 4);
var originalCompressedSize = BitConverter.ToInt32(originalBytes, resourceSize + 8);
if (originalCompressedSize <= 0
    || resourceSize + ExternalHeaderSize + originalCompressedSize != originalBytes.Length)
{
    throw new InvalidDataException("Shader external bytecode size is invalid.");
}

int dataOffset;
int dataSize;
using (var resource = new Resource())
{
    resource.Read(inputPath);
    var dataBlock = resource.DataBlock
        ?? throw new InvalidDataException("Shader resource has no DATA block.");
    dataOffset = checked((int)dataBlock.Offset);
    dataSize = checked((int)dataBlock.Size);
}

var phaseBytecodes = ReadAndPatchPhases(
    inputPath, widthScale, out var originalPhaseHash);
var uncompressedBytecode = phaseBytecodes.SelectMany(bytes => bytes).ToArray();
if (uncompressedBytecode.Length != originalRawSize)
{
    throw new InvalidDataException(
        "Width patch unexpectedly changed the uncompressed shader size.");
}
var dictionary = GetValveShaderDictionary();
var (compressedBytecode, compressionLevel) = CompressBytecode(
    uncompressedBytecode, dictionary, originalCompressedSize);
var serializedWidthScale = widthScale;
if (compressedBytecode.Length != originalCompressedSize
    && Environment.GetEnvironmentVariable("SHADER_PATCH_FIT_SIZE") == "1")
{
    (compressedBytecode, compressionLevel, serializedWidthScale) =
        FitWidthScaleToOriginalCompressedSize(
            phaseBytecodes, widthScale, dictionary, originalCompressedSize);
}
var replacementPhaseHash = MD5.HashData(phaseBytecodes[OutlinePhase]);

var outputBytes = new byte[resourceSize + ExternalHeaderSize + compressedBytecode.Length];
originalBytes.AsSpan(0, resourceSize).CopyTo(outputBytes);
var metadataCompressionLevel = PatchHashInMetadataFrame(
    outputBytes, dataOffset, dataSize, originalPhaseHash, replacementPhaseHash);
var sizeCompressionLevel = PatchBytecodeSizeInMetadataBuffer(
    outputBytes,
    dataOffset,
    ExternalHeaderSize + originalCompressedSize,
    ExternalHeaderSize + compressedBytecode.Length);
BitConverter.GetBytes(ZstdDictionaryType).CopyTo(outputBytes, resourceSize);
BitConverter.GetBytes(originalRawSize).CopyTo(outputBytes, resourceSize + 4);
BitConverter.GetBytes(compressedBytecode.Length).CopyTo(outputBytes, resourceSize + 8);
compressedBytecode.CopyTo(outputBytes, resourceSize + ExternalHeaderSize);

Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
File.WriteAllBytes(outputPath, outputBytes);
VerifyOutput(outputPath, serializedWidthScale, replacementPhaseHash);

Console.WriteLine(
    $"outline distance scale: 1.00x -> {serializedWidthScale:F6}x; "
    + $"typed metadata preserved; zstd levels "
    + $"{metadataCompressionLevel}/{sizeCompressionLevel}/{compressionLevel}; "
    + $"wrote {outputPath} ({outputBytes.Length} bytes)");
return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"ShaderPatch failed: {exception.Message}");
    return 1;
}

static List<byte[]> ReadAndPatchPhases(
    string inputPath, float widthScale, out byte[] originalPhaseHash)
{
    using var program = new VfxProgramData();
    program.Read(inputPath);
    if (program.StaticComboEntries.Count != 1)
    {
        throw new InvalidDataException(
            $"Expected one static shader combo, got {program.StaticComboEntries.Count}.");
    }

    var combo = program.GetStaticCombo(program.StaticComboEntries.Single().Key);
    if (combo.ShaderFiles.Length != 6 || combo.ShaderFiles[OutlinePhase] is null)
    {
        throw new InvalidDataException("Expected six generate_outlines shader phases.");
    }

    var phases = new List<byte[]>(combo.ShaderFiles.Length);
    for (var index = 0; index < combo.ShaderFiles.Length; index++)
    {
        var shader = combo.ShaderFiles[index]
            ?? throw new InvalidDataException($"Shader phase {index} is missing.");
        var declaredSize = BitConverter.ToInt32(shader.Bytecode, 24);
        if (declaredSize < 32 || declaredSize > shader.Bytecode.Length)
        {
            throw new InvalidDataException(
                $"Invalid DXBC size {declaredSize} for phase {index}.");
        }

        var bytecode = shader.Bytecode.AsSpan(0, declaredSize).ToArray();
        VerifyDxbcChecksum(bytecode, $"input phase {index}");
        phases.Add(bytecode);
    }

    var outline = phases[OutlinePhase];
    originalPhaseHash = MD5.HashData(outline);
    if (BitConverter.ToSingle(outline, NegativeScaleOffset) != -1.0f
        || BitConverter.ToSingle(outline, PositiveScaleOffset) != 1.0f)
    {
        throw new InvalidDataException(
            "Could not identify the phase-2 signed-distance scale. "
            + "The game shader may have changed.");
    }

    BitConverter.GetBytes(-1.0f / widthScale).CopyTo(outline, NegativeScaleOffset);
    BitConverter.GetBytes(1.0f / widthScale).CopyTo(outline, PositiveScaleOffset);
    DxbcChecksum.Compute(outline).CopyTo(outline, 4);
    VerifyDxbcChecksum(outline, "patched phase 2");
    return phases;
}

static float ReadWidthScale(string inputPath)
{
    using var program = new VfxProgramData();
    program.Read(inputPath);
    if (program.StaticComboEntries.Count != 1)
    {
        throw new InvalidDataException(
            $"Expected one static shader combo, got {program.StaticComboEntries.Count}.");
    }

    var combo = program.GetStaticCombo(program.StaticComboEntries.Single().Key);
    var shader = combo.ShaderFiles[OutlinePhase]
        ?? throw new InvalidDataException("Outline shader phase 2 is missing.");
    var size = BitConverter.ToInt32(shader.Bytecode, 24);
    var bytecode = shader.Bytecode.AsSpan(0, size).ToArray();
    VerifyDxbcChecksum(bytecode, "inspected phase 2");
    var negative = BitConverter.ToSingle(bytecode, NegativeScaleOffset);
    var positive = BitConverter.ToSingle(bytecode, PositiveScaleOffset);
    if (positive <= 0.0f || negative != -positive)
    {
        throw new InvalidDataException(
            $"Unexpected signed-distance constants {negative:R}/{positive:R}.");
    }
    return 1.0f / positive;
}

static (byte[] Bytes, int Level, float WidthScale)
    FitWidthScaleToOriginalCompressedSize(
        List<byte[]> phases,
        float requestedWidthScale,
        byte[] dictionary,
        int preferredSize)
{
    var outline = phases[OutlinePhase];
    var exactPositive = 1.0f / requestedWidthScale;
    var exactBits = BitConverter.SingleToInt32Bits(exactPositive);
    const int MaxUlpAdjustment = 1024;

    for (var level = 14; level <= 22; level++)
    {
        var smallest = int.MaxValue;
        var largest = 0;
        using var compressor = new Compressor(level);
        compressor.LoadDictionary(dictionary);
        compressor.SetParameter(ZSTD_cParameter.ZSTD_c_contentSizeFlag, 0);
        compressor.SetParameter(ZSTD_cParameter.ZSTD_c_dictIDFlag, 0);
        for (var delta = 1; delta <= MaxUlpAdjustment; delta++)
        {
            foreach (var signedDelta in new[] { -delta, delta })
            {
                var positive = BitConverter.Int32BitsToSingle(exactBits + signedDelta);
                BitConverter.GetBytes(-positive).CopyTo(outline, NegativeScaleOffset);
                BitConverter.GetBytes(positive).CopyTo(outline, PositiveScaleOffset);
                DxbcChecksum.Compute(outline).CopyTo(outline, 4);
                var input = phases.SelectMany(bytes => bytes).ToArray();
                var candidate = compressor.Wrap(input).ToArray();
                smallest = Math.Min(smallest, candidate.Length);
                largest = Math.Max(largest, candidate.Length);
                if (candidate.Length == preferredSize)
                {
                    return (candidate, level, 1.0f / positive);
                }
            }
        }
        if (Environment.GetEnvironmentVariable("SHADER_PATCH_DIAGNOSTICS") == "1")
        {
            Console.WriteLine(
                $"scale-fit zstd level {level}: {smallest}-{largest} bytes");
        }
    }

    BitConverter.GetBytes(-exactPositive).CopyTo(outline, NegativeScaleOffset);
    BitConverter.GetBytes(exactPositive).CopyTo(outline, PositiveScaleOffset);
    DxbcChecksum.Compute(outline).CopyTo(outline, 4);
    throw new InvalidDataException(
        "Could not fit the requested outline scale into the original "
        + "static-combo bytecode size.");
}

static (byte[] Bytes, int Level) CompressBytecode(
    byte[] input, byte[] dictionary, int preferredSize)
{
    byte[]? fallback = null;
    for (var level = 1; level <= 22; level++)
    {
        using var compressor = new Compressor(level);
        compressor.LoadDictionary(dictionary);
        var candidate = compressor.Wrap(input).ToArray();
        if (level == 19)
        {
            fallback = candidate;
        }
        if (candidate.Length == preferredSize)
        {
            return (candidate, level);
        }
    }
    return (fallback ?? throw new InvalidDataException(
        "Could not compress the patched shader bytecode."), 19);
}

static int PatchBytecodeSizeInMetadataBuffer(
    byte[] resourceBytes,
    int dataOffset,
    int originalSize,
    int replacementSize)
{
    if (originalSize == replacementSize)
    {
        return 0;
    }

    const int Kv3Version5HeaderSize = 120;
    const int CompressionMethodOffset = 20;
    const int CompressedBuffer1Offset = 76;
    const int UncompressedBuffer2Offset = 80;
    const int CompressedBuffer2Offset = 84;

    if (BitConverter.ToUInt32(resourceBytes, dataOffset) != 0x4B563305u
        || BitConverter.ToInt32(resourceBytes, dataOffset + CompressionMethodOffset) != 2)
    {
        throw new InvalidDataException(
            "Expected a Zstd-compressed Binary KV3 version-5 shader DATA block.");
    }
    var compressedBuffer1 = BitConverter.ToInt32(
        resourceBytes, dataOffset + CompressedBuffer1Offset);
    var rawBuffer2Size = BitConverter.ToInt32(
        resourceBytes, dataOffset + UncompressedBuffer2Offset);
    var compressedBuffer2Size = BitConverter.ToInt32(
        resourceBytes, dataOffset + CompressedBuffer2Offset);
    if (compressedBuffer1 <= 0 || rawBuffer2Size <= 0 || compressedBuffer2Size <= 0)
    {
        throw new InvalidDataException("Shader KV3 buffer sizes are invalid.");
    }

    var buffer2Start = checked(dataOffset + Kv3Version5HeaderSize + compressedBuffer1);
    var originalFrame = resourceBytes
        .AsSpan(buffer2Start, compressedBuffer2Size).ToArray();
    byte[] rawBuffer2;
    using (var decompressor = new Decompressor())
    {
        var buffer = new byte[rawBuffer2Size];
        if (!decompressor.TryUnwrap(originalFrame, buffer, out var written)
            || written != rawBuffer2Size)
        {
            throw new InvalidDataException("Could not decompress shader KV3 numeric buffer.");
        }
        rawBuffer2 = buffer;
    }

    Span<byte> originalNeedle = stackalloc byte[4];
    BitConverter.TryWriteBytes(originalNeedle, originalSize);
    var scalarOffset = FindUnique(rawBuffer2, originalNeedle);
    BitConverter.GetBytes(replacementSize).CopyTo(rawBuffer2, scalarOffset);

    for (var level = 1; level <= 22; level++)
    {
        using var compressor = new Compressor(level);
        compressor.SetParameter(ZSTD_cParameter.ZSTD_c_checksumFlag, 1);
        var candidate = compressor.Wrap(rawBuffer2).ToArray();
        if (candidate.Length == originalFrame.Length)
        {
            candidate.CopyTo(resourceBytes, buffer2Start);
            return level;
        }
    }

    throw new InvalidDataException(
        $"Shader KV3 numeric buffer could not retain its original "
        + $"{originalFrame.Length}-byte compressed size.");
}

static int PatchHashInMetadataFrame(
    byte[] resourceBytes,
    int dataOffset,
    int dataSize,
    byte[] originalHash,
    byte[] replacementHash)
{
    var dataEnd = checked(dataOffset + dataSize);
    if (dataOffset < 0 || dataEnd > resourceBytes.Length)
    {
        throw new InvalidDataException("Shader DATA block bounds are invalid.");
    }

    var compressedHashOffset = dataOffset
        + FindUnique(resourceBytes.AsSpan(dataOffset, dataSize), originalHash);
    ReadOnlySpan<byte> zstdMagic = [0x28, 0xB5, 0x2F, 0xFD];
    var frameStart = -1;
    for (var offset = dataOffset; offset <= compressedHashOffset - zstdMagic.Length; offset++)
    {
        if (resourceBytes.AsSpan(offset, zstdMagic.Length).SequenceEqual(zstdMagic))
        {
            frameStart = offset;
        }
    }
    if (frameStart < 0)
    {
        throw new InvalidDataException("Could not locate the shader metadata Zstd frame.");
    }
    for (var offset = compressedHashOffset + originalHash.Length;
        offset <= dataEnd - zstdMagic.Length;
        offset++)
    {
        if (resourceBytes.AsSpan(offset, zstdMagic.Length).SequenceEqual(zstdMagic))
        {
            throw new InvalidDataException(
                "The phase hash was not in the final shader metadata frame.");
        }
    }

    ReadOnlySpan<byte> kv3Trailer = [0x00, 0xDD, 0xEE, 0xFF];
    var frameEnd = dataEnd;
    if (resourceBytes.AsSpan(dataEnd - kv3Trailer.Length, kv3Trailer.Length)
        .SequenceEqual(kv3Trailer))
    {
        frameEnd -= kv3Trailer.Length;
    }
    var originalFrame = resourceBytes.AsSpan(frameStart, frameEnd - frameStart).ToArray();
    byte[] rawFrame;
    using (var decompressor = new Decompressor())
    {
        var buffer = new byte[1024 * 1024];
        if (!decompressor.TryUnwrap(originalFrame, buffer, out var written))
        {
            throw new InvalidDataException("Could not decompress shader metadata frame.");
        }
        rawFrame = buffer.AsSpan(0, written).ToArray();
    }
    var rawHashOffset = FindUnique(rawFrame, originalHash);
    replacementHash.CopyTo(rawFrame, rawHashOffset);

    for (var level = 1; level <= 22; level++)
    {
        using var compressor = new Compressor(level);
        compressor.SetParameter(ZSTD_cParameter.ZSTD_c_checksumFlag, 1);
        var candidate = compressor.Wrap(rawFrame).ToArray();
        if (candidate.Length != originalFrame.Length)
        {
            continue;
        }

        candidate.CopyTo(resourceBytes, frameStart);
        return level;
    }

    throw new InvalidDataException(
        "Patched phase hash could not be recompressed to the original metadata-frame size.");
}

static void VerifyOutput(string outputPath, float widthScale, byte[] expectedHash)
{
    using var program = new VfxProgramData();
    program.Read(outputPath);
    var combo = program.GetStaticCombo(program.StaticComboEntries.Single().Key);
    var shader = combo.ShaderFiles[OutlinePhase]
        ?? throw new InvalidDataException("Patched shader phase 2 is missing.");
    var size = BitConverter.ToInt32(shader.Bytecode, 24);
    var bytecode = shader.Bytecode.AsSpan(0, size).ToArray();
    VerifyDxbcChecksum(bytecode, "output phase 2");

    var negative = BitConverter.ToSingle(bytecode, NegativeScaleOffset);
    var positive = BitConverter.ToSingle(bytecode, PositiveScaleOffset);
    if (negative != -1.0f / widthScale || positive != 1.0f / widthScale)
    {
        throw new InvalidDataException("Serialized outline-width scale verification failed.");
    }
    if (!MD5.HashData(bytecode).AsSpan().SequenceEqual(expectedHash))
    {
        throw new InvalidDataException("Serialized phase hash verification failed.");
    }
}

static int FindUnique(ReadOnlySpan<byte> haystack, ReadOnlySpan<byte> needle)
{
    var found = -1;
    for (var start = 0; start <= haystack.Length - needle.Length; start++)
    {
        if (!haystack.Slice(start, needle.Length).SequenceEqual(needle))
        {
            continue;
        }
        if (found >= 0)
        {
            throw new InvalidDataException("Shader phase hash was not unique.");
        }
        found = start;
    }
    return found >= 0
        ? found
        : throw new InvalidDataException("Shader phase hash metadata was not found.");
}

static byte[] GetValveShaderDictionary()
{
    var dictionaryType = typeof(VfxProgramData).Assembly.GetType(
        "ValveResourceFormat.CompiledShader.ZstdDictionary", throwOnError: true)!;
    var method = dictionaryType.GetMethod(
        "GetDictionary_2bc2fa87",
        BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic)
        ?? throw new MissingMethodException(dictionaryType.FullName, "GetDictionary_2bc2fa87");
    return method.Invoke(null, null) as byte[]
        ?? throw new InvalidDataException("Valve shader dictionary was unavailable.");
}

static void VerifyDxbcChecksum(byte[] bytecode, string label)
{
    if (!DxbcChecksum.Compute(bytecode).AsSpan().SequenceEqual(bytecode.AsSpan(4, 16)))
    {
        throw new InvalidDataException($"DXBC checksum failed for {label}.");
    }
}
