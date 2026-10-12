# Airways Atlas

A map workspace for public US aviation infrastructure. Radar and control facilities are the default view. Exact documented equipment types appear in the catalog and inspector; satellite imagery is available in the Map / Satellite switch and each located facility's inspection button.

## Run and verify

```sh
npm install
npm run dev
npm run data:build
npm run data:update   # adopt a newer FAA NASR release (see below)
npm test
npm run test:browser
npm run build
```

Vite serves localhost:5173; the static production build is `dist/`. No deployment is configured.

## Sources and reliability

FAA NASR cycle **2026-10-01** is the primary inventory. Retained originals and SHA-256 hashes are in `data/raw/manifest.json`. The dataset contains **11,677 normalized records**, **11,600 mapped**, and **77 unlocated**. Counts are records, not established unique installations or a complete national inventory.

Supplemental evidence is retained and hash-checked separately in `data/supplemental/manifest.json`:

- [NASA/JPL FAA long-range radar inventory](https://uavsar.jpl.nasa.gov/kml/FAA_LongRangeRadars.kml): 93 US/territory sites. Site coordinates come from descriptions, not decorative polygon geometries. The publication date is unknown.
- [FAA-sponsored MIT Lincoln Laboratory ATC-425](https://www.ll.mit.edu/sites/default/files/publication/doc/2018-05/Cho_2015_ATC-425.pdf): 2015-05-26 long-range equipment inventory, distinguishing ARSR-4 and CARSR-program sites. CARSR entries retain their original legacy type. Current conversion and operational status are not certified.
- [FAA-sponsored ATC-450](https://www.ll.mit.edu/sites/default/files/publication/doc/radar-coverage-analysis-terminal-precipitation-glass-program-cho-atc-450.pdf): 2022-03-04 terminal models, including ASR-8/9/11, and explicitly documented NCT sensor associations. The retained filename contains 2021, but the report and displayed evidence date are 2022.
- [FAA service-center directory](https://www.faa.gov/sites/faa.gov/files/service-center-list-12.19.23.pdf): 2023-12-19 facility addresses. Published addresses remain in the inspector. A TRACON building is the facility itself, so TRACONs with an official address are mapped at a labeled estimate of that address, marked ≈ and "Approximate address". Seven use the service-center directory (NCT, SCT, C90, PCT, N90, S46, T75). Fourteen more use FAA Letter to Airmen letterheads and the FAA PIV service-center list (2026-09-18), positioned by a unique Census address match (A11, D01, F11, M03, M98, P31, P50, Y90) or EPA Facility Registry Service coordinates (D10, I90, L30, R90, U90, A90). EPA does not state how its coordinates were collected. Conflicting official addresses are noted in each record. A80, D21, JCF, P80 and S56 have official addresses but no unique match, so they remain unlocated. `npm run data:tracons` retains the source pages, EPA responses and geocodes with checksums in `data/supplemental/tracon-manifest.json`; the per-facility decisions are in `data/supplemental/tracon_sources.json`. Tower address estimates are retained as research only and are not rendered.
- [FAA NFDD 056](https://aeronav.faa.gov/aero_data/NFDD/nfdd-2025-03-25-56.pdf): 2025-03-25 OAK and NUQ antenna positions quoted in a removed procedure remark. Removal reflects documentation requirements; it does not establish installation removal or current equipment status.
- [NTSB WPR16FA172 ATC factual report](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=Air+Traffic+Control+Group+Chairman%27s+Factual+Report-Master.PDF&ID=40464366): 2017-11-02 Reno ASR-11 antenna position; the 2022 equipment inventory separately corroborates its model.
- [DOT/FAA QMV procurement forecast](https://www.transportation.gov/procurement-forecast-opportunity/procurement-forecast-opportunity-673706-1-facilities-security): 2024-09-03 identity corroboration for the Mill Valley radar site.
- [Radomes.org Mill Valley history](https://www.radomes.org/museum/showsite.php?site=Mill+Valley+AFS%2C+CA): clearly labeled community evidence for Mt. Tam's historical aliases. Its coordinates and primary model evidence come from the government inventory and FAA-sponsored research.

Every facility carries field-level sources with publisher, document link, evidence fields and dates. Location and model dates remain separate from the NASR release. An older documented model is never presented as confirmed live equipment. Records without published equipment coordinates use explicitly labeled FAA airport reference markers only when the source documents an airport association. Otherwise they remain searchable and unlocated. Historical and current records may overlap across source tables; cross-table installation reconciliation is incomplete.

Boundaries now come directly from [FAA Aeronautical Information Services' Airspace Boundary service](https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/ArcGIS/rest/services/Boundary_Airspace/FeatureServer), effective **2026-09-03 through 2026-10-29**. Its FAA ownership, service metadata, WGS84 query and 74 polygon records are retained and checksum-validated in `data/boundaries/manifest.json`. They cover 27 center/region identifiers and 58 center/type/altitude variants. High and low center geometries are selected separately; oceanic FIR and CTA are separate choices. Multi-part regions retain every source polygon. Date-line outlines are split at the map seam to prevent world-spanning diagonal lines.

The earlier ARB prose renderer incorrectly discarded supplied intermediate border/arc vertices and overlaid altitude variants. It has been replaced rather than patched with invented segments. Raw ARB records remain archived for comparison. These are chart-published center and FIR/CTA outlines, **not internal controller sector boundaries** or live sector configurations. No radar coverage or responsibility is inferred from distance; the optional modeled coverage layer below is a terrain line-of-sight model, not published coverage.

## Interaction and data workflow

Search names, identifiers, models, aliases and published associations across all layers. Without a search, selected layers control browsing. State and exact type filters apply in both cases. Mapped-only is optional; unknown locations remain visible by default. NCT details retain the seven sensor identifiers explicitly listed in ATC-450 and link matched records. Clicking an ARTCC opens its complete published association list across all layers and states, including unlocated systems. Ordinary filters are paused in this view; its search searches associated systems. Center boundaries appear automatically, with a thick colored line and contrasting casing on map and satellite imagery. Boundary lines are clickable, including the San Juan CERAP region. Center selection fits the boundary and associated locations. Selecting an associated system retains center context; Exit center systems restores browsing. The map still samples at most 150 marker elements per viewport. An ≈ annotation identifies airport-reference markers; tooltips and details explicitly distinguish them from equipment positions. Unclustered SVG symbols show individual facilities, with centered navigation diamonds and no circular icon containers. At most 150 map marker elements are mounted, including selection brackets. Each pan, zoom, resize or filter change recomputes a spatially distributed sample of viewport facilities; zooming in reveals more detail. Existing markers are retained when possible. The complete results list remains searchable, and a map count indicates when locations are hidden.

Approach service has its own symbols: TRACON/CERAP approach facilities use a scope symbol, and combined tower facilities whose FAA type includes approach control (ATCT-TRACON, ATCT-RAPCON, ATCT-A/C, ATCT-RATCF) carry a small teal approach badge on the tower symbol.

Mobile has Map / Facilities tabs and a dismissible facility inspector. `/` focuses search; Escape closes details. Filters, region, basemap and selected facility persist in the share URL. Map tiles and optional fonts require network access; data and tile failures have separate messages.

### Modeled radar coverage

FAA does not publish radar coverage. The "Modeled radar coverage" control shows terrain line-of-sight at 1,000, 2,500, 5,000 or 10,000 ft above ground, computed by `npm run data:coverage` using the method of the FAA-sponsored [ATC-425](https://www.ll.mit.edu/sites/default/files/publication/doc/2018-05/Cho_2015_ATC-425.pdf) report: SRTM-derived terrain, a 4/3-Earth-radius refraction model, and the Table 2-1 maximum aircraft detection range for each radar family (ARSR-4 420 km; CARSR 430 km for FPS and 380 km for ARSR-1/2/3 legacy sites; ASR 100 km). Only radars with published site or antenna coordinates and a documented family are modeled: 39 ARSR-4, 48 CARSR and 3 terminal ASRs. Radars placed at airport reference points, or with no documented model, are listed as not modeled, with the reason given. With no radar selected, national mosaics show where any modeled radar has line of sight; darker areas are covered by more radars. Selecting a modeled radar shows only its coverage, with the covered fraction at each altitude.

The model assumes a 20 m antenna above the terrain at each site, because tower heights are not published. It ignores buildings, vegetation, beam patterns, ground clutter, the cone of silence, sensitivity and operational status. It is labeled as modeled everywhere it appears and is not FAA coverage. Terrain comes from [Terrain Tiles on AWS](https://registry.opendata.aws/terrain-tiles/) (USGS 3DEP, SRTM, GMTED2010, ETOPO1): about 1,300 tiles cached in `data/terrain` (gitignored) and checksummed in `data/coverage/terrain-manifest.json`. A rebuild from the cache takes about 40 seconds; `npm run data:update` reruns it after each release.

### Updating to a new FAA release

FAA publishes NASR every 28 days (2026-10-01, 2026-10-29, 2026-11-26, …). Run `npm run data:update` on or after an effective date. It does nothing when the retained cycle is current. Otherwise it fetches the release, refreshes FAA chart boundaries, rebuilds `public/data`, updates the dated counts in this README, runs `npm test` and writes `data/releases/<cycle>.md`. The report lists records added, removed and changed per layer, with old → new values; records whose FAA key changed (an ILS upgraded to ILS/DME, a renumbered runway) appear as one change. Nothing is committed: review the report and `git diff`, run `npm run test:browser`, then commit. If any step fails, the previous raw files, build, manifests and README are restored. The superseded raw release stays in `data/raw.previous` until the next update.

`--check` only reports whether a newer cycle is posted. `--upcoming` adopts the next cycle as soon as FAA posts it, before it takes effect. `--cycle YYYY-MM-DD` selects a specific release. `--keep-boundaries` skips the boundary refresh. Supplemental evidence (JPL, Lincoln Laboratory, FAA directories, NTSB) is carried forward unchanged; its matching against new NASR records is re-run, so review report entries for matched radars.

`npm run data:boundaries` refreshes FAA chart polygons and their independently dated source manifest. `npm run data:acquire` stages the pinned FAA files, validates ZIPs and retains independent supplemental evidence when replacing the NASR raw directory. `data:build` validates NASR, supplemental, and boundary manifests before normalization. Refresh supplemental evidence deliberately with updated files, review source dates and matching decisions, then regenerate its checksums. Do not change inventory dates solely because a file was downloaded again.

`public/data/catalog.json` supports search; per-category files load full attributes lazily. `facilities.json` preserves source keys, null positions, original coordinates, attributes and provenance. `audit.json` reports coverage and limitations. The UI links both source manifests and the audit. Tests cover coordinate bounds, source integrity, Mt. Tam, NCT accuracy, Reno antenna coordinates, model search and desktop/mobile satellite/source interactions.

This independent atlas is not an FAA product or a navigation tool.


Airport towers have a dedicated layer: all 723 current US ATCT and combined ATCT facility records are retained with exact FAA facility types. Approach/departure-provider associations come from NASR, including SFO → NCT. Tower records without published equipment coordinates use labeled FAA airport reference markers when the airport identity and NASR site number match.

Nationwide surveillance coverage retains all 369 US NASR RDR records, alongside AFF and NASA/JPL radar records. Model types remain unknown when the sources do not specify them. The FAA [ASDE-X deployment list](https://www.faa.gov/air_traffic/technology/asde-x) supplies all 35 listed airports (2023-09-07), and its [ASSC deployment list](https://www.faa.gov/air_traffic/technology/adsb/atc/assc) supplies all nine (2024-05-24), including SFO. These are multi-sensor systems, not single located radar antennas. Deployment pages describe system architecture but do not publish each airport's sensor inventory or coordinates. Airport reference markers are explicitly labeled as airport context, not antenna positions. Retained FAA pages are checksum-validated with the supplemental sources. This is nationwide source coverage, not a claim that every physical radar installation has been located.

Airport-reference markers now make documented ATCT, airport ASR/PAR, ASDE-X and ASSC deployments visible even when precise equipment coordinates are absent. The marker and detail identify the FAA airport reference point; `equipment_geometry` remains null. Tower and surface-system symbols sharing a reference point have separate pixel anchors so both remain clickable. This applies nationwide, including SFO, without changing source coordinates.
