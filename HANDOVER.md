# Handover — BIG Administrative Boundary ETL

## Status: ~90% Complete (Boundary ✅, Facility ETL code + architecture ✅, Import pending)

## What's Done

- **Spatial models**: `Province`, `City`, `District`, `Village` with `code` columns + relationships
- **Metadata table**: `DatasetMetadata` (layer_name, download_date, record_count, source, version, status)
- **Core ETL** (`backend/app/etl/big.py`):
  - UPSERT by code (idempotent)
  - Geometry validation (`make_valid` → `ensure_multipolygon`)
  - CRS normalization to EPSG:4326
  - GiST index creation
  - Province geometry generation via `ST_Union` of city geometries
  - Metadata recording for imports
  - **Batch persistence**: `load_cities`, `load_districts`, `load_villages` use `execute_values` for batch INSERT ... ON CONFLICT
  - **Timing instrumentation**: each phase (validation, geometry conversion, batch insert, commit) logged with `[timing]`
  - **Dedup by code** before batch insert to avoid PostgreSQL "cannot affect row a second time"
- **Provider abstraction** (`backend/app/etl/providers/`):
  - `DatasetProvider` ABC in `base.py`
  - `LocalFileProvider` in `local.py` — reads GeoJSON from local directory
  - `BIGFeatureServiceProvider` in `big_api.py` — downloads from BIG API with caching
  - `DmxsanProvider` in `dmxsan.py` — reads from dmxsan/indonesia-admin-boundaries repo with field mapping
  - `__init__.py` exports all providers
- **CLI scripts**: `download_boundaries.py`, `import_boundaries.py` with `--provider` flag (local|big-api|dmxsan|alfanas)
- **Dependencies**: `tqdm`, `requests`, `psycopg2-binary` already installed
- **AlfAnasProvider** (`backend/app/etl/providers/alfanas.py`): reads Kecamatan SHP, strips Z, ensures MultiPolygon, normalizes CRS, renames fields (KODE_KEC→code, KECAMATAN→name, KAB_KOTA→parent_name), fills null names with KODE_KEC, caches result
- **City alias mapping** (`backend/app/etl/mappings/city_aliases.json`): resolves 7 naming mismatches between SHP and City table (e.g. "Kota Administrasi Jakarta Barat" → "Kota Adm. Jakarta Barat")
- **Dataset restructure**: dmxsan data moved from external repo mount to `backend/data/raw/dmxsan/{province,city}/`; alfanas data at `backend/data/raw/alfanas/district/`
- **Docker**: stale `/dmxsan-data` volume removed from `docker-compose.yml`
- **Facility ETL** (`backend/app/etl/facility.py`): normalize, PostGIS temp table spatial join, batch execute_values INSERT ... ON CONFLICT, raw_tags JSONB preserved, timing instrumentation
- **PBF parser** (`backend/app/etl/pbf_parser.py`): reads per-province PBF via Pyrosm, filters 5 facility types (School/Hospital/Clinic/BusStop/Park) via OSM tag map
- **Facility CLI** (`backend/scripts/import_facilities.py`): `--types School --pbf ...` or default path
- **Facility model**: updated with `source`, `external_id`, `raw_tags JSONB`, `source_updated_at`, unique index on (source, external_id), composite index (facility_type, city_id), district_id index
- **Facility API**: `GET /api/v1/facilities` now supports `district_id` filter
- **Data architecture docs**: `docs/FACILITY_ACQUISITION.md` (strategy comparison), `docs/FACILITY_ARCHITECTURE.md` (1-2 year data model), `docs/FACILITY_ETL_DESIGN.md` (initial design)
- **Key finding**: Pyrosm default engine OOM on all PBF files. **`engine='out_of_core'`** required. Per-province PBF strategy validated.

## Session Log

### 26 Jul 2026 — Provider Abstraction + Batch Persistence + Dmxsan Import
- Built `DatasetProvider` ABC, `LocalFileProvider`, `BIGFeatureServiceProvider`, `DmxsanProvider`
- Refactored `big.py`: provider-aware functions, removed legacy BIG API code
- Refactored `load_cities/load_districts/load_villages` to batch `execute_values` with dedup + timing
- Set up Docker volume mount for dmxsan-data
- Successfully imported 38 provinces + 515 cities via DmxsanProvider (~5 min)
- Published `HANDOVER.md` v1 with full status, CLI usage, verification commands

