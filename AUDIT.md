# BACKEND VERIFICATION AUDIT — Invisible City

Tanggal: 31 Jul 2026
Status: Audit selesai, belum ada perbaikan

Scope: `backend/app/api/v1/{facility,city,analytics}.py`, models, schemas, live DB.
Tidak ada fix dilakukan. DB state dipulihkan setelah test write (facility=77,869, user=1, 0 test row).

---

## 1. Facility API — **WARNING**

**Routes** (`backend/app/api/v1/facility.py`):
- `POST /api/v1/facilities/` — create
- `GET /api/v1/facilities/` — list
- **Tidak ada**: `GET /{id}`, `PUT`, `DELETE` (CRUD tidak lengkap)

**Query params**: `skip`, `limit` (default 0/100), `facility_type`, `city_id`, `district_id`. Semua filter berfungsi dan akurat vs DB (lihat §6).

**Pagination — FAIL**:
- `?limit=-5` → **HTTP 500** (unhandled psycopg2 error, bukan 400). `?skip=-5` sama.
- `?limit=200000` → 25.2 MB payload, **11.4s**. Tanpa max cap.
- Tanpa `ORDER BY` → urutan non-deterministik. Bukti: `limit=5` run1/run2 konsisten tapi `skip=5` mengembalikan `[79493, 57253, 57254, 11242, 57255]` (id out-of-order) → page boundary bisa shift/duplicate antar request.

**Response schema** (`schemas/facility.py`): `id, name, facility_type, lat, lng, source, external_id, raw_tags, city_id, district_id, source_updated_at`. Tidak mengembalikan `geom` (ok). `lat/lng` duplikasi koordinat `geom` (0 mismatch di DB).

**PostGIS usage**: list endpoint **tidak memakai spatial function sama sekali** — filter FK murni (`city_id`, `district_id`). Spatial join sudah dilakukan saat ETL (sesuai FACILITY_ARCHITECTURE decision). `geom` + GiST index ada tapi tak dipakai query-time.

**POST validation — FAIL** (`facility.py:10-32`):
- `name=""` → **accepted** (HTTP 200, id 104065)
- `lat=999, lng=999` → **accepted** (HTTP 200, id 104066) — tidak ada range check (-90..90 / -180..180)
- Tidak cek FK city/district exist, tidak cek containment lat/lng di district.
- Type validation OK: `lat="abc"` → 422.

---

## 2. Geographic / City API — **WARNING**

**Routes** (`backend/app/api/v1/city.py`):
- `GET /api/v1/cities/` — 515 kota (id + name)
- `GET /api/v1/cities/{city_id}/boundary` — GeoJSON FeatureCollection, 404 jika tak ada ✓
- `GET /api/v1/cities/{city_id}/districts` — GeoJSON FeatureCollection

**Province → City**: DB relasi benar (38 province, 515 city, FK `province_id` valid, 0 null). **Tapi tidak ada endpoint province sama sekali** — city selector flat, tak bisa filter by province. PRD Feature 1 mensyaratkan level Province. **GAP**.

**Performance — FAIL**: `GET /api/v1/cities` = **8.7–15.9s** untuk payload 16 KB. Root cause: `db.query(City).all()` (`city.py:16`) memuat **SEMUA kolom termasuk `geom` — total 205 MB** (515 kota × avg 400 KB). Bukti: `SELECT id,name FROM city` = **0.3ms** vs `SELECT *` = 0.1ms di PG tapi network+parsing 205MB WKB via psycopg2 = 8–16s.

**city_id consistency**: PASS — 0 orphan FK, filter city_id cocok dengan count DB.

**Districts bug**: `GET /cities/999999/districts` → **HTTP 200** dengan `features: []`, bukan 404 (inkonsisten vs boundary). Tidak cek city existence.

---

## 3. UFS / Analytics API — **FAIL** (sebagai UFS)

**Route** (`backend/app/api/v1/analytics.py:10-44`): `GET /api/v1/analytics/ufs?city_id=`

**Flow**: `count(facility [where city_id]) / baseline 20 → min(x*100, 100)`. Breakdown by type. Status Good/Fair/Poor.

**DB queries**: 2 count queries (total + breakdown group by). Exploitasi index `idx_facility_type_city` (EXPLAIN: Index Only Scan, 1.1ms). Cepat tapi...

**Hardcoded/mock — FAIL**:
- `baseline = 20.0` hardcoded (`analytics.py:28`) — bukan per-indicator, bukan per-populasi
- Status thresholds (`>=70 Good, >=40 Fair, else Poor`) **tidak sesuai PRD/skill** (Excellent 80 / Good 60 / Fair 40 / Poor 20 / Critical 0)
- Tidak ada 5 indicator modular (Education/Healthcare/Transportation/PublicSpace/Accessibility), tidak ada population/density input, tidak ada weights
- **Tidak ada tabel `ufs_scores`** (tidak ada di DB), tidak ada Redis cache — melanggar skill "scores must be cached in ufs_scores table"
- Efek: kota dengan ≥20 facility → UFS 100 (overestimate). Buatan.

