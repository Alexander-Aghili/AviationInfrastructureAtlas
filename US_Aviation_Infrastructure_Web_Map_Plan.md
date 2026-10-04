# US Aviation Infrastructure Web Map Build Plan

Implementation guide | 2 October 2026

## Goal

Build an independent interactive map of publicly documented US aviation infrastructure: radar installations, ground navigation aids, instrument landing equipment, air traffic control facilities, communications sites, and aviation weather stations. Visitors can toggle layers, search by identifier or location, inspect facilities, and explore published relationships with Air Route Traffic Control Centers (ARTCCs).

Use FAA datasets as the primary source. Map physical equipment locations, control facility locations, airspace boundaries, and published surveillance coverage as distinct feature types. Measure dataset coverage before claiming a complete inventory. The map displays published information as of a stated effective date; it is not a live equipment-status or outage service.

## Recommended first release

Start with ground navigation aids, published radar sites, ARTCC facilities, ARTCC boundaries, and remote communications sites. Add landing-system components, towers and approach facilities, aviation weather stations, and published surveillance coverage as their source schemas are validated.

Use a responsive map with clustered points, an identifier search, a layer selector, a results list, and a facility details panel. Clicking a marker opens its details. Source links open in a new tab. Selecting an ARTCC highlights its published boundary and associated facilities wherever the source explicitly establishes that relationship.

## Primary FAA data sources

| Layer | NASR group | Extraction purpose |
| --- | --- | --- |
| Ground navigation aids | NAV | Navigation aid identifiers, facility types, coordinates, and published attributes |
| Instrument landing equipment | ILS | Landing-system components and their individual locations where provided |
| Radar installations | RDR and AFF | Radar records and en-route or secondary radar sites |
| ARTCC facilities | AFF or documented CSV successor | Physical center locations and associated facility records |
| ARTCC boundaries | ARB | Published boundary coordinates and descriptions |
| Communications sites | COM, FRQ, AFF | Remote communications facilities and published frequency associations |
| Towers and approach facilities | ATC and legacy TWR | Published control facility and communications records |
| Aviation weather stations | AWOS and WXL | Weather reporting locations and attributes |

The FAA NASR index identifies the cycle effective 1 October 2026 as current at the time of planning. It also announces format changes effective with the 3 September 2026 cycle. Use the layouts and mappings shipped with the selected cycle rather than assuming older field positions or table names remain valid.

The inspected AFF layout includes ARTCC, Air Route Surveillance Radar (ARSR), secondary radar (SECRA), Remote Communications Air/Ground (RCAG), and Center Radar Approach Control (CERAP) facility types, with site latitude and longitude. These records are useful for both facility points and explicit center associations. Inspect the current equivalent before implementing the parser.

## Data model

Separate physical sites, equipment or service records, organizational associations, frequencies, boundaries, and coverage layers. Several devices or services can share one site, and one radar may serve multiple centers. Preserve these relationships without counting each association as a new installation.

| Field | Purpose |
| --- | --- |
| feature_id and source_key | Stable map identity and original FAA record identifier |
| site_id and equipment_id | Physical site grouping and equipment identity where supported |
| name, identifiers, aliases | Display name, FAA or ICAO identifiers, and alternative names |
| feature_type and subtype | Radar, navigation aid, communications, control facility, weather station, or boundary |
| geometry and coordinate_role | WGS84 geometry plus equipment location, facility reference point, boundary, or published coverage |
| owner_or_operator | Published ownership or operating organization where available |
| relationships | Explicit associations with centers, airports, runways, or other facilities |
| attributes | Frequencies, channels, elevation, equipment type, status, and remarks where actually published |
| source and effective_date | Dataset, table, record locator, cycle, and retrieval timestamp |
| quality and review_notes | Missing values, coordinate interpretation, conflicts, and review decisions |

Retain original coordinate values, units, precision, and datum information. Do not use a nearby airport reference point as the location of a radar antenna, localizer, glide slope, or tower without labeling that substitution. Store unknown coordinates as null and retain the record in the results list.

## Step by step implementation

### Step 1  Acquire one coherent FAA publication cycle

Resolve the current NASR cycle from the official index and download its data, README, layouts, and legacy-to-CSV mapping. Retain the original files and a manifest of URLs, effective dates, retrieval times, and checksums. Prefer CSV groups where they contain the needed information. Use fixed-width or AIXM files when required, with a parser matched to their documented version.

Avoid mixing cycles across layers without recording the difference. Inventory all required groups and flag missing or failed downloads. Treat source formats and effective dates as part of the dataset, not incidental metadata.

### Step 2  Inspect representative records and schemas

Select a navigation aid, terminal radar, en-route radar, ARTCC building, RCAG site, and boundary example. Check each record against its official field definitions. Establish which coordinates identify equipment, a facility reference point, an associated airport, or a boundary vertex. Confirm that identifiers, types, units, and optional values are interpreted correctly.

Inspect the scope of RDR and AFF separately before combining them. Do not assume the radar dataset alone contains every en-route radar, or that a record’s associated airport coordinates identify the radar installation. Document coverage gaps and table mappings.

### Step 3  Normalize facilities and coordinates

Convert documented coordinate representations to decimal degrees and WGS84 where an appropriate datum transformation is known. Support hemisphere signs, degrees-minutes-seconds, and seconds-of-arc representations. Validate numeric ranges and GeoJSON order [longitude, latitude]. Preserve source values for troubleshooting.

Create typed records with stable source keys. Normalize identifiers without discarding distinctions between FAA and ICAO codes. Attach published frequency units and elevation reference information. Interpret status fields according to their definitions; do not infer live operability from a publication record.