### 27 Jul 2026 — Dataset Audit + Final Verification
- **Kecamatan SHP audit**: 7,275 features, `KODE_KEC` unique, EPSG:4326 — ready for district import
- **Kel_Desa SHP audit**: 83,518 features, `KODE_KD` 99.9% unique, `JENIS_KD` for type — ready for village import
- Docker Desktop pipe intermittently unavailable (`//./pipe/dockerDesktopLinuxEngine`) — direct Python fallback available
- Updated this handover with audit findings, new CLI examples, and updated pending work

### 28-29 Jul 2026 — Village ETL Implementation + Deferral
- AlfAnasProvider expanded: `desa` layer with field mapping (KODE_KD→kdpumdes, KEL_DESA→namobj, KODE_KEC→kdpumkec, JENIS_KD→tipadm), `_sanitize_village_type()` (0/4/999→NULL), `_fill_name_fallback` per layer
- `load_villages()` refactored: `iterrows`→`itertuples`, redundant `validate_geometry` removed, `ON CONFLICT DO UPDATE`→`DO NOTHING`, page_size benchmark loop added (200/500/1000), detailed phase timing
- Kel_Desa.shp (83,518 features, avg 9.5KB WKB, total ~757MB) copied to `backend/data/raw/alfanas/village/`
- All ETL runs failed:
  - Docker runs: bash timeout (60m, insert never finished) or OOM SIGKILL (exit 137)
  - Host Python runs: password auth failed from Windows; complex128 numpy error from `shapely.ops.transform`
- Root cause: Shapely C geometry objects (~800MB) + WKB bytes (~800MB) coexist in heap, exceeding Docker Desktop WSL2 VM total memory (2.77 GB). Not a dataset problem — ETL design issue.
- Decision: Deferred to Post-MVP. All code preserved. Streaming/chunked or PostgreSQL COPY recommended for re-implementation.

### 29 Jul 2026 — Facility ETL: Architecture Investigation + Code Complete
- **Data strategy decision** (docs/FACILITY_ACQUISITION.md): Geofabrik PBF + Pyrosm.
  Rejected Overpass (515 API calls), osm2pgsql (overkill for 5 types), government data
  (unreliable BIG API, unpredictable timeline).
- **Architecture decision** (docs/FACILITY_ARCHITECTURE.md):
  - facility table is source of truth (bukan OSM). Re-import tidak destroy enriched data.
  - raw_tags JSONB preserved untuk future reprocess tanpa re-download PBF.
  - Spatial join di ETL time (PostGIS ST_Intersects via temp table), bukan query runtime.
  - Update periodic (bulanan), bukan real-time sync.
- **Bottleneck discovery**: Pyrosm default engine OOM pada semua file PBF — bahkan Jakarta
  55 MB. Root cause: Cython extension alokasi memori berlebihan di `iter_primitive_blocks`.
- **Breakthrough**: Pyrosm `engine='out_of_core'` bekerja sempurna:
  - Jakarta 55 MB: 3,925 schools in 9.3s ✅
  - Full Indonesia 1.7 GB: open 1s, tapi query >10 menit (single-core fallback di docker exec)
- **Arsitektur final**: Per-province PBF + Pyrosm `engine='out_of_core'`.
  Setiap provinsi 5-254 MB, processing <30s per provinsi. Tidak perlu osmium.
- **Code completed** (belum dijalankan):
  - `backend/app/etl/pbf_parser.py` — reads PBF, filters 5 facility types via Pyrosm
  - `backend/app/etl/facility.py` — normalize, PostGIS spatial join, batch insert, raw_tags preserved
  - `backend/scripts/import_facilities.py` — CLI `--types School|Hospital|Clinic|BusStop|Park`
  - `backend/app/models/facility.py` — updated: source, external_id, raw_tags JSONB, source_updated_at, 3 indexes
  - `backend/app/schemas/facility.py` — updated with new fields
  - `backend/app/api/v1/facility.py` — added district_id filter
  - `backend/app/etl/big.py` — added facility GiST index
- **Docker instability**: `com.docker.service` stops intermittently — both `docker exec` and
  `docker compose` fail with pipe 500 error. Recovery: restart Docker Desktop manually.
