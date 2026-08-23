using System.Text;
using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.Serialization.KeyValues;

const string PropertyName = "m_OutlineColorEnemyHero";

if (args.Length != 5
    || !byte.TryParse(args[2], out var requestedRed)
    || !byte.TryParse(args[3], out var requestedGreen)
    || !byte.TryParse(args[4], out var requestedBlue))
{
    Console.Error.WriteLine(
        "Usage: VDataPatch <input.vdata_c> <output.vdata_c> <red 0-255> "
        + "<green 0-255> <blue 0-255>");
    return 2;
}

var inputPath = Path.GetFullPath(args[0]);
var outputPath = Path.GetFullPath(args[1]);

using var resource = new Resource();
resource.Read(inputPath);

var originalDataBlock = resource.DataBlock
    ?? throw new InvalidDataException("Resource has no DATA block.");

BinaryKV3 dataBlock;
using (var source = File.OpenRead(inputPath))
using (var reader = new BinaryReader(source, Encoding.UTF8, leaveOpen: false))
{
    dataBlock = new BinaryKV3(BlockType.DATA)
    {
        Size = originalDataBlock.Size,
        Offset = originalDataBlock.Offset,
        Resource = resource,
    };
    dataBlock.Read(reader);
}

if (!dataBlock.Data.Properties.TryGetValue(PropertyName, out var colorValue)
    || colorValue.Value is not KVObject color
    || !color.IsArray
    || color.Count != 4)
{
    throw new InvalidDataException($"Expected a four-component {PropertyName} array.");
}

var before = Enumerable.Range(0, 3)
    .Select(index => Convert.ToByte(color[index].Value))
    .ToArray();
var replacementValues = Enumerable.Range(0, color.Count)
    .Select(index => color[index])
    .ToList();
var requested = new[] { requestedRed, requestedGreen, requestedBlue };
for (var index = 0; index < requested.Length; index++)
{
    replacementValues[index] = new KVValue(
        color[index].Type, color[index].Flag, (int)requested[index]);
}
var replacementColor = new KVObject(color.Key, replacementValues);
dataBlock.Data.Properties[PropertyName] = new KVValue(
    colorValue.Type,
    colorValue.Flag,
    replacementColor);

using var serializedData = new MemoryStream();
dataBlock.Serialize(serializedData);
var replacementData = serializedData.ToArray();

var originalBytes = File.ReadAllBytes(inputPath);
Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
using (var output = new FileStream(outputPath, FileMode.Create, FileAccess.Write, FileShare.None))
using (var writer = new BinaryWriter(output, Encoding.UTF8, leaveOpen: true))
{
    writer.Write(0xDEADBEEFu);
    writer.Write(resource.HeaderVersion);
    writer.Write(resource.Version);
    writer.Write(8u);
    writer.Write((uint)resource.Blocks.Count);

    var metadataOffsets = new long[resource.Blocks.Count];
    for (var index = 0; index < resource.Blocks.Count; index++)
    {
        writer.Write((uint)resource.Blocks[index].Type);
        metadataOffsets[index] = output.Position;
        writer.Write(0xDEADBEEFu);
        writer.Write(0xDEADBEEFu);
    }

    for (var index = 0; index < resource.Blocks.Count; index++)
    {
        while (output.Position % 16 != 0)
        {
            writer.Write((byte)0);
        }

        var block = resource.Blocks[index];
        var blockStart = output.Position;
        if (ReferenceEquals(block, originalDataBlock))
        {
            writer.Write(replacementData);
        }
        else
        {
            writer.Write(originalBytes, checked((int)block.Offset), checked((int)block.Size));
        }
        var blockEnd = output.Position;

        output.Position = metadataOffsets[index];
        writer.Write(checked((uint)(blockStart - metadataOffsets[index])));
        writer.Write(checked((uint)(blockEnd - blockStart)));
        output.Position = blockEnd;
    }

    var finalSize = checked((uint)output.Length);
    output.Position = 0;
    writer.Write(finalSize);
}

using var verificationResource = new Resource();
verificationResource.Read(outputPath);
var verificationOriginal = verificationResource.DataBlock
    ?? throw new InvalidDataException("Serialized resource has no DATA block.");
using var verificationSource = File.OpenRead(outputPath);
using var verificationReader = new BinaryReader(verificationSource, Encoding.UTF8, leaveOpen: false);
var verificationData = new BinaryKV3(BlockType.DATA)
{
    Size = verificationOriginal.Size,
    Offset = verificationOriginal.Offset,
    Resource = verificationResource,
};
verificationData.Read(verificationReader);
if (verificationData.Data.Properties[PropertyName].Value is not KVObject verificationColor)
{
    throw new InvalidDataException($"Serialized {PropertyName} is not an array.");
}
var verified = Enumerable.Range(0, 3)
    .Select(index => Convert.ToByte(verificationColor[index].Value))
    .ToArray();
if (!verified.SequenceEqual(requested))
{
    throw new InvalidDataException(
        "Serialized RGB verification failed: "
        + $"expected {string.Join(',', requested)}, got {string.Join(',', verified)}.");
}

Console.WriteLine(
    $"{PropertyName} RGB: {string.Join(',', before)} -> {string.Join(',', verified)}");
Console.WriteLine($"wrote {outputPath} ({new FileInfo(outputPath).Length} bytes)");
return 0;
