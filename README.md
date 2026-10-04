# Airways Atlas

A map workspace for public US aviation infrastructure. Radar and control facilities are the default view. Exact documented equipment types appear in the catalog and inspector; satellite imagery is available in the Map / Satellite switch and each located facility's inspection button.

## Run and verify

```sh
npm install
npm run dev
npm run data:build
npm test
npm run test:browser
npm run build
```

Vite serves localhost:5173; the static production build is `dist/`. No deployment is configured.

## Sources and reliability

FAA NASR cycle **2026-10-01** is the primary inventory. Retained originals and SHA-256 hashes are in `data/raw/manifest.json`. The dataset contains **11,633 normalized records**, **10,495 mapped**, and **1,138 unlocated**. Counts are records, not established unique installations or a complete national inventory.

Supplemental evidence is retained and hash-checked separately in `data/supplemental/manifest.json`:

- [NASA/JPL FAA long-range radar inventory](https://uavsar.jpl.nasa.gov/kml/FAA_LongRangeRadars.kml): 93 US/territory sites. Site coordinates come from descriptions, not decorative polygon geometries. The publication date is unknown.
- [FAA-sponsored MIT Lincoln Laboratory ATC-425](https://www.ll.mit.edu/sites/default/files/publication/doc/2018-05/Cho_2015_ATC-425.pdf): 2015-05-26 long-range equipment inventory, distinguishing ARSR-4 and CARSR-program sites. CARSR entries retain their original legacy type. Current conversion and operational status are not certified.
- [FAA-sponsored ATC-450](https://www.ll.mit.edu/sites/default/files/publication/doc/radar-coverage-analysis-terminal-precipitation-glass-program-cho-atc-450.pdf): 2022-03-04 terminal models, including ASR-8/9/11, and explicitly documented NCT sensor associations. The retained filename contains 2021, but the report and displayed evidence date are 2022.
- [FAA service-center directory](https://www.faa.gov/sites/faa.gov/files/service-center-list-12.19.23.pdf): 2023-12-19 facility addresses. Seven successful US Census geocodes, including NCT, are visibly **approximate street-range address estimates**, not surveyed facility or antenna positions. Failed matches remain unlocated.
- [FAA NFDD 056](https://aeronav.faa.gov/aero_data/NFDD/nfdd-2025-03-25-56.pdf): 2025-03-25 OAK and NUQ antenna positions quoted in a removed procedure remark. Removal reflects documentation requirements; it does not establish installation removal or current equipment status.
- [NTSB WPR16FA172 ATC factual report](https://data.ntsb.gov/Docket/Document/docBLOB?FileExtension=.PDF&FileName=Air+Traffic+Control+Group+Chairman%27s+Factual+Report-Master.PDF&ID=40464366): 2017-11-02 Reno ASR-11 antenna position; the 2022 equipment inventory separately corroborates its model.
- [DOT/FAA QMV procurement forecast](https://www.transportation.gov/procurement-forecast-opportunity/procurement-forecast-opportunity-673706-1-facilities-security): 2024-09-03 identity corroboration for the Mill Valley radar site.
- [Radomes.org Mill Valley history](https://www.radomes.org/museum/showsite.php?site=Mill+Valley+AFS%2C+CA): clearly labeled community evidence for Mt. Tam's historical aliases. Its coordinates and primary model evidence come from the government inventory and FAA-sponsored research.

Every facility carries field-level sources with publisher, document link, evidence fields and dates. Location and model dates remain separate from the NASR release. An older documented model is never presented as confirmed live equipment. Radar or control records without corroborated coordinates remain searchable; airport centroids are not substituted. Historical and current records may overlap across source tables; cross-table installation reconciliation is incomplete.

The map renders 54 **partial** ARTCC boundary variants. Unsupported arcs, national-border instructions and antimeridian segments are omitted. No radar coverage or responsibility is inferred from distance.

## Interaction and data workflow

Search names, identifiers, models, aliases and published associations across all layers. Without a search, selected layers control browsing. State and exact type filters apply in both cases. Mapped-only is optional; unknown locations remain visible by default. NCT details retain the seven sensor identifiers explicitly listed in ATC-450 and link matched records. Clicking an ARTCC opens its complete published association list across all layers and states, including unlocated systems. Ordinary filters are paused in this view; its search searches associated systems. Center boundaries appear automatically, with a thick colored line and contrasting casing on map and satellite imagery. Boundary lines are clickable. Selecting an associated system retains center context; Exit center systems restores browsing. The map still samples at most 150 marker elements per viewport. An ≈ annotation identifies approximate facility address estimates. Unclustered SVG symbols show individual facilities, with centered navigation diamonds and no circular icon containers. At most 150 map marker elements are mounted, including selection brackets. Each pan, zoom, resize or filter change recomputes a spatially distributed sample of viewport facilities; zooming in reveals more detail. Existing markers are retained when possible. The complete results list remains searchable, and a map count indicates when locations are hidden.

Mobile has Map / Facilities tabs and a dismissible facility inspector. `/` focuses search; Escape closes details. Filters, region, basemap and selected facility persist in the share URL. Map tiles and optional fonts require network access; data and tile failures have separate messages.

`npm run data:acquire` stages the pinned FAA files, validates ZIPs and retains independent supplemental evidence when replacing the NASR raw directory. `data:build` validates both manifests before normalization. Refresh supplemental evidence deliberately with updated files, review source dates and matching decisions, then regenerate its checksums. Do not change inventory dates solely because a file was downloaded again.

`public/data/catalog.json` supports search; per-category files load full attributes lazily. `facilities.json` preserves source keys, null positions, original coordinates, attributes and provenance. `audit.json` reports coverage and limitations. The UI links both source manifests and the audit. Tests cover coordinate bounds, source integrity, Mt. Tam, NCT accuracy, Reno antenna coordinates, model search and desktop/mobile satellite/source interactions.

This independent atlas is not an FAA product or a navigation tool.