### Step 4  Reconcile sites and relationships

Merge repeated representations only when identifiers or supporting evidence establish they refer to the same equipment or physical site. Nearby points alone are insufficient. Preserve co-located navigation components and multiple equipment types as distinct equipment records within a site group.

Use explicit center and airport associations to build relationships. A point inside an ARTCC polygon can be labeled geographically within that area, but that does not establish ownership or service responsibility. A radar shared by centers should retain multiple relationships. Keep unassociated facilities rather than forcing a match.

### Step 5  Build boundary and coverage geometries

Parse ARTCC boundary descriptions using their documented ordering and geometry rules. Preserve distinctions between altitude-dependent or other boundary variants if provided. Validate rings, disconnected components, and antimeridian crossings. Do not replace curved boundary segments with unsupported straight lines; use a documented approximation when conversion requires one.

For an optional coverage layer, obtain the FAA’s published estimated ADS-B and secondary surveillance radar coverage files. The FAA AIP describes selectable coverage at several heights, including 500, 1,500, 3,000, 5,000, and 10,000 feet AGL, with additional Alaska options. Verify the available download’s date and altitude reference. Coverage is an estimate from the published model, not a real-time guarantee.

Do not generate coverage by drawing a fixed-radius circle around every radar. Keep coverage estimates, regulatory ADS-B airspace, and control boundaries separate, with distinct labels and legends. If the current published coverage download cannot be obtained or validated, release the facility map first and mark coverage as pending.

### Step 6  Build the exploration interface

Use a static frontend with a web map renderer such as MapLibre GL JS or Leaflet. Generate versioned GeoJSON and normalized metadata from the ingestion pipeline. Load layers on demand; introduce vector tiles only if measured data size or interaction performance warrants them. Choose a basemap provider compatible with expected traffic and display its required attribution.

Provide layer toggles, subtype filters, state or region filters, search by name and identifier, and a visible result count. Include Alaska, Hawaii, and territories with clear navigation controls. Cluster crowded points and expand co-located equipment through a selectable site list. Make the result list and detail panel usable on mobile and by keyboard.

### Step 7  Implement facility details and center selection

On marker selection, display the facility name, identifiers, type, coordinate role, published attributes, associated center or airport, remarks, source, and data effective date. Label absent information as unknown rather than filling it from assumptions. Link to a verified facility-specific FAA page when available; otherwise link to the publication and show the record identifier so the source is traceable.

Selecting an ARTCC highlights its physical facility point, published boundary, and explicitly associated radar or communications sites. Optional relationship lines represent documented associations, not cable routes, network topology, or radio coverage. Selecting a landing system should expose individual components where coordinates are supplied.

### Step 8  Add optional coverage and cycle comparison controls

Provide an altitude selector only for coverage variants actually supplied by the source, with AGL or MSL clearly identified. Show source date and method notes beside the legend. Retain a way to view facility locations without coverage overlays.

For publication comparisons, retain two or more cycles and match records using stable identifiers. Highlight added, removed, moved, or changed records. A record removed from NASR means it was removed from that publication; review supporting evidence before calling the facility decommissioned or demolished. Report schema changes separately from equipment changes.

### Step 9  Validate the dataset and interface

Report records imported per source, mapped and unlocated counts, unique equipment and site counts, duplicates, unresolved associations, and geographic outliers. Test representative coordinates against the official source and available imagery. Verify distinct equipment and associated-airport coordinate fields, hemisphere signs, units, and missing values.

Test boundary validity, coverage altitude labels, Alaska and Pacific geometries, shared radar associations, multiple devices at one site, and search identifier aliases. Confirm layer filters, counts, links, cluster expansion, keyboard navigation, mobile layout, and loading failures. Review selected ARTCC relationships against the original records. Do not declare inventory completeness merely because all downloads parsed successfully.

### Step 10  Publish and maintain

Deploy the app with one validated dataset release, a clear effective date, source attribution, coverage notes, and a correction route. Keep the last successful release for rollback. Refresh imports when new NASR cycles become available, validate schema compatibility, compare records, and review unexpected changes before publishing. A failed update leaves the existing release intact.

Future maintenance can follow the FAA’s 28-day publication cadence. This plan does not itself create or schedule an automation. Historic views are limited to the snapshots actually retained; do not imply that a facility’s original installation date can be inferred from its first appearance in the collected snapshots.

## Release sequence

1. Validate a representative sample and establish coordinate roles and stable identifiers.
2. Publish navigation aids, radar, ARTCC locations and boundaries, and remote communications sites.
3. Add landing equipment, tower and approach facility records, and aviation weather stations after schema validation.
4. Add published altitude-dependent surveillance coverage where current files can be obtained and verified.
5. Introduce publication-cycle comparisons after multiple validated snapshots are retained.

## Official starting references

- [FAA NASR subscription index and current cycle](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/)
- [Inspected NASR group listing for the August 2026 cycle](https://www.faa.gov/air_traffic/flight_info/aeronav/aero_data/NASR_Subscription/2026-08-06/)
- [Inspected ARTCC facilities and communications layout](https://nfdc.faa.gov/webContent/28DaySub/2026-08-06/Layout_Data/aff_rf.txt)
- [Inspected navigation aids layout](https://nfdc.faa.gov/webContent/28DaySub/2026-08-06/Layout_Data/nav_rf.txt)
- [FAA AIP surveillance coverage description](https://www.faa.gov/air_traffic/publications/atpubs/aip_html/part2_enr_section_1.6.html)
- [FAA public data portal](https://www.faa.gov/data)

Use the inspected August layouts as evidence of available fields, then obtain the layouts for the actual selected release cycle before writing import code.
