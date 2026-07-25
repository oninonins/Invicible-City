---
name: urban-analysis
description: Urban Fairness Score calculation, spatial analysis patterns, GIS methodology, and accessibility analysis for the Invisible City platform
license: MIT
compatibility: opencode, claude
metadata:
  domain: urban-planning
  project: invisible-city
---

## What I Do

This skill defines the domain-specific urban analysis methodology and GIS infrastructure used by the Invisible City platform. It covers the Urban Fairness Score (UFS), GIS infrastructure, ETL engineering, spatial analysis operations, data sources, and simulation patterns.

Use this skill whenever implementing or modifying features related to:
- Urban Fairness Score calculation
- Spatial / GIS analysis
- Accessibility measurement
- Impact simulation
- Recommendation engine logic

---

## 1. Urban Fairness Score (UFS)

### Modular Indicators

UFS is composed of 5 modular indicators, each scored 0–100 independently:

| Indicator | Weight (default) | Description |
|-----------|-----------------|-------------|
| Education Score | 20% | School availability vs. school-age population |
| Healthcare Score | 20% | Hospital/clinic availability vs. total population |
| Transportation Score | 20% | Bus stop / transit stop density per km² |
| Public Space Score | 20% | Park / public space area per capita |
| Accessibility Score | 20% | Average distance to nearest facility of each type |

### Per-Indicator Formula

```
ratio = actual_value / target_value
score = min(ratio * 100, 100)
```

- `actual_value` — real count from database for the given area
- `target_value` — predefined baseline (e.g., 1 school per 5000 children, 1 clinic per 10000 people)
- Score is capped at 100

### Aggregation

```
UFS = Σ(weight_i × score_i)
```

- Default: equal weights (20% each)
- Weights must be configurable per city via a future admin setting
- Always round final score to 1 decimal place

### Categories

| Range | Category |
|-------|----------|
| 80–100 | Excellent |
| 60–79 | Good |
| 40–59 | Fair |
| 20–39 | Poor |
| 0–19 | Critical |

### Implementation Rules

- All UFS calculations must filter by `city_id` or `district_id` from the Geographic Context
- Scores must be cached in the `ufs_scores` table with a materialized timestamp
- Modular design: each indicator is an independent service function
- Never hardcode targets — store in a `ufs_indicators` config table or env

---

## 2. GIS Infrastructure & ETL Engineering

### PostGIS Extension & Tuning

**Extension setup:**
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

**Spatial indexes:**
- Always create GIST index on geometry columns:

```sql
CREATE INDEX idx_facilities_geom ON facilities USING GIST (geom);
CREATE INDEX idx_district_geom ON districts USING GIST (geom);
```

- Partial indexes for filtered queries:

```sql
CREATE INDEX idx_facilities_school_geom ON facilities USING GIST (geom) WHERE facility_type = 'School';
```

**Geometry validation pipeline:**
```python
def validate_geometry(geom):
    if not geom.is_valid:
        reason = geom.is_valid_detail()
        geom = geom.buffer(0)
        log_warning(f"Geometry fixed: {reason}")
    return geom
```

Invalid geometries should be quarantined in an `etl_geometry_errors` table for manual review, never silently dropped.

### ETL Pipeline Engineering

**OSM import strategies:**

| Method | When to Use |
|--------|-------------|
| `osmium tags-filter` + custom script | Selective extraction of specific amenity tags |
| `osm2pgsql` | Full continent/country import with rendering |
| `osmnx` (Python) | Small area extraction for analysis |

**OSM tag filtering (osmium):**
```bash
osmium tags-filter input.osm.pbf \
  amenity=school,hospital,clinic,bus_stop,bus_station,kindergarten,university \
  -o filtered.osm.pbf
```

**Shapefile import (BIG data):**
```bash
# Handle CP1252 encoding (common in Indonesian government shapefiles)
ogr2ogr -lco ENCODING=UTF-8 -nlt PROMOTE_TO_MULTI \
  -t_srs EPSG:4326 output.geojson input.shp
```

**GeoJSON CRS validation:**
- Always verify coordinate order is lon/lat (not lat/lon)
- Validate with `ogrinfo -al -so file.geojson`
- Reject files with CRS other than EPSG:4326

**Failed geometry quarantine table:**
```sql
CREATE TABLE etl_geometry_errors (
    id SERIAL PRIMARY KEY,
    source TEXT,
    original_geom TEXT,
    error_detail TEXT,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending'
);
```

### OSRM Setup

**Pipeline:**
```bash
osrm-extract -p car.lua region-latest.osm.pbf
osrm-contract region-latest.osrm
osrm-routed --algorithm mld region-latest.osrm
```

**Profiles:**
- `car.lua` — for driving time estimates
- `foot.lua` — for walking accessibility (15-min catchment)
- `bike.lua` — for cycling mobility analysis