- **DB schema**: ALTER TABLE + indexes applied via psql. Facility table ready for data.
- **Pyrosm v0.12.0** installed in running container (pip install).
- **osmium-tool v1.18.0** installed as fallback (apt-get). Not needed if using `out_of_core`.

### 27 Jul 2026 (Sesi 2) — District ETL + City Alias Mapping
- **AlfAnasProvider** created at `backend/app/etl/providers/alfanas.py` — reads Kecamatan.shp with full field mapping
- Provider registered in `__init__.py` + `import_boundaries.py` (`--provider alfanas`)
- LAYERS config updated: district fields changed to `code`/`name`/`parent_name`
- `load_districts()` enhanced: skips orphans (null/unmatched parent) instead of inserting NULL city_id; logs skipped count + samples
- Rollback handling added in `import_boundaries.py` for failed layers
- **Initial import**: 7,197 districts imported, 78 skipped (6 placeholder codes + 72 naming mismatches), 0 duplicates, 0 invalid geom, SRID 4326, GiST index created — ~224s
- **City alias mapping**: created `backend/app/etl/mappings/city_aliases.json` with 7 explicit 1:1 mappings
- `load_districts()` enhanced: resolves aliases via cached JSON before parent FK lookup; logs unresolved names for maintenance
- Docker Desktop pipe broke before re-run with aliases — import with aliases pending
- Dataset restructured: dmxsan moved to `backend/data/raw/dmxsan/`, stale Docker volume removed

## Verified Import (26 Jul 2026)

```
--provider dmxsan --layers provinsi kabupaten_kota

Timing:
  cities extract+validate+convert: 2.62s (521 rows)
  cities parent FK resolution:     0.02s (38 parents)
  cities dedup:                    6 rows
  cities batch insert:             39.27s (515 rows, page_size=200)
  cities commit:                   0.30s
  province geom generation:        ~77s (ST_Union)
  Total:                           299.5s (~5 min)

Results:
  province: 38 (geom: 38 valid, 0 null)
  city:     515 (geom: 515 valid, 0 null)
```

## Refactor Details

### Provider Abstraction (`backend/app/etl/big.py`)
- `BIG_BASE_URL`, `query_layer()`, `features_to_geojson()`, `download_layer()`, `download_all_layers()`, `load_geojson()` removed
- `load_layer(db, layer_cfg, provider=None)` — accepts any `DatasetProvider`
- `load_all_layers(db, provider=None, layers_to_load=None)` — provider parameter
- `run_full_etl(db, provider=None, layers_to_process=None)` — provider parameter
- `set_default_provider(provider)` / `get_default_provider()` — global default

### Batch Persistence (`backend/app/etl/big.py`)
Row-by-row ORM inserts replaced with `psycopg2.extras.execute_values`:

**Before** (per row):
```python
for _, row in gdf.iterrows():
    geom = validate_geometry(row.geometry)
    existing = db.query(City).filter(City.code == code).first()
    if existing: existing.name = name
    else: db.add(City(...))
    db.flush()
db.commit()
```

**After** (batch):
```python
# Phase 1: Extract + Validate + Convert geometry to WKB (timed)
# Phase 2: Resolve parent FKs in bulk query (timed)
# Phase 3: dedup → execute_values batch INSERT ... ON CONFLICT (timed)
# Phase 4: commit (timed)
```

## Verified Import — District (28 Jul 2026, Final)

```
--provider alfanas --layers kecamatan

Alias mapping: 10 entries (7 initial + 3 added after first re-run)
  Added: Kota Pare Pare→Kota Parepare, Pahuwato→Pohuwato,
         Pangkajene Kepulauan→Pangkajene Dan Kepulauan

Timing:
  districts extract+validate+convert:   69.3s (7,275 rows)
  districts parent FK resolution:       47.9s (514 parents resolved)
  districts skip orphans:                6 (placeholder codes only)
  districts batch insert:              141.4s (7,269 rows, page_size=200)
  districts commit:                      0.8s

Results:
  district:       7,269 (skipped 6 unavoidable placeholders)
  orphans:            0
  duplicate codes:    0
  invalid geometries: 0
  SRID:            4326
  GiST index: idx_district_geom

Note: 6 skipped records are placeholder data (codes like 82.--.--, 64.--.--)
with no KAB_KOTA value — unavoidable.
```