**Correctness risk**: count AKURAT (diverifikasi §6), tapi angka UFS menyesatkan sebagai equity score. Business logic di API route, bukan service/GIS layer — melanggar AGENTS.md "Never perform GIS calculations inside API routes".

**Missing API** (PRD Phase 5-8): recommendation, priority ranking, simulator, report — semua belum ada.

---

## 4. Spatial Queries — **PASS** (dengan catatan)

**Relasi**: province(38) → city(515) → district(7,269) → village(0, deferred). 0 orphan district/city. Facility FKs valid (0 orphan). **92 facility NULL city+district** (School 55, Park 15, dst — orphan ETL, mayoritas NTT/Timor-Leste). Konsisten: 77,869 - 92 = 77,777 = jumlah `ST_Within` match.

**Geometry**: 0 null geom, semua POINT/MULTIPOLYGON EPSG:4326. `ST_X(geom)==lng` && `ST_Y(geom)==lat` untuk **semua** 77,869 rows (0 mismatch).

**Indexes** (semua ada):
- GiST: `idx_province_geom`, `idx_city_geom`, `idx_district_geom`, `idx_facility_geom`
- Btree: `idx_facility_type_city`, `idx_facility_district`, `idx_facility_source_eid`
- EXPLAIN: count query pakai Index Only Scan; list `LIMIT 100` pakai Seq Scan (2.5ms, fine).

**N+1**: **tidak ada**. Tidak ada `relationship()` di model Facility; semua route single-query. No lazy loading trigger.

**WARNING**:
- Facility query tak pernah pakai GiST (hanya boundary ETL/display)
- `/cities/{id}/districts` tak pakai `ST_Simplify` — 768 KB untuk 10 district (77 KB/district), melanggar panduan performa skill
- `Village` model ada tapi 0 rows + tak di-expose (deferred, bukan bug)

---

## 5. Tests — **FAIL**

- **Tidak ada folder tests** di repo (backend/frontend/root)
- `pytest` **tidak terpasang** di container backend (`ModuleNotFoundError`)
- `requirements.txt` tanpa pytest/ruff/black; tidak ada `pyproject.toml`/config lint
- Tidak bisa run tests — tidak ada yang bisa dijalankan

**Missing critical tests**: facility filter/pagination boundary, POST validation, UFS math, boundary GeoJSON, FK integrity, auth flows.

---

## 6. API Integration Verification — **PASS**

Semua endpoint dipanggil live vs query PostgreSQL langsung:

| Endpoint | API Result | DB Result | Verdict |
|----------|-----------|-----------|---------|
| `GET /facilities?city_id=264&limit=5` | 5 rows, all city 264 | count 2,970 | ✓ |
| `GET /facilities?facility_type=Hospital` | 3,804 total | 3,804 | ✓ |
| `GET /facilities?district_id=6397` | 10 rows, all district 6397 | — | ✓ |
| `GET /facilities?limit=200000` | 25.2 MB / 11.4s | 77,869 | ✓ count, ✗ perf |
| `GET /cities` | 515 | 515 | ✓ |
| `GET /cities/264/boundary` | MultiPolygon, 404 for bogus | — | ✓ |
| `GET /cities/264/districts` | 10 features (Tebet = Jakarta Selatan) | 10 | ✓ |
| `GET /analytics/ufs?city_id=264` | total 2,970, breakdown match | 2,970 | ✓ |
| `GET /analytics/ufs?city_id=239` | 1 School, score 5.0 | 1 | ✓ |
| `GET /analytics/ufs` | 77,869 | 77,869 | ✓ |
| `POST /facilities` (valid) | 200, row + geom benar | ST_X=lng | ✓ (cleaned) |
| `POST /facilities` lat=999 | 200 accepted | — | ✗ validation |
| `GET /facilities?limit=-5` | **500** | — | ✗ |
| Auth register/login/me | 200 / 200 / 200 | — | ✓ |
| Health | 200 | — | ✓ |

---

## Ringkasan Verdict

| Area | Verdict |
|------|---------|
| 1. Facility API | **WARNING** (filter akurat; pagination 500, no ORDER BY/no cap, validation lemah, CRUD parsial) |
| 2. Geographic/city API | **WARNING** (data konsisten; `/cities` 205MB geom per request = 8–16s, no province endpoint, districts no 404) |
| 3. UFS/analytics | **FAIL** (mock: baseline 20, status kategori salah, no ufs_scores/cache, no indicator modular) |
| 4. Spatial queries | **PASS** (relasi/geom/index benar, no N+1) |
| 5. Tests | **FAIL** (tidak ada tests, pytest tak terinstall) |
| 6. Integration | **PASS** (semua count API == DB) |

**Prioritas fix yang disarankan (menunggu instruksi)**:
1. `/cities` — jangan load `geom` (select id/name only) → hemat 8–15s
2. Pagination — `ge:0`, `le:500`, `ORDER BY id` → hilangkan 500 + non-determinism
3. POST facility — validasi name non-empty, lat/lng range, FK exist
4. UFS — implement per-indicator modular atau minimal align kategori PRD + `ufs_scores` cache