**Indonesia PBF source:**
```
https://download.geofabrik.de/asia/indonesia-latest.osm.pbf
```

**Health check:**
```bash
curl http://osrm:5000/health
```

**Docker Compose integration:**
```yaml
osrm:
  image: ghcr.io/project-osrm/osrm-backend
  command: >
    sh -c "osrm-extract -p /opt/car.lua /data/indonesia-latest.osm.pbf
    && osrm-contract /data/indonesia-latest.osrm
    && osrm-routed --algorithm mld /data/indonesia-latest.osrm"
  volumes:
    - osrm-data:/data
  ports:
    - "5000:5000"
```

### GDAL Utilities

| Command | Purpose |
|---------|---------|
| `ogr2ogr -f GeoJSON output.geojson input.shp` | Shapefile → GeoJSON |
| `ogr2ogr -f GPKG output.gpkg input.geojson` | GeoJSON → GeoPackage |
| `ogr2ogr -t_srs EPSG:4326 output.shp input.shp` | CRS reprojection |
| `ogrinfo -al -so file.geojson` | Schema inspection without data |
| `ogrinfo -sql "SELECT * FROM layer WHERE ..." file.gpkg` | SQL filter on vector file |

### Table Partitioning

For cities with more than 100,000 facilities, use PostgreSQL partitioning:

```sql
CREATE TABLE facilities_partitioned (
    LIKE facilities INCLUDING ALL
) PARTITION BY LIST (city_id);

CREATE TABLE facilities_city_1 PARTITION OF facilities_partitioned
    FOR VALUES IN (1);
CREATE TABLE facilities_city_2 PARTITION OF facilities_partitioned
    FOR VALUES IN (2);
```

---

## 3. Spatial Analysis & GIS Operations

### Coordinate Reference System (CRS)

| Use Case | CRS | EPSG |
|----------|-----|------|
| Input / storage | WGS 84 | 4326 |
| Distance / area calculation | UTM zone 49S (Indonesia) | 32749 |
| Display (frontend map) | WGS 84 | 4326 |

Always convert to EPSG:32749 before calculating distances or areas.

### PostGIS Patterns

**Buffer zones (catchment areas):**
```sql
ST_Buffer(geom::geography, radius_meters)
```
Use `::geography` cast for accurate meter-based buffers.

**Nearest-neighbor query:**
```sql
SELECT id, name, ST_Distance(geom::geography, <target>::geography) AS dist
FROM facilities
ORDER BY geom::geography <-> <target>::geography
LIMIT 1;
```

**Spatial containment:**
```sql
ST_Contains(district.geom, facility.geom)
ST_Within(facility.geom, district.geom)
```

**Filter by administrative area:**
```sql
ST_Intersects(area.geom, facility.geom)
```

### GeoPandas / Shapely Patterns

```python
# Buffer in meters (project first)
gdf = gdf.to_crs("EPSG:32749")
gdf["buffer"] = gdf.geometry.buffer(radius_meters)
gdf = gdf.to_crs("EPSG:4326")

# Spatial join
joined = gpd.sjoin(facilities_gdf, districts_gdf, how="left", predicate="within")
```

### Network Analysis

- **OSRM** — for travel time / distance matrix between facilities and population centers
  - Use `table` service for many-to-many distance/time
  - Use `route` service for point-to-point directions
- **NetworkX** — for graph-based traversal (shortest path, isochrones)
  - Build graph from OSM road data via `osmnx`
  - Calculate shortest path with travel time weights

### Performance Optimization

**Bounding box filtering:**
```sql
-- Fast bounding box pre-filter (&& operator)
SELECT * FROM facilities
WHERE geom && ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326);

-- Precise intersection (slower, use after bbox filter)
AND ST_Intersects(geom, ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326));
```

**GeoJSON response optimization:**
```sql
SELECT id, name, ST_AsGeoJSON(ST_Simplify(geom, 0.001), 6) AS geojson
FROM facilities WHERE city_id = :city_id;
```

- Use `ST_Simplify` to reduce GeoJSON payload size for web display
- Maximum 6 decimal places for coordinates
- Use `ST_AsGeoJSON` directly in SQL instead of serializing in Python

---

## 4. Administrative Hierarchy

```
Province → City → District → Village → Facilities
```

### Rules

- Every spatial query must respect the current geographic context
- `facilities` table contains `city_id` (required) and `district_id` (optional) foreign keys
- Filter chain: selected province → filter available cities → selected city → filter districts
- Administrative boundaries use `MULTIPOLYGON` geometry type
- Hierarchy is defined in `Province`, `City`, `District`, `Village` models with `geom` column

### Example Query Chain