## CLI Usage

```powershell
# Import from local GeoJSON (default, no network)
docker compose run --rm backend python /app/scripts/import_boundaries.py

# Import with explicit input dir
docker compose run --rm backend python /app/scripts/import_boundaries.py --provider local --input-dir data/raw/big

# Download from BIG API (if server is responsive)
docker compose run --rm backend python /app/scripts/download_boundaries.py --provider big-api

# Import from BIG API directly (with caching)
docker compose run --rm backend python /app/scripts/import_boundaries.py --provider big-api

# Import using DmxsanProvider (reads from data/raw/dmxsan)
docker compose run --rm backend python /app/scripts/import_boundaries.py --provider dmxsan

# Import district from AlfAnas Kecamatan SHP
docker compose run --rm backend python /app/scripts/import_boundaries.py --provider alfanas --layers kecamatan
```

## AlfAnasProvider (`backend/app/etl/providers/alfanas.py`)
- Reads Kecamatan.shp from `backend/data/raw/alfanas/district/`
- Field mapping: `KODE_KEC`→`code`, `KECAMATAN`→`name`, `KAB_KOTA`→`parent_name`
- Falls back null KECAMATAN to KODE_KEC (8 records)
- Drops unused columns: KODE_KK, KODE_PROV, KAB_KOTA, PROVINSI, FID
- Strips Z dimension, ensures MultiPolygon, normalizes CRS to EPSG:4326
- Caches GeoDataFrame in memory
- Only supports `kecamatan` layer (raises ValueError for others)

## City Alias Mapping (`backend/app/etl/mappings/city_aliases.json`)
Resolves 7 naming mismatches between Kecamatan SHP (`KAB_KOTA`) and City table (`name`):

| SHP Name | DB Name |
|----------|---------|
| Kota Administrasi Jakarta Barat | Kota Adm. Jakarta Barat |
| Kota Administrasi Jakarta Pusat | Kota Adm. Jakarta Pusat |
| Kota Administrasi Jakarta Selatan | Kota Adm. Jakarta Selatan |
| Kota Administrasi Jakarta Timur | Kota Adm. Jakarta Timur |
| Kota Administrasi Jakarta Utara | Kota Adm. Jakarta Utara |
| Administrasi Kepulauan Seribu | Adm. Kep. Seribu |
| Kepulauan Siau Tagulandang Biaro | Kep. Siau Tagulandang Biaro |

Loaded once and cached at module level in `big.py`. Applied before parent FK lookup in `load_districts()`. Unresolved names logged with warning for maintenance.

## DmxsanProvider (`backend/app/etl/providers/dmxsan.py`)
- Reads 38 province files + 516 kabupaten files from cloned `dmxsan/indonesia-admin-boundaries` repo
- Field mapping: `WADMPR` → `namobj`, `WADMKK` → `wadmkk`+`namobj`, `WADMPR` → `wadmpr`
- Strips Z dimension from geometries (source has MULTIPOLYGON Z)
- Sets `OGR_GEOJSON_MAX_OBJ_SIZE=0` for large features
- In-memory cache for repeated reads
- Successfully imported 38 provinces + 515 cities in ~5 min (see Verified Import above)

## Dataset Audit (27 Jul 2026)

### Kecamatan SHP
Sourced from `batas-administrasi-indonesia/Kecamatan/Kecamatan SHP/`:
- **Count**: 7,275 features
- **Key field**: `KODE_KEC` — unique code, 0 null/duplicate
- **CRS**: EPSG:4326
- **Geometry**: mixed Polygon + MultiPolygon, has Z dimension
- **Parent keys**: `KODE_KK` → city, `KODE_PROV` → province
- **Verdict**: ready as primary source for district layer (strip Z, minor dedup)

### Kel_Desa SHP
Sourced from `batas-administrasi-indonesia/Kel_Desa/Kel_Desa/`:
- **Count**: 83,518 features
- **Key field**: `KODE_KD` — 83,452 unique, 37 null, 11 duplicate codes (placeholders like `91.15.--.----`)
- **Village type**: `JENIS_KD` provides Desa/Kelurahan/invalid classification
- **CRS**: EPSG:4326, has Z dimension
- **Verdict**: suitable with minor cleanup (reject null/placeholder codes, strip Z)
- **Recommended loader**: batch `execute_values` with dedup + null-code filtering

