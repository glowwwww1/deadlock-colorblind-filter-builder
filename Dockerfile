FROM mcr.microsoft.com/dotnet/sdk:9.0 AS vdata-builder

WORKDIR /source
COPY tools/vdata_patch/VDataPatch.csproj tools/vdata_patch/
RUN dotnet restore tools/vdata_patch/VDataPatch.csproj --runtime linux-x64
COPY tools/vdata_patch/Program.cs tools/vdata_patch/GlobalUsings.cs tools/vdata_patch/
RUN dotnet publish tools/vdata_patch/VDataPatch.csproj -c Release -r linux-x64 --self-contained false --no-restore -o /publish

FROM mcr.microsoft.com/dotnet/runtime:9.0

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/deadlock-builder
ENV PATH="/opt/deadlock-builder/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY web_app.py build_colorblind_mod.py colorfilters.py vpk_util.py ./
COPY web/ web/
COPY demo_images/ demo_images/
COPY assets/ assets/
COPY backup/original_vpost/ backup/original_vpost/
COPY backup/original_vcss/ backup/original_vcss/
COPY backup/original_shaders/ backup/original_shaders/
COPY backup/original_vdata/ backup/original_vdata/
COPY THIRD_PARTY_NOTICES.md ./
COPY --from=vdata-builder /publish/ tools/vdata_patch/publish/

EXPOSE 10000
CMD ["python3", "web_app.py", "--host", "0.0.0.0", "--no-browser"]