```python
# Get all facilities in a district
facilities = db.query(Facility).filter(
    Facility.district_id == district_id,
    ST_Within(Facility.geom, district.geom)
).all()
```

---

## 5. Data Sources

| Source | CRS | Format | Frequency | Usage |
|--------|-----|--------|-----------|-------|
| OpenStreetMap (OSM) | 4326 | PBF / GeoJSON | Monthly | Roads, schools, hospitals, bus stops, parks |
| BIG (Geoportal) | 4326 | Shapefile | Annually | Administrative boundaries, rivers |
| BPS (Statistics) | — | CSV / JSON | Annually | Population, density, poverty data |
| Satu Data Indonesia | 4326 | GeoJSON / API | Bi-Annually | Government facilities |

### Facility Type Mapping (OSM → Category)

| OSM amenity | Category | UFS Indicator |
|-------------|----------|---------------|
| `school`, `kindergarten`, `university` | School | Education |
| `hospital`, `clinic`, `doctors` | Healthcare | Healthcare |
| `bus_station`, `bus_stop` | Transport | Transportation |
| `park`, `playground`, `garden` | Public Space | Public Space |
| (all of the above) | — | Accessibility |

---

## 6. Accessibility Analysis

### Distance Types

| Type | Method | When to Use |
|------|--------|-------------|
| Euclidean | `ST_Distance(geom::geography, ...)` | Quick estimates, large areas |
| Network-based | OSRM / NetworkX routing | Accurate travel time, walkability |
| Manhattan | PostGIS `ST_Distance` with projection | Grid-pattern cities |

### Catchment Area Standards

| Mode | Catchment Radius |
|------|-----------------|
| Walking | 15 minutes (~1 km) |
| Public transit | 30 minutes |
| Driving | 45 minutes |

### Accessibility Score Logic

```
For each facility type:
  1. Find nearest facility to each population point
  2. Calculate average distance across all population points
  3. Normalize: score = max(0, 100 - (avg_distance / max_threshold * 100))

Final Accessibility Score = average across all facility types
```

---

## 7. Impact Simulation Pattern

### Principle

Simulations operate on a **Temporary Simulation Layer** and **never** modify production `facilities` data directly.

### Implementation

1. User creates a scenario: `simulations` table (scenario_id, city_id, name, created_at)
2. Temporary facilities stored in `temp_simulation_facilities` (scenario_id, geom, facility_type, name)
3. UFS is recalculated using: `production_facilities UNION temp_simulation_facilities`
4. Results stored in `simulation_results` (scenario_id, before_score, after_score, improvement)
5. On discard: delete all rows with matching `scenario_id`
6. On save: optionally promote temp facilities to real `facilities` (requires admin approval)

### SQL Pattern

```sql
WITH all_facilities AS (
    SELECT geom, facility_type FROM facilities WHERE city_id = :city_id
    UNION ALL
    SELECT geom, facility_type FROM temp_simulation_facilities WHERE scenario_id = :scenario_id
)
SELECT facility_type, COUNT(*) FROM all_facilities GROUP BY facility_type;
```

---

## 8. Recommendation Engine

### Architecture

```
Spatial Analysis → Rule Engine → Priority Generator → LLM Narrative (optional)
```

### Rule Engine Rules

- If UFS < 40 and facility density < 50% of target → **High Priority**
- If UFS 40–60 and no facility within 2 km → **Medium Priority**
- If UFS > 60 → **Low Priority / Maintenance**
- Population density multiplier: high density + low UFS = higher priority

### Priority Generator Output

```json
{
  "priority": 1,
  "area_id": 123,
  "area_name": "Kecamatan X",
  "ufs_score": 32.5,
  "recommended_action": "Build 1 public school",
  "reasoning": "Only 2 schools for 15000 school-age children (target: 3)",
  "expected_impact": "+8.2 UFS improvement"
}
```

### LLM Integration

- LLM is **optional** — the system must work without it
- If LLM is configured, enrich the output with a natural-language narrative paragraph
- The LLM provider must be abstracted behind an interface (OpenAI / Gemini / dummy)
- Prompt must include UFS breakdown, priority items, and area context

---

## 9. Caching Strategy

- UFS scores per district → cache in Redis with TTL 1 hour (or until next ETL run)
- Facility counts per area → cache in Redis with TTL 30 minutes
- OSRM distance matrix → cache per origin-destination pair
- Invalidate cache when ETL pipeline completes for a city

---

## 10. Error Handling

Every urban analysis function must handle:

| Condition | Behavior |
|-----------|----------|
| No facilities in area | Return score 0 with status "No Data" |
| Missing demographic data | Skip affected indicator, rebalance weights |
| Geometry validation failure | Log error, skip row, continue pipeline |
| OSRM service unavailable | Fall back to Euclidean distance with warning |
| Empty simulation scenario | Return "No changes detected" |