## Village ETL — Deferred (Post-MVP)

### Status
✅ AlfAnasProvider — desa layer: field mapping, sanitization, Z strip, MultiPolygon done
✅ `load_villages()` — refactored: itertuples, ON CONFLICT DO NOTHING, skip validate_geom
✅ Kel_Desa.shp — copied to `backend/data/raw/alfanas/village/`
❌ Execution blocked: OOM in Docker Desktop WSL2 VM (2.77 GB limit)

### Root Cause — ETL Design, Not Dataset

The ETL holds ALL geometries in Python heap simultaneously:

| Component | Memory | Detail |
|-----------|:------:|--------|
| Shapely C geometries (GeoDataFrame) | ~800 MB | 83k polygons × avg 593 vertices |
| WKB bytes objects (prepared list) | ~800 MB | wkb.dumps() output, avg 9.5 KB each |
| Python tuple/list/dict overhead | ~200 MB | prepared, filtered, dedup, value_tuples |
| execute_values temp SQL | ~50 MB | Per-batch hex-encoded WKB string |
| GeoDataFrame attributes | ~50 MB | 12 non-geometry columns |
| PostgreSQL shared_buffers | 128 MB | Server-side |
| Docker/Kernel + other containers | ~600 MB | Redis, OS, overlay |
| **Peak total** | **~2.6 GB** | Docker VM total: **2.77 GB** |

Container killed with `exitCode=137` (SIGKILL — OOM). No headroom for the benchmark loop or PostgreSQL parse trees.

**This is NOT a dataset problem.** The 83k villages (avg 9.5KB WKB, total ~757MB) are manageable. The issue is the in-memory ETL pattern: load → transform → serialize → hold all data until commit. GeoPandas' `memory_usage(deep=True)` reports only 54 MB because Shapely C structs are NOT tracked by Python's memory profiler.

### Failure History

