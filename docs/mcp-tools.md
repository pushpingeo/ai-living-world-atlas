# What Tobler relies on (the MCP contract)

Tobler (github.com/pushpingeo/tobler) uses the atlas through the MCP server at
`https://atlas-mcp.robdunfey.workers.dev/mcp`, reached from Tobler's own Worker by a service binding.
The Tobler and atlas chats work separately, so this page is the agreement between them: the atlas chat
keeps everything listed here working, and changes or removes any of it only after a note under
"Requests and changes" below. New, optional parameters can be added freely.

## Tools and fields Tobler uses

**`find_datasets`**
- Inputs: `lon`, `lat`, `radius_km` or `bbox` [w, s, e, n]; `concept` (vocabulary id); `capability: "query"`;
  `geometry` (`point` | `line` | `polygon`; datasets with unknown geometry are kept); `limit` (Tobler asks for 100).
- Behaviour: national publishers' datasets are left out when their country doesn't touch the area
  (`include_other_countries` widens it). Tobler depends on this to keep foreign layers out.
- Outputs read per result: `id`, `title`, `publisher`, `publisher_type`, `coverage`, `licence`,
  `extent_may_be_overstated`, `geometry` (list), `country`. Top level: `matches`, `results`.

**`fetch_features`**
- Inputs: `id`; `lon`, `lat`, `radius_km` or `bbox`; `limit` (50–100); `text` (name-like fields, server-side on
  ArcGIS, filtered after fetching on others).
- Outputs read: `returned`, `features` (GeoJSON in WGS84 with properties).
- WFS requests must keep giving the bbox in CRS84 (fixed 17 Nov; without it, layers in a national grid came back empty).

**`vocabulary`**: used by diagnostics only.

Concept ids Tobler maps to (in `js/atlasfeatures.js`): power-plant, mineral-extraction, oil-gas, port-airport,
settlement, school, health-facility, greenspace, tourism-recreation, road, rail, river, pipeline, power-line,
protected-area, heritage-site, admin-boundary, maritime-boundary, offshore-wind-site, renewable-potential.
Renaming or removing one of these breaks a Tobler search.

## Requests and changes

Newest first. Tobler's chat adds requests here; the atlas chat marks them done or declined.

