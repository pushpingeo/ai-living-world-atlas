# Africa: where the public map services are (scoping, 17 Nov 2026)

Scoping only: no crawl built. The index has **no African national publishers yet**. None of the services below are
in any wave, and the global wave has no passing dataset with an African country.

## What a first look found

Searched ArcGIS Online (the one source reachable from the workspace) country by country, for oil, gas, petroleum,
blocks, licences, concessions, permits, cadastre, mining and seismic. Every hosting org with 2+ hits is in
`africa-agol-candidates.csv` (320 orgs). Keyword search is noisy: "Niger" matches Nigeria and "Guinea" matches
Papua New Guinea, so the list needs a human pass.

**National petroleum and mining bodies publishing openly (the prize):**

| Country | Publisher | Public services | Examples |
|---|---|---|---|
| Ghana | GNPC (national oil company) | 44 | onshore/offshore blocks, licences, open licences, 2D/3D seismic, wells, fields, FPSOs |
| Angola | ANPG (petroleum agency) | 57 | blocks, maritime zones, bathymetry, environmental layers; also its own server gis.anpg.co.ao |
| Kenya | an account whose owner name suggests the petroleum ministry (not confirmed) | 26 | petroleum blocks, old and reconstituted blocks, 2D/3D seismic, gravity, wells |
| Morocco | ONHYM (hydrocarbons and mines) | 14 | petroleum agreements and reconnaissance contracts, mining projects |
| Mozambique | FNDS (national sustainable development fund) | 580 | mostly forestry and land; includes active oil and gas concessions |
| Rep. of Congo, Cameroon, Gabon, CAR, DRC, Eq. Guinea, Liberia | WRI Forest Atlas (run with the ministries) | many | oil permits, mining permits, forest concessions, protected areas |

**Useful but not authoritative:**
- Consultancies' acreage maps: Somalia licensed acreage and licence rounds, Equatorial Guinea licence blocks
  (Perceptum). Good for finding names, but the publisher isn't the government. Show them as such.
- NGOs: WWF (Kenya oil blocks, Hoima–Tanga pipeline), Global Forest Watch (mining concessions for some countries),
  The Nature Conservancy.
- Continental: Esri's Africa GeoPortal, Africa Geoscience Data, GRID3 settlements, UNEP.

**Nigeria and Tanzania:** nothing official for petroleum turned up on ArcGIS Online. Petroleum licence maps there
seem to be PDFs or behind data-room logins (NUPRC, TPDC/PURA). The next places to look are below.

## Other routes (not tried yet; need a probe run from Actions)

1. **Servers under African domains.** Look up hostnames under .ng, .tz, .gh, .ke, .gov.za and so on in
   certificate-transparency logs and the Common Crawl URL index. Then keep the ones that answer at
   `/arcgis/rest/services`, `/server/rest/services` or `/geoserver/ows`. This is how to find self-hosted
   government servers that no catalogue lists. Probably the best route for Nigeria and Tanzania.
2. **Mining cadastre portals.** Several countries run online cadastres (often Trimble Landfolio) with map layers
   behind them: Tanzania, Zambia, Kenya, Uganda, Namibia, Mozambique among others. These need checking one by one.
   Mining licences rather than petroleum, but the same kind of data.
3. **Continental platforms with OGC services:** Digital Earth Africa (WMS/WCS across the continent), RCMRD
   (Nairobi), OSS (Sahara and Sahel Observatory), HDX/OCHA.
4. **OGC service search engines** (GeoSeer, Spatineo) that already index WMS/WFS by country.

## Suggested wave (spike-africa), for Rob to approve

- **Seeds:** the national bodies above (GNPC, ANPG and its server, ONHYM, the Kenya petroleum account, FNDS), the
  Forest Atlas servers, Digital Earth Africa, plus an approved list from `africa-agol-candidates.csv` after a human
  pass. Consultancies and NGOs go in with their own publisher type, not as government.
- **Then** route 1 (domain discovery) as a second pass for countries still thin, starting with Nigeria and Tanzania.
- **Licences:** most of these services state no licence, so they'll show "not stated". Petroleum data in
  particular often comes with terms on the agency's website. Check those before Tobler uses anything commercially.
- **Cost:** crawling is free (Actions). Tagging a few tens of thousands of datasets is a few dollars.
- **Size:** this adds to the viewer data. Do the gzip change in `docs/viewer-data-size.md` first.