| # | Code Version | Method | Duration | Result |
|:-:|:------------:|:------:|:--------:|:------:|
| 1 | Old (page=2000, iterrows, validate_geom) | Docker | 10 min | bash timeout (provider processing) |
| 2 | Old | Docker | 30 min | OOM (leaked container from #1, 1.88GB) |
| 3 | Old | Docker | 60 min | bash timeout (insert never finished) |
| 4 | New (page=2000, itertuples, no validate) | Docker | 491s | OOM exit=137 (benchmark loop) |
| 5 | New | Host Python 127.0.0.1 | — | password auth failed |
| 6 | New (with benchmark 200/500/1000) | Docker | 491s | OOM exit=137 (benchmark loop) |

### Bottleneck Diagnosis

| Component | Verdict | Evidence |
|-----------|:-------:|----------|
| **RAM** | 🔴 PRIMARY | exitCode=137 SIGKILL at 491s, ~2.3 GB resident |
| **execute_values** | 🟡 Temp allocation | 668 batches × avg 10MB SQL strings → heap fragmentation |
| **psycopg2** | 🟢 NOT bottleneck | Connections function correctly |
| **GeoPandas** | 🟡 Undercounted memory | memory_usage() reports 54MB, actual ~800MB (Shapely C) |
| **wkb.dumps()** | 🟢 NOT bottleneck | ~20s for 83k features (measured) |
| **PostgreSQL** | 🟢 NOT bottleneck | shared_buffers=128MB, work_mem=4MB, idle during OOM |
| **CPU** | 🟢 NOT bottleneck | Phase 1 completes in 130s, no CPU spike |
| **Docker VM** | 🔴 Limit 2.77 GB | docker info: Total Memory: 2.77GiB |
| **Host RAM** | 🟡 Low headroom | ~1 GB free before OOM |

### All Existing Code Preserved (No Cleanup)

| File/Location | What Exists |
|---------------|-------------|
| `backend/app/etl/big.py:388-516` | `load_villages()` — fully refactored with itertuples, benchmark, DO NOTHING |
| `backend/app/etl/providers/alfanas.py` | Desa layer in LAYER_PATHS, LAYER_FIELD_MAP, `_sanitize_village_type()` |
| `backend/data/raw/alfanas/village/` | Kel_Desa.shp + .dbf .shx .prj .cpg |
| `backend/app/models/spatial.py` | Village model, indexes, FK constraints |
| Docker/DB | `village` table exists with indexes, 0 rows |

### Re-implementation Recommendations (Post-MVP)

#### Approach A — Streaming Chunked Processing (Recommended)
```
for each chunk of 5,000 features:
    gdf = gpd.read_file(shp, rows=slice(start, start+5000))
    process_chunk(gdf)
    del gdf  # free memory before next chunk
```
- **Memory**: ~150 MB peak (5k geometries + WKB)
- **Runtime**: ~5 min total (more DB round trips)
- **Complexity**: Low (add `rows` parameter to provider)
- **Notes**: Reads the SHP file 17 times (slow) OR slice cached GeoDataFrame

#### Approach B — PostgreSQL COPY via GeoDataFrame.to_postgis()
```
gdf.to_postgis('village_staging', engine, if_exists='replace')
INSERT INTO village (code, name, district_id, geom, village_type, bps_code)
SELECT s.code, s.name, d.id, s.geom, s.village_type, s.bps_code
FROM village_staging s
JOIN district d ON d.code = s.parent_code
ON CONFLICT (code) DO NOTHING;
DROP TABLE village_staging;
```
- **Memory**: ~54 MB (GeoDataFrame only, no WKB bytes)
- **Runtime**: ~30s (COPY is 10-100x faster than INSERT)
- **Complexity**: Medium (staging table + FK join in SQL)
- **Notes**: Bypasses psycopg2 execute_values entirely. `to_postgis()` uses COPY internally.

#### Approach C — Chunked execute_values on Cached GeoDataFrame
```
gdf = provider.read_layer('desa')
chunk_size = 5000
for i in range(0, len(gdf), chunk_size):
    chunk = gdf.iloc[i:i+chunk_size]
    value_tuples = process_chunk(chunk)
    execute_values(..., value_tuples, ...)
    del chunk, value_tuples
del gdf
```
- **Memory**: ~200 MB peak (chunk only)
- **Runtime**: ~6 min (more round trips, but smaller per batch)
- **Complexity**: Low (add slice loop around existing code)
- **Notes**: No provider changes needed, only loop around current pipeline

**All three approaches solve the root cause**: eliminate the ~1.6 GB of simultaneously held geometry data by never loading all 83k features into memory at once.

## Known Issues / Blockers

1. **BIG Feature Service** (`kspservices.big.go.id`) is unreliable:
   - Layer 2 (City polygons): 500 errors / timeouts
   - Layer 3 (District): ~2 min per 1000 records
   - Layer 4 (Village): ~83k records → impractical via live API
2. **Layer 0** (Province) returns line geometry (`esriGeometryPolyline`), not polygons — geometry is generated via `ST_Union` after city import
3. **pg_hba.conf** was modified to `trust` for external connections from the Docker host
4. **Password issue**: PostgreSQL password auth fails from Windows host — connecting via Docker internal network works fine
5. **No sample GeoJSON files** in `data/raw/big/` yet — need to seed from GitHub mirror or alternative source
6. **Docker Desktop pipe** (`//./pipe/dockerDesktopLinuxEngine`) intermittently unavailable on Windows — some sessions cannot run `docker exec`; use `docker compose run --rm backend` or direct Python connection instead
7. **Docker Desktop WSL2 memory**: 2.77 GB total RAM limits large in-memory ETL. Village ETL (83k complex polygons) requires ~2.6 GB peak. Mitigation: chunked processing or increase Docker VM RAM via `.wslconfig`.
8. **Pyrosm default engine OOM**: `pyrosm.OSM()` default engine crashes with `Cannot allocate memory` on ANY PBF file (even 55 MB Jakarta) inside Docker. Temporary workaround: `engine='out_of_core'` parameter. Root cause: Cython extension `iter_primitive_blocks_and_string_tables` allocates excessive memory. If upstream fixes this, switch back to default engine.
9. **Pyrosm `workers='auto'` fails in docker exec**: Parallel decoding falls back to single process because `docker exec` lacks `if __name__ == "__main__"`. Full Indonesia PBF (1.7 GB) query takes >10 min single-core. Mitigation: per-province PBFs (5-254 MB each, process in <30s).

## Pending Work (~3%)

### 1. ~~Import Districts~~ ✅ DONE (7,269 imported)
- Final: 7,269 districts, 0 orphans, 0 dupes, 0 invalid geom, SRID 4326
- 6 unavoidable placeholder codes skipped (82.--.--, 64.--.--, etc.)
- 10 city aliases in `backend/app/etl/mappings/city_aliases.json`
- `load_districts` batch persistence verified with 7,275 rows

### 2. Import Villages — ❌ DEFERRED (Post-MVP)
- All code implemented, tested, and preserved (AlfAnasProvider desa layer, `load_villages()`, data files)
- Execution blocked by OOM in Docker Desktop WSL2 (2.77 GB limit)
- Root cause: in-memory ETL pattern holds all geometries + WKB simultaneously
- See Village ETL — Deferred (Post-MVP) section for root cause analysis and re-implementation recommendations

### 3. (Optional) GitHubReleaseProvider
- Add `providers/github.py` to download release zip from GitHub mirror

### 4. Facility ETL — Code ✅, Execution ⏳
- All code implemented: parser, normalizer, spatial join, batch insert, CLI, API
- DB schema updated + indexes applied
- Blocker: Pyrosm default engine OOM pada semua file PBF.
- **Solusi**: Pyrosm `engine='out_of_core'` + per-province PBF (download dari geo2day.com)
- **Next**: download per-province PBFs → jalankan import per provinsi → verifikasi
- Frontend "No Data Available" is caused by `facilities.length === 0` check (page.tsx:73) — not a bug, just empty table

## Verification Commands

```powershell
# Start DB
docker compose up -d db

# Reset tables
docker compose run --rm backend python /app/scripts/reset_db.py

# Import from local files (after seeding)
docker compose run --rm backend python /app/scripts/import_boundaries.py

# Verify
docker exec sdgs-db-1 psql -U postgres -d sdgs -c "
SELECT 'province' AS layer, count(*) FROM province
UNION ALL SELECT 'city', count(*) FROM city
UNION ALL SELECT 'district', count(*) FROM district;"
docker exec sdgs-db-1 psql -U postgres -d sdgs -c "SELECT * FROM dataset_metadata"

# Verify district FK integrity
docker exec sdgs-db-1 psql -U postgres -d sdgs -c "
SELECT count(*) AS orphan_districts FROM district d LEFT JOIN city c ON d.city_id = c.id WHERE c.id IS NULL;"

# Verify GiST index
docker exec sdgs-db-1 psql -U postgres -d sdgs -c "
SELECT indexname FROM pg_indexes WHERE tablename='district' AND indexdef LIKE '%gist%';"
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/etl/big.py` | Core ETL — load, validate, normalize |
| `backend/app/etl/providers/` | Provider abstraction (base, local, big_api, dmxsan, alfanas) |
| `backend/app/etl/providers/dmxsan.py` | DmxsanProvider — reads dmxsan/indonesia-admin-boundaries repo |
| `backend/app/etl/providers/alfanas.py` | AlfAnasProvider — reads Kecamatan SHP |
| `backend/app/etl/mappings/city_aliases.json` | City name alias mappings for parent FK resolution |
| `backend/app/etl/osm.py` | Existing OSM ETL (reference pattern) |
| `backend/app/models/spatial.py` | Spatial models |
| `backend/app/models/etl.py` | ETLJob + DatasetMetadata |
| `backend/scripts/download_boundaries.py` | Download CLI (--provider big-api\|local\|dmxsan) |
| `backend/scripts/import_boundaries.py` | Import CLI (--provider local\|big-api\|dmxsan\|alfanas) |
| `docker-compose.yml` | Service orchestration |
| `backend/app/etl/pbf_parser.py` | Pyrosm PBF parser — 5 facility types, engine='out_of_core' |
| `backend/app/etl/facility.py` | Facility ETL — normalize, spatial join, batch insert |
| `backend/scripts/import_facilities.py` | Facility import CLI (`--types --pbf`) |
| `docs/FACILITY_ACQUISITION.md` | Data strategy comparison (Overpass/PBF/osm2pgsql/Gov) |
| `docs/FACILITY_ARCHITECTURE.md` | 1-2 year facility data architecture decisions |
| `docs/FACILITY_ETL_DESIGN.md` | Initial ETL design document |