- (24 Nov evening, **England's current pollution, storm overflows, England Peat Map**) Additive. Same fields as the UK
  packs (`nation`, `completeness`, `completeness_note` in endpoint details).
  - **3 hosted EA files** (wave `spike-files`; `vocab/files/ea-*.yaml`), fetched like the GEM and JNCC files
    (`fetch_features` reads the 1° tiles near the area; `where` isn't supported on hosted files):

    | Record | Id | Features |
    |---|---|---|
    | Industrial installation permits, England | `e96296234c630eca` | 6,333 (in force and ended; superseded versions left out) |
    | Waste site permits, England | `81ad43b046380b3d` | 19,092 (in force and ended) |
    | Serious pollution incidents (Category 1 and 2), England, 2001 to date | `d4e38afd394a1bf4` | 17,507 |

    Status fields: `Status` (Effective = in force) on installations, `STAT_SDESC` (Issued = in force) on waste sites;
    activity in `primary_activity` / `activities` and `licence_type`. Incidents: `EIL_WATER`, `EIL_LAND`, `EIL_AIR`
    (Category 1 to 4), `pollutant_types`, `pollutants`, `NOT_DATE`. **Licence:** EA Conditional Licence, `open_licence`
    false, accepted by Rob for screening (in `terms`). **Operator and holder names, contacts and street addresses are
    not in the copy** (some are private individuals). Refreshed monthly (3rd of the month); `details.data_date` is the
    download day. Say on a report that an incident near a site doesn't mean its owner caused it.
  - **13 curated records** (wave `spike-ukwaterpeat`, `vocab/seeds/uk-water-peat.yaml`; keyword `uk-water-peat-pack`):

    | Record | Id | Completeness |
    |---|---|---|
    | Storm overflows live: Anglian `590f8c58e1f154eb`, Wessex `44d4446b579eae51`, Severn Trent `ba844827cc3cfa78`, Yorkshire `834984471176a754`, South West `59dc11dc3b75f3ee`, United Utilities `69c7a58eed102b4f`, Northumbrian `8b2942f395985f0c`, Thames `4ae36af79367ade1` | | **partial** (each company's own area; no live layer for Southern or Welsh Water) |
    | Storm overflow spills in 2025, England and Wales (annual returns, all 11 companies) | `4123e7d7391d4cbd` | complete for 2025 |
    | Storm overflows live, Scottish Water (Rivers Trust copy, **not open**) | `e80013b64da35b0d` | complete for monitored overflows |
    | Peaty soil extent, England | `9c44057149e34495` | complete (modelled) |
    | Peat presence and depth observations, England | `202e4d558bbf7718` | **partial** (where surveyed) |
    | Peatland restoration register, England | `3a350525aee8b4cc` | **partial** (national schemes) |

    Live storm overflow `Status`: 1 discharging now, 0 not, -1 monitor offline (South West Water's fields are lower case:
    `status`). For "how often does it spill", use the annual returns' `countedSpills` and `totalDurationAllSpillsHrs`.
    Licences: water companies CC BY 4.0, annual returns and peat OGL. `terms` on the peat observations: leave out
    `surveyor` (names people).
- (24 Nov afternoon, **US done**) **US contamination screening: EPA's national layers.** Additive. Same fields as the UK
  packs: `details.nation` ("United States"), `completeness`, `completeness_note`.
  - **10 new records** (wave `spike-uscontamination`, `vocab/seeds/us-contamination.yaml`), ids fixed; keyword
    `us-contamination-pack`. All public domain (`open_licence` true), attribution "U.S. Environmental Protection Agency".

    | Topic | Record | Completeness |
    |---|---|---|
    | Superfund NPL boundaries (polygons) | `5e0e98fb5909b1e1` | complete (EPA's federal list) |
    | Superfund NPL sites with status (points) | `c38ed5a534806b6f` | complete |
    | All Superfund sites, NPL and non-NPL (SEMS) | `a1a721163c4fb225` | complete |
    | Brownfields with EPA grant funding (ACRES) | `85b4bdc7c49e5055` | **partial**: only EPA-funded properties |
    | RCRA corrective action boundaries | `8427fb0a7235a865` | **partial**: only EPA Regions 1, 3, 4, 7, 10 (no Texas, California, Great Lakes, Southwest) |
    | Toxics Release Inventory facilities | `287038202610ca08` | complete (above the TRI thresholds) |
    | Air emission sources (ICIS-Air) | `41198ffb356b4b40` | **partial**: many minor sources are state-only |
    | Major water discharge permits (NPDES major) | `33493d9c2306128a` | complete |
    | All water discharge permits (NPDES, 1.9M points) | `85a67d0fcb04bf97` | complete; small boxes only |
    | Hazardous waste treatment, storage, disposal (RCRA TSD) | `07c5b1364a229296` | complete |

  - **How to read them.** "Complete" here means complete for EPA's federal programme. State cleanup sites aren't in any
    of these, so say "none in EPA's national records", not "none". NPL status: `Status` (NPL Site, Deleted NPL Site,
    Proposed NPL Site) on the points; `NPL_STATUS_CODE` (F, D, P, N, R...) on the boundaries. SEMS: `INTEREST_TYPE`
    SUPERFUND NPL or SUPERFUND (NON-NPL); a non-NPL record means EPA looked at the site, not that it is contaminated.
    Air: `where: "INTEREST_TYPE='AIR MAJOR'"` for large sources. FRS points carry `ACCURACY_VALUE` and `FAC_URL`.
  - **Personal data:** the RCRA boundaries carry facility contact names, emails and phones; `terms` says leave them out.
  - **Not curated:** EPA's 900k RCRA hazardous waste handlers (too broad for a screen), Cleanups in My Community
    (overlaps these), state lists (`concept: "contaminated-land"`, partial). The crawled EPA copies of some of these
    still exist under other ids; use these.
- (24 Nov afternoon, **step 2 done for Scotland, Wales and NI; England waits on Rob**) **UK contamination screening:
  current pollution.** Additive. Same fields as step 1 (`nation`, `completeness`, `completeness_note` in endpoint details).
  - **6 new records** (wave `spike-ukpollution`, `vocab/seeds/uk-pollution.yaml`), ids fixed; keyword `uk-pollution-pack`.

    | Topic | England | Wales | Scotland | Northern Ireland |
    |---|---|---|---|---|
    | Permitted sites | (download only: see gaps) | installations `44f83dc4a6a75e38`, waste sites `2301597b68920a17` (NRW) | all granted authorisations `b32daeca2c368112` (SEPA) | trade discharge consents `2abb7782c0d51447` (DAERA) |
    | Pollution incidents | (download only) | (download only) | (none found) | confirmed incidents per 1 km square, 2011-2024, `ca262452381e06c6` (DAERA) |
    | Past land use (step 1 gap) | – | – | – | Historical Land Use Database `ecea8189ad7c042f` (NIEA, ~14,600 sites) |

  - **How to read them.** SEPA: 120k points, mostly small water registrations (septic tanks); for pollution sources use
    `where: "regulatory_area IN ('Industrial Activities','Waste','Radioactive Substances')"` or filter on
    `authorisation_level` (PPC Part A, PPC Part B, Waste Management Licence...). NRW installations: `Primary_activity_desc_en`;
    NRW waste: `Operational_status` (Operational, Closed, Pre-Operational). DAERA incidents: only squares with an incident are
    in the layer, so a square that isn't there had none confirmed; `totals`, per-year `y2011`...`y2024`, source and severity
    fields. DAERA consents: `app_status` includes revoked and historic consents (`cons_type` "Trade (Historic)"), so filter
    on it. NI land use: `Descriptio` is the past use, `DBID` the source list; a list of past uses, not of contamination.
  - **Licences.** Open (OGL): SEPA, DAERA incidents, NI land use. Not open: NRW's permits (NRW licence only, like its
    landfill), DAERA consents (no licence stated). **Personal data:** SEPA's `authorisation_holder` and NRW's `Operator`
    include private individuals; `terms` says leave them out.
  - **Licence decisions (Rob, 24 Nov):** radon `3f1f871836efd2da` is now `open_licence` true (accepted as OGL). EA landfill
    (`3a4c49302d01deb3`, `7c9fa9e8c48a162a`) stays `open_licence` false, because the Conditional Licence isn't an open
    licence, but its `terms` now say it's accepted for screening use on those terms (site names and dates, no personal
    fields; re-read by Nov 2027).
  - **Speed, live 24 Nov:** 0.4-1.1 s per fetch_features.
  - **Gaps (report as "not checked"):** England's permits, pollution incidents and Pollution Inventory exist only as
    Environment Agency ZIP downloads, not services (the Pollution Inventory's licence allows internal use only, so it
    won't be added); SEPA's Pollutant Release Inventory is a 2018 shapefile only; NRW's pollution incidents are a download;
    Scotland has no incident layer; Defra's national AQMA map needs a token, so AQMAs come only from councils that publish
    their own (`concept: "air-quality-area"`, partial). Wales's permit layers were last edited December 2023.
- (24 Nov, Tobler reply `claude/contamination-tobler-reply.md`, **step 1 done**) **UK contamination screening:
  old sources and receptors.** Additive. Step 2 (current pollution: permits, release inventories, incidents, AQMAs)
  comes next.
  - **16 new records** (wave `spike-ukground`, `vocab/seeds/uk-ground.yaml`), ids fixed; keyword `uk-ground-pack` lists
    them all.

    | Topic | England | Wales | Scotland | Northern Ireland |
    |---|---|---|---|---|
    | Historic landfill | `3a4c49302d01deb3` EA | `69871d2785dc1d1b` NRW | (no national layer) | (none found) |
    | Authorised landfill | `7c9fa9e8c48a162a` EA | `98ddbba3cb0b50f8` NRW | (SEPA permits: step 2) | (none found) |
    | Coal mining risk | `ec38ddbef814026b` high risk, `73e7225df3f929e7` low risk (Mining Remediation Authority, GB-wide) | same | same | (not covered) |
    | Closed mining waste | `7719defbb5b780ef` EA | `4f4d8e01d0678a76` NRW | – | – |
    | Source protection zones | `6c3e0babf56f294e` EA | `5d4037034edc4d37` NRW | (none in this form) | (none in this form) |
    | Radon | `3f1f871836efd2da` UKHSA, whole UK and Isle of Man | | | |
    | Council records (**partial**) | Derby `5ef41092de2010de`, Lambeth `164c454dced356b7` and landfill `ac1475ee668c32b4`, Sheffield register `8d25d1f7b39def53` | – | Clackmannanshire `e310e4158da08197` | – |

  - **New field on every curated UK record (85: these 16 plus the 69 of 22-23 Nov):** `get_dataset`
    `endpoints[].details.nation` (England, Scotland, Wales, Northern Ireland, "England, Scotland, Wales", UK),
    `details.completeness` (`complete` or `partial`) and `details.completeness_note`. **This is what Tobler's reply called
    "coverage".** It's named completeness because dataset details already have `coverage`, which means extent size
    (local, regional, national...). `complete`: an empty answer means none in that nation. `partial`: silence never means
    none. Partial today: the 5 council layers, and England's post-1988 ALC (surveyed sites only).
  - **Class values, read live 24 Nov** (also in `details.class_values` where listed):
    - EA SPZ `number`: 1 (2,478), 1c (217), 2 (1,370), 2c (200), 3 (403), 3c (2), 4 (16). "c" = confined aquifer
      (subsurface activity only); 4 = zone of special interest. NRW SPZ `NUMBER`: 1, 2, 3 (integers).
    - Radon `CLASS_MAX` 1-6 per 1 km square: 1 under 1% of homes at or above the Action Level; 2 = 1-3%; 3 = 3-5%;
      4 = 5-10%; 5 = 10-30%; 6 = over 30%. `Advice` says "Radon measurement is advised" from class 2. Not for basements.
    - Coal mining `FEATURE_TY`: one value per layer ("Development High Risk Area - Subject to Change"); presence is the
      answer. Outside both layers: no recorded coal mining risk (coal only; metal mines and other workings aren't in it).
    - EA authorised landfill `status`: Effective, Issued, Closure, Expired, Expired (Inactive), Part Suspended.
      EA historic landfill `inert`: Yes (11,107), Y (2), blank (8,697).
  - **Licences, verbatim with where they were read.** Open: coal high risk area (OGL), both SPZ layers (OGL), NRW closed
    mining waste (OGL). **Not open, each for a reason:**
    - **EA landfill (both):** Environment Agency Conditional Licence. It allows commercial use, but this dataset's terms limit
      it to one year at a time and the data holds personal data (licence holders' names and addresses: `lic_hold`,
      `licholdadd`, `lic_name`). Show site names and dates; leave the personal fields out (`terms` says so).
    - **NRW landfill (both):** NRW says on data.gov.uk that it doesn't grant re-use of the full dataset (a redacted version
      under an NRW licence). NRW's ArcGIS item says OGL for historic landfill; they disagree, so not open.
    - **Radon:** unsettled. UKHSA's current item states no licence, its 2015 copy says OGL, and the underlying BGS data is
      under BGS's own licence. **Superseded the same afternoon: Rob accepted it as OGL, so it is now open.**
    - **Coal low risk area, EA closed mining waste:** no licence stated.
    - **Council layers:** no licence stated; Sheffield's is the OS INSPIRE end user licence.
  - **Speed, live 24 Nov:** 0.3-5.8 s per fetch_features (Lambeth and the coal low risk area slowest). Clackmannanshire's server takes ~20 s; radon has 254k squares
    (keep boxes small).
  - **Gaps (report as "not checked"):** no national historic landfill or contaminated-land layer for Scotland or Northern
    Ireland; no source protection zones in Scotland or NI in this form; NI has no coal mining risk layer; Carlisle publishes
    a layer but refuses the atlas's checks; York's register layer holds only a "test data" placeholder, so it was left out; most councils publish nothing. Historic land use (old maps) is not open data.
  - **New concepts** (all datasets re-tagged where relevant, 24 Nov): `contaminated-land`, `landfill`, `mining-legacy`,
    `groundwater-protection`, `pollution-source`, `air-quality-area`. `brownfield` now means land registers only; `waste`,
    `water-quality` and `air-quality` are narrower. `find_datasets` with `concept: "contaminated-land"` is the way to find
    council and state records anywhere.

- (23 Nov, Tobler request, **done**, live 23 Nov 23:55 UTC) **The UK pack, broadened: landscape, heritage, peat, farmland
  quality, flood zones and the SSSI Impact Risk Zones.** All additive (one additive field, `type_name`, below).
  - **45 new records** (wave `spike-ukpack`, `vocab/seeds/uk-pack.yaml`), each on the designating or publishing body's own
    service, ids fixed. Their keywords include `uk-screening-pack`, so `find_datasets` with `text: "uk-screening-pack"` and
    a UK box lists all 45 (checked live).

    | Topic | England | Scotland | Wales | Northern Ireland |
    |---|---|---|---|---|
    | National Parks | `e6b26569ae936cbc` | `2c64c45082dde4d4` Cairngorms, `31c64df372cb3cc8` Loch Lomond & Trossachs | `b92f5c5c3588e51d` | (none exist) |
    | National Landscapes (AONBs) / NSAs | `516acf7fb62329d4` | `cab9ecdbc9a0d348` NSAs | `c36dc458130de6ad` | `e592ebe2d66ea421` AONBs |
    | Other landscape | | `e3aaad523213b9e5` Wild Land Areas | `59dcdad44dc244ad` Special Landscape Areas (local plans, collated by NRW); `f4a9ac905085b8bb` Registered Historic Landscapes | |
    | Listed buildings | `983f6d4fe0ad19b7` | `11286ed717adf1b6` | `80195c0f4b64266b` | `f88428f3ab779e89` (filter, see below) |
    | Scheduled monuments | `3ab45d9b3f6c7b62` | `a6136b469d7f05be` | `2a620f0931d8f136` | `bd19212dd9c5657b` scheduled zones |
    | Parks and gardens | `cb837def8797354a` | `34e3e976f1938536` Inventory GDL | `72b425ef6d5c8d27` | `950ab4ea78ffb5d6` |
    | Battlefields | `eeddb3a335fe89ac` | `f4cbbfd5efdb9163` Inventory | (no layer found) | `94d72c520a2f4a38` (not statutory) |
    | World Heritage Sites | `88dd85f584df67eb` | `0d622d81aa3431a4` | `4af8b44459c04866` | `916bd027a2130550` |
    | Peat | | `c083949b58058a10` Carbon and Peatland 2016 (**not open**, see below) | | |
    | Farmland quality | `13092572fa28c747` provisional ALC; `5e7c583217c03078` post-1988 ALC | `339b7b656d0df917` LCA 1:250k (**licence not OGL**) | `ad19381cfa5083b1` predictive ALC v2 | (none found) |
    | Flood zones | `5ffe9c81924b8082` FZ2 and FZ3, rivers and sea | SEPA: river `f267f1d11983d686` medium, `e65fa9c5834c9d96` low; coastal `b998a526249919d6` medium, `53dde745af4ecbd8` low; surface water `874a454456a0df96` medium | NRW Flood Map for Planning: rivers `9474dd68603a995c`, sea `56805a5239c6052a`, surface water `75b9c6058f651588` | (none found) |
    | SSSI Impact Risk Zones | `05ca97cc51458e33` | | | |

  - **`get_dataset` endpoint details** (`endpoints[].details`) say which field to read: `name_field`, `code_field`,
    `link_field`, and per topic `grade_field` (listed buildings, parks and gardens, ALC), `zone_field` (EA: `flood_zone` FZ2/FZ3;
    NRW: `risk` "Flood Zone 2"/"Flood Zone 3"), `likelihood_field` (SEPA: `BAND_DESC`), `class_field` (Carbon and Peatland:
    `IMPORTANCE`, classes 1 and 2 nationally important; Hutton: `LCCODE`, 1-7). NI listed buildings: the layer is the whole
    Historic Buildings Record; listed ones have `CurrentGra` in `listed_values` (A, B+, B, B1, B2); "Record Only" and "Delisted"
    aren't listed. Wales predictive ALC: `predictive` is 1, 2, 3a, 3b, 4, 5, NA or U.
  - **SSSI Impact Risk Zones, decoded.** `details.irzcode` points to `vocab/sssi_irz_codes.json` (raw URL) and
    `docs/sssi-irz-codes.md`. The 13 digits are, in order: all consultations, infrastructure, wind and solar, minerals/oil/gas,
    rural non-residential, residential, rural residential, air pollution, combustion, waste, composting, discharges, water
    supply. 0 = no consultation for that category; any other digit selects a threshold text (verbatim from Natural England's
    checker). First digit 1 = all applications, 2 = all but householder; all zeros = none. All 208,189 zones decode.
  - **Licences, verbatim, with attribution** in `licence` and `attribution` (`vocab/licence_overrides.yaml` says where each was
    read). All OGL except: **Carbon and Peatland 2016** is under the UK **Non-Commercial** Government Licence (`open_licence`
    false); **Hutton's LCA** is under the James Hutton Institute Open Data Licence, whose terms we haven't read (`open_licence`
    false until someone does). Historic England's wording comes from its ArcGIS item ("Released under OGL", plus its Open Data
    Hub terms, whose page refuses bots). The EA's own attribution line wasn't readable (script-only page).
  - **New additive field: `type_name`.** A curated WFS record (Cadw, Welsh Government, NRW flood zones, EA flood zones) names
    its feature type in `details.type_name`; its `layer` is `<record id>:0`. `fetch_features` and `usage.query_url` use it.
  - **Speed, live 23 Nov (mcp-ask, one box per record where it should find something, limit 5):** all 45 returned features,
    0.2-1.8 s, except the IRZ (4.4 s, Leeds). Big layers, keep boxes small: SEPA surface water (8.2M polygons), NRW surface water
    (2.3M), Carbon and Peatland (440k), HE listed buildings (380k), Welsh ALC (255k), IRZ (208k). HES and Hutton can't page
    (up to 10,000 and 1,000 features per query); Hutton was ~20 s in an earlier direct test.
  - **Ranking, not changed:** in a plain concept search older crawled copies rank first (near Stonehenge the HE records come
    below Wiltshire's and HE's other layers). Use the ids. Crawled copies with other ids also exist for HES scheduled monuments
    (`25ffbbeec3836e1a`), SEPA river medium (`ce6e59e44174bf68`) and Hutton LCA (`bd18c4d31d168bf4`): prefer the new ids.
  - **Not found or not added (gaps to report as "not checked"):** Dark Sky Parks (no national layer; only council local-plan
    copies, e.g. Galloway Forest in D&G's LDP2, Northumberland's local plan); Scotland's Local Landscape Areas (on the
    Improvement Service's Spatial Hub, not checked); England's local landscape designations (council by council); Cadw's
    battlefields list (no layer found); Northern Ireland flood maps (DfI; only a DfC "premium" copy found) and farmland
    classification (none). Available but not asked for, so not added: England Peat Map (Natural England), Wales unified peat
    map (DataMapWales), HES listed-building outlines (746), Cadw WHS essential settings and significant views.

- (22 Nov, Tobler requests, **done**, live 22 Nov evening) **UK protected sites as fixed records, project outlines, and fixes.**
  All additive except the concept and publisher-type changes marked below.
  - **25 new records**, one per designation and nation, pointing at the designating body's own feature service (JNCC's
    offshore set is hosted by the atlas as tiles, because JNCC's OGC server doesn't answer cloud runners). Ids are fixed:

    | Nation | SAC | SPA | Ramsar | SSSI/ASSI | Marine | Ancient woodland | Other |
    |---|---|---|---|---|---|---|---|
    | UK offshore (JNCC) | | | | | `1d6371b702df0abc` SAC, SPA, MCZ, NCMPA, HPMA beyond 12 nm | | |
    | England (Natural England) | `a9cad137cd6e2466` | `8b28077c10e3e057` | `fc67624f3bd09663` | `0c53cecc65701f0c` | `2470b667af95db9c` MCZ | `4d20427c9827e672` | `f7fd85401cdf700f` priority habitats |
    | Scotland (NatureScot) | `7d382e1686a08bff` | `b10cb9d7a2892f7f` | `b2f1c178d39c0d0e` | `c6e90f0435ff9097` | `f682edebaabd1b8b` NCMPA inshore | `83edcb984cbc578d` | |
    | Wales (NRW) | `f1f2acb0cb971df9` | `0f71127c51a2172c` | `a6fa6c34e1ffe4c1` | `0761e0de1e55f269` | `10f54cd67c434aa8` MCZ | `dae5eef189e09f22` | |
    | Northern Ireland (DAERA) | `da17adda6e50b6da` | `7571a1f57be683da` | `a13d205bd42efeb8` | `e4d3902ce86a9334` ASSI | `6f8ffc3a4d831d53` all NI MPAs | | |

    Their keywords include `uk-statutory-designation`, so `find_datasets` with `text: "uk statutory designation"` lists
    them; concepts come from tagging as usual (protected-area, plus habitat, wetland, woodland or marine-activity).
  - **Licences and attribution, verbatim:** all are OGL v3.0 (checked). `get_dataset` gives each publisher's attribution
    statement in `attribution` (JNCC also `terms`); `vocab/licence_overrides.yaml` says where each was read. NRW's and
    DAERA's ArcGIS items carry thin licence text, so theirs come from DataMapWales and Open Data NI.
  - **New `get_dataset` details on these endpoints** (`endpoints[].details`): `name_field`, `code_field` (JNCC also
    `designation_field`: `SITE_STATU`), `data_date` and `data_date_source` (the data's own last edit, not our check).
  - **Overlaps to know:** sites straddling 12 nm are in JNCC's set and the country's; Dee and Severn estuary sites in
    both England's and Wales's. NatureScot's layers have one row per polygon part (Tobler already joins pieces).
  - **Natura 2000 and the UK, confirmed:** EMODnet's copy of the EEA Natura 2000 polygons (`2edf9cd303464f05`) has no UK
    sites (Dogger Bank returns only the Dutch Doggersbank; a Welsh/English box returns none). The EEA's centroid layer
    (`03094468579f7159`) still lists 924 UK sites, but from a 2013 release. Don't use either for UK sites.
  - **`fetch_features`, additive:** an ArcGIS layer whose page is smaller than `limit` (Natural England's MCZs send 3 a
    page) is now read page by page in parallel up to the limit; `pages_read` says how many pages when more than one.
    A WFS gets one 15 s wait (was two of 25 s: EMODnet Seabed Habitats' point layers failed after ~52 s); the error now
    says "timed out after 15 s". ArcGIS requests still wait 25 s. Hosted-file tiles retry once and a failed read is no longer
    cached for an hour (the likely cause of GEM's "tile 0_0 unreadable" on 18 Nov).
  - **Changed concepts (hand-set at publish time, `vocab/concept_overrides.yaml`):** 38 NSTA seismic survey layers
    are now `geology` only (were `oil-gas`), so "offshore platform" searches by `oil-gas` stop picking them. Licensing
    round prospects and areas stay `oil-gas`. Wreck layers (UKHO via EMODnet `d266bb32a493da90`, EMODnet heritage
    wrecks, NOAA, Historic England protected wrecks and others, 25 in all) are `heritage-site` and `shipping` (were
    mostly `seabed-habitat`).
  - **Changed publisher type:** The Crown Estate's layers (21) are `public-body` (were `business`), so they rank with
    other authorities; Crown Estate Scotland was already `regional-gov`. (`vocab/publisher_type_overrides.yaml`.)
  - **Speed, live 22 Nov (mcp-check, one box per record inside its nation, limit 50):** 0.2-3.1 s for 23 of the 25.
    JNCC at Dogger Bank 0.4 s (Dogger Bank and Southern North Sea SACs). Natural England's MCZs: 47 in 1.1 s over 16
    pages. **Slow: England's priority habitats** (818k polygons on Natural England's ArcGIS Online) took 1.4-20 s in
    direct tests and once timed out; keep boxes small and treat a timeout as "not checked".
  - **Ranking, not changed:** in a plain `protected-area` search at an offshore point these records come well down the
    list (Dogger Bank: places 58-75 of 188), behind England-wide land layers whose bounding boxes reach the North Sea.
    Use the ids above for the baseline rather than relying on search order.
  - **Project outlines (20 Nov request):** new hosted record **`03cc52745432ee74`**, the Planning Inspectorate's NSIP
    site boundaries from planning.data.gov.uk (285 projects with a location, OGL v3.0, attribution "© Crown copyright
    and database right 2026"). `details`: `name_field` name, `code_field` reference (EN010151…), `status_field`
    infrastructure-project-decision (pre-application, examination, decision, post-decision, withdrawn…), `type_field`,
    `link_field` documentation-url. A copy of 22 Nov: refreshed by hand (the source updates daily). NatureScot's Onshore
    Windfarm Proposals (`a0484a5671248c7a`) already ranks first for `power-plant` in Kintyre; its data predate Sept
    2024, which is why Cnoc Buidhe isn't in it. No GIS layer of Scottish Section 36 applications was found (the Energy
    Consents portal publishes cases, not boundaries); Wales's DNS not checked yet.
  - **Ids of hosted and curated records are now fixed** (they had followed whichever endpoint passed its check). On
    22 Nov a rerun gave the 18 GEM trackers other ids (e.g. extraction `97dd06297d3a4f43` instead of
    `11650fec8b9d8e5f`) for at most 15 minutes (about 20:35-20:50 UTC); they are back (checked live 20:55), and won't
    move again.
  - Already working, checked live 22 Nov: HES Scheduled Monuments `25ffbbeec3836e1a` (50 near Linlithgow, 2.2 s) and
    Hutton land capability `bd18c4d31d168bf4` (50, 3.5 s), since the 19 Nov no-paging fix; GEM extraction "Bonga" (3, 0.4 s).

- (20 Nov, Tobler request, **done**, live 08:00 UTC) **Land elevation at a point, national and global.** All additive; builds
  on `sample` from the depth request below.
  - **New `details.sample.method` values:** `api` (a point-height service: `sample_url` plus `value_path`, a JSON
    pointer such as `/elevations/0`) and `cog` (a cloud-optimised GeoTIFF: `use.file_url` names the file for a point,
    `details.sample.how` says how to fill it, then read the pixel). `identify` can now also be a MapServer identify
    (Geoscience Australia), with `value_path` saying where the number is.
  - **Any `sample` may carry its own templates** (`sample_url`, `file_url`). Placeholders the caller fills:
    `{lon}` `{lat}` and `{west}` `{south}` `{east}` `{north}` (WGS84, box half-size `box_deg`, default 0.001);
    `{x}` `{y}` and `{xmin}` `{ymin}` `{xmax}` `{ymax}` in `sample.crs` (box half-size `box_m`). Some services need
    a national grid (Swiss LV95, Dutch RD, UTM): the `crs` says which.
  - **`sample.browser: false`** marks a source a web page can't read directly (no CORS): fetch through a server.
  - **New records** (concept `elevation`): Scotland's 50 cm national lidar (COG) and one record per Scottish lidar
    survey (18, WMS feature-info); Copernicus GLO-30
    (COG on AWS, surface model, server-side only); France (IGN API), Japan (GSI API), Switzerland (swisstopo API),
    Spain (IGN 5 m WCS), Norway (Kartverket WCS), North Rhine-Westphalia (1 m WCS), Canada (NRCan HRDEM WCS),
    Netherlands (AHN feature-info), Australia (GA 5 m lidar and 1 second, MapServer identify).
  - **England's EA lidar WMS** and **Scotland's lidar WMS** layers now have `sample` (feature-info, metres).
  - Records whose host refuses GitHub's runners (Geoscience Australia) are checked by hand and show `unchecked`.
  - **`sample.nodata`** gives a service's no-data answer where it isn't empty: France's API answers -99999 outside
    its data, Scotland's surveys -9999 (or -999) outside the flown area. Treat these as "no value", not a height.
  - Live check (mcp-check, 20 Nov 08:13 UTC), heights read through the server's templates: Paris 34.83 m (IGN),
    Tokyo 3.6 m (GSI), Bern 553.8 m (swisstopo), Madrid 648 m (IGN Spain), Oslo 4.90 m (Kartverket), Cologne
    46.51 m (NRW), Ottawa 71.0 m (NRCan), Sydney 20.9 m (GA 5 m), Skye 121.7 m (Scotland 50 cm COG; 121.5 m by its
    WMS), Edinburgh 86.1 m (Scotland lidar phase 5), London 9.54 m (EA), Washington 18.4 m (3DEP). GLO-30 answered
    everywhere (read server-side). AHN gives nothing on buildings and water. CEDA's OPeNDAP refused repeated requests
    from GitHub (403) though single requests work: use the UNH image service for GEBCO in bulk.

- (19 Nov, Tobler request, **done**, live 20 Nov) **Values at a point: water depth and shipping density.** All additive.
  - **New capability `sample`**: the endpoint returns a number at a point, not a picture. `find_datasets` takes
    `capability: "sample"`. Picture-only services and vertically exaggerated ones (titles with 3.5x, 5x, 10x,
    "exaggeration", hillshade, colour ramps) never get it.
  - **`get_dataset` endpoints gain `details.sample`**, which says how to read the value:
    `method` (`identify`: ArcGIS ImageServer identify/getSamples; `feature-info`: WMS GetFeatureInfo as JSON, value
    in `field`; `opendap`: one grid cell by index; `lerc-tile`: ArcGIS tiled imagery, read the pixel from a LERC2D
    tile; `wcs`: GetCoverage of a tiny box, GeoTIFF), plus `value` (what the number is: `elevation`, `depth`,
    `density`, `class`, `measure`), `units` and `vertical_datum` where known. For `opendap` and `lerc-tile` it also
    gives the grid (origin, cell size, level) so the cell can be worked out. `use.sample_url` is a ready template
    with `{lon}` and `{lat}` (WGS84) for `identify` and `feature-info`.
  - **`get_dataset` gains `attribution`** (the publisher's attribution or citation line, verbatim) and **`terms`**
    (the publisher's terms of use, verbatim) where recorded. Both are omitted when we haven't recorded them.
  - **New records** (wave `spike-values`, concept `bathymetry` or `shipping`): GEBCO_2026 grid by OPeNDAP from CEDA
    (GEBCO's own distributor); GEBCO_2026 and its type-identifier grid as ImageServers at UNH CCOM; NOAA NCEI's DEM
    Global Mosaic; the World Bank/IMF Global Shipping Traffic Density (all vessels and five types, Esri-hosted tiles,
    CC BY 4.0).
  - **Licence fix:** EMODnet Bathymetry layers (ows.emodnet-bathymetry.eu) and EMODnet's vessel density coverages
    now carry CC BY 4.0 from EMODnet's terms, with EMODnet's attribution line. `open_licence` becomes true.
  - Ids already in the atlas don't change.
  - Live check (mcp-check, 20 Nov), values read through the server's own `sample_url`: off the Niger Delta (4.0N
    5.5E) GEBCO_2026 OPeNDAP -83 m (`dae2320fae0b26f0`), UNH image service -87 m (`9e5419ff6f330200`), NOAA mosaic
    -80 m (`962c2706d519ddd4`), GEBCO TID 40 (predicted, not measured; `77444d56f4682135`). Central North Sea: EMODnet
    DTM -87 m. Esri's own `gebco` copy said -140.5 m off the Niger Delta: prefer the GEBCO records. Shipping density
    ids: all vessels `a337942943e725dd`, commercial `2340ba1f3edf4c6d`, fishing `7ff33a9404410501`, oil and gas
    `7b04932bbcfb62ac`, passenger `11baa92a9a648e32`, leisure `26a0e614508f04e6`.
  - Watch `details.sample.value`: EMODnet's DTM 2016 and 2018 layers give depth as a positive number (`value:
    depth`); everything else in metres is `elevation`, negative below the datum.
  - Curated records' extents are set by hand, so they aren't flagged as overstated: `get_dataset` may show
    `extent_source: "curated"` (new value beside `declared` and `measured`).
  - A curated record whose host refuses crawlers in robots.txt (CEDA, Esri's tiled image services) shows its check
    as `unchecked`, not `fail`: we don't run automated checks there, and the record was checked by hand.

- (18 Nov, atlas change, **planned**, not yet live) **Publisher registry and trusted publishers**
  (`docs/publisher-registry-design.md`). When it ships, all additive except one:
  - `find_datasets` and `get_dataset` gain `publisher_id` (when matched), `trusted` (true/false) and, for data a
    partner hosts, `hosted_by` (e.g. Ordnance Survey data hosted by Esri UK). `find_datasets` gains `trusted_only`;
    trusted datasets get a small ranking boost.
  - **Changed text:** `publisher` shows the registry name when matched ("British Geological Survey" rather than
    "British Geological Survey (BGS)"); `get_dataset` keeps the crawled credit as `publisher_credit`.
  - New D1 columns, so one full reload (search keeps working during it).

- (18 Nov, atlas change, deployed ~14:38 UTC) **Spatial index for `find_datasets`.** Area and concept searches now read a quadtree cell
  key table instead of scanning the extent indexes: a 5 km search reads ~25k rows rather than ~270k (plus a count of
  as many again), and a concept search reads only that concept's datasets in the area (Gulf of Mexico oil-gas: ~1k
  rather than 264k). Details and measurements in `docs/decisions.md`. No input or output field changes. What can differ:
  - **Ranking sees every match** on area and concept searches, not only the 3,000 nearest in size, so the top results
    can change where an area holds more than 3,000 datasets (a city centre, a country-wide concept).
  - **`matches` is exact** on those searches (up to 20,000; above that `matches_capped`). On a large area without
    text or a concept that holds many datasets (the UK, the US, an ocean), results come from the 60,000 best-scored
    datasets world-wide, as before; `matches` then counts the ones in the area (typically a few thousand, not
    "10,000 capped"), with `matches_capped: true`.
  - `debug: true` reports `rows_read` for the whole search (all queries), plus `index`: `cells`, `rank` or `extent`.
  - `include_other_countries: true` and `text` searches use the same paths as before.

- (18 Nov) **Global Energy Monitor: 18 trackers as hosted datasets** (all CC BY 4.0, stated in each file; citation in
  every `fetch_features` `source`). Oil and gas extraction fields (outlines where mapped), gas pipelines and oil/NGL
  pipelines (routes, simplified to ~100 m), LNG terminals, oil and gas plants, coal plants, coal mines, coal
  terminals, wind, utility-scale solar, hydropower, geothermal, bioenergy, nuclear, iron and steel plants, cement
  plants, chemical plants, iron ore mines. Search with `text` "Global Energy Monitor" or the tracker name, or by
  concept (`pipeline`, `power-plant`, `oil-gas`, `mineral-extraction`, `port-airport`).
  - Hosted files are now **tiles**: the `geojson` endpoint URL ends in `index.json`, and `fetch_features` reads only
    the tiles near the area (all tiles for a `text` search; up to 40 nearest otherwise, with `matched_is_partial`).
  - **Left out:** solar rows sourced from TransitionZero (CC BY-NC 4.0, 18,732 rows); the integrated power tracker
    (repeats the individual trackers and carries the same non-commercial part); the methane emitters tracker (plumes
    are CC BY-NC-SA); coal mine boundaries (no licence stated); ownership, finance and LNG-carrier tables (not maps).
  - The extraction tracker keeps its id (11650fec8b9d8e5f). Field names are unchanged.

- (18 Nov) **Hosted download datasets: new endpoint protocol `geojson`.** Some sources only offer a download (Global
  Energy Monitor's trackers come as an .xlsx by request form). The atlas converts them (`atlas/files.py`) and hosts
  one GeoJSON at `…/data/f/<id>.geojson`; the dataset gets a `geojson` endpoint with `query` and `download`.
  `fetch_features` filters the file by area and `text` like any service, and adds `matched` (total in the area) and
  `source` (publisher, citation, licence, release). `where` isn't supported for these. Additive only. First one: GEM's
  Global Oil and Gas Extraction Tracker, once Rob has the March 2026 file.

- (18 Nov) **Tobler request: text search that holds up world-wide. Done** (deployed 18 Nov). `find_datasets`:
  - **`text`** now uses a full-text index (SQLite FTS5) over the **title, publisher, tags (concepts, ISO themes,
    keywords) and the first 300 characters of the description**. All words must match. Words of 4+ letters match as
    prefixes (`therm` finds thermal), and `"quoted phrases"` match exactly. AND, OR, NOT, NEAR and filler words
    (the, of, in, for) are ignored, and punctuation is dropped. Text that leaves no words is an error. Any area size
    works, up to the whole world.
  - **Large areas without text** (over 25 square degrees, roughly 5° by 5°: a region, a country or bigger): candidates are the
    best-scored datasets in the area rather than every one, so results are a good sample, not exhaustive. Add
    `text` or a `concept` to narrow it.
  - **Ranking:** text searches rank by relevance, then publisher authority (government and international bodies
    before local, academic, aggregators and businesses), then fit. Area searches rank by fit, then authority.
  - **Duplicates folded (new, on by default):** results with the same title and much the same extent (over half of
    the larger extent overlapping) are folded into the best-ranked one, listed in a new **`also_available_from`**
    field (`[{id, publisher, publisher_type}]`, up to 10). `fold_duplicates: false` turns it off.
  - **`matches`** now counts up to 10,000; above that, **`matches_capped: true`** is set. New field **`search`**
    says which path ran: `text`, `area` or `large-area`.
  - All field names Tobler uses are unchanged; the new ones are additive.

- (18 Nov) **Africa published, and national authorities pass without a description.** New wave `spike-africa`
  (8,688 passing datasets) added to `runs/published.txt`. It includes petroleum layers from ONHYM (Morocco), the
  Petroleum Authority of Uganda and ANPG (Angola), plus Mozambique's FNDS and WRI's Forest Atlas. Quality rule change
  (Rob's call): central-government and national public-body layers that answer and aren't junk now pass even with no
  description, and code-like or all-caps titles are tidied ("Petroleum agreements onshore"). Expect thinner
  `abstract` text on these. **A trial for Africa only** (country list in `atlas/quality.py`); other regions are
  unchanged until Rob decides.
  *Not available:* GNPC (Ghana), Kenya's State Department for Petroleum and ANPG's ArcGIS Online services need a login
  token. Additive only; no field changes.

- (17 Nov, night) **Tobler request: trusted global services, key-gated services, Esri copies. Design written, not
  built:** `docs/trusted-services-design.md`. Proposes, all additive: `licence_class` (open, open-inferred, esri-mla,
  restricted, stated, unknown) with `exclude_licence_class`; `trusted` and `trusted_only`; `source` and `copy_of` for
  Living Atlas copies, ranked after the publisher's own service; key-gated services (`access: "key"`, key held by the
  atlas Worker) starting with NASA FIRMS. Suggested order: licence class first. Waiting on Rob for the FIRMS key, the
  trusted list and the non-commercial question.
- (17 Nov, night) **Tobler request: EMODnet as feature services, with licences. Done, published ~22:45.** New wave
  `spike-emodnet` (`vocab/seeds/emodnet.yaml`), first in `runs/published.txt`: WFS and WMS of the EMODnet portals plus
  EMODnet's GeoNetwork (2,134 records). A layer's WFS and WMS on one server are one dataset, and `fetch_features`
  uses the WFS. Catalogue records join layers by server and layer name, so CC-BY 4.0 and descriptions come through.
  Human Activities: 251 passing, 156 fetchable as WFS, 178 with CC-BY 4.0. Examples: Heritage Ship Wrecks
  `ee41a8d58f1fe201`, UKHO worldwide wrecks `d266bb32a493da90` (3 wrecks at Rosebank), Pipelines `bb42a4c5b1c1508f`,
  Offshore Installations `a38e968b2ce8d36a`, Wind Farms (polygons) `f70f5adfc354d387`, Military Areas (polygons)
  `ff292558d2076043`, Dumped Munitions (polygons) `821bb9c912e8e65c`. Heritage Ship Wrecks has nothing east of
  Shetland; that's the data, not a fault.
  - **Ids changed:** the old WMS-only EMODnet records are replaced by these (datasets an earlier wave fully holds are
    dropped at publish). Fields unchanged.
  - **Not covered:** EMODnet Geology's and Physics' own servers refuse crawlers in robots.txt, so we don't crawl them
    directly (some Physics layers come in through catalogue links).
  - **"Prefer WFS over a WMS sibling" in general:** done wherever both are crawled, by the same grouping. Next step:
    probe `/wfs` beside known GeoServer WMS endpoints in future crawls, so siblings are found without seeding.
- (17 Nov, night) **Tobler request: mislabelled NSTA record (`bdb5d0a70436343e`). Done.** It wasn't only a title:
  the crawl had grouped NSTA's live service and its `_removed_` twin under one dataset, because they share a title
  and extent, and the removed one came first. Nine NSTA datasets were like this, including `29a134d61746d7dc`
  (pipeline linear, ED50). At publish time (`atlas/titles.py`), such datasets are now split: the original id keeps the
  live service, and the removed service becomes its own dataset with " – removed" in its title (for example
  `bdb5d0a70436343e` live, `16b89c1506aa0b84` removed; `29a134d61746d7dc` live, `d35c83cc47faa79b` removed). Where
  every endpoint is in a status-named service, the word is added to the title. Words: removed, decommissioned,
  abandoned, proposed, planned, superseded, obsolete, archived, expired, relinquished. **Not "historic"**: in
  service names it mostly means heritage (Historic Environment Scotland, Historic England), so it would mislabel
  live data. Also left out: "former" and "draft". *Contract effect:* new dataset ids appear for the split-off
  parts; existing ids keep working and now point at live data; field names are unchanged.
- (17 Nov, late evening) **Tobler request: `fetch_features` "No dataset with id". Done 21:15** (see the outage note
  below). Guarantee: every id `find_datasets` returns can be opened with `get_dataset` and passed to
  `fetch_features`. The deploy smoke test checks it after every MCP deploy, and `mcp-check` checks it on demand.

- (17 Nov, ~20:13–21:15, atlas fault, fixed) **`get_dataset` and `fetch_features` failed** with "No dataset with id"
  while `find_datasets` kept working. The MCP Worker reads dataset details from the viewer's detail files on GitHub
  Pages, and the viewer's switch to gzipped files (`d/xx.json` to `dz/xxx.json.gz`) moved them. The Worker now reads
  the new files (and the old ones as a fallback). Lesson for the atlas chat: a viewer data layout change is an MCP
  change. `mcp-check` (runs/mcp-check.env) now tests all three tools live.

- (17 Nov, atlas change, approved by Rob) **Inferred licence for US federal works.** For about 5-6k US datasets
  from federal agencies (NOAA, USFS, Census, BLM, USGS, BOEM…) that state no open licence, `licence` becomes
  "US federal government work: public domain in the US (inferred, 17 U.S.C. §105; not stated by the publisher)",
  followed by the publisher's credit line, and `open_licence` becomes true. Skipped when the credit names a
  non-federal party (a university, company, state or county). Field names and types don't change, so nothing
  in Tobler should break. Tobler may want to show "inferred" when it reports a licence: the word is always in the text.

- (17 Nov, parked by Rob) A nightly name index of named features (licence blocks, fields, protected areas,
  wind leases) so a named search is one query. Needs a licence check before any building.
