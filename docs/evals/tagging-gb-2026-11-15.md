# AI tagging agreement: Haiku 5.5 vs Opus 5.5

200 passing UK datasets (68 with publisher-declared themes); 0 errors.

## Themes (ISO 19115)
- First theme identical: **86%**; any theme shared: 99%; mean overlap 0.75
- Against publisher-declared themes (68 datasets): Haiku matches 85%, Opus matches 85%

## Concepts
- First concept identical: **84%**; any concept shared (or both none): 90%; mean overlap 0.76
- No concept fits: Haiku 2%, Opus 4%
- Out-of-vocabulary answers (dropped): Haiku 2, Opus 0

## Proposed new concepts (both models)
- hydrogeology: 5
- garden-plant-collection: 4
- garden-landscape-feature: 4
- airborne-geophysics: 2
- historic-map: 2
- plant-collection-locations: 2
- urban-heat-exposure: 2
- seismic-survey: 2
- fly-tipping: 2
- phenology: 2
- nitrate-vulnerable-zone: 2
- sea-level-rise: 2
- compulsory-purchase-order: 2
- water-safety-equipment: 2
- traffic-count: 2

## Cost of this test
- Haiku: 200 calls, $0.09; Opus: 200 calls, $3.66
- Haiku at batch rates would tag 100k datasets for about $23

## First-concept disagreements (up to 40)
- **LDP Level 4 Settlement Extent** (Brecon Beacons National Park Authority): Haiku ['land-use-plan', 'settlement'] / Opus ['settlement', 'land-use-plan']
- **Car free development addresses** (Bristol City Council): Haiku ['address'] / Opus ['planning-application', 'parking', 'address']
- **Heat connection zone** (Bristol City Council): Haiku ['waste'] / Opus ['land-use-plan']
- **Road and rail noise 2005 Lden** (Bristol City Council): Haiku ['waste'] / Opus ['noise']
- **Healthy and Biologically Diverse - Commercial Fish and Shellfish Stock** (Scottish Government SpatialData.gov.scot): Haiku ['fishing', 'seabed-habitat'] / Opus ['species-occurrence', 'fishing']
- **Surface water high risk areas** (Bristol City Council): Haiku ['waste'] / Opus ['flood-risk']
- **Crop Map of England (CROME) 2023** (Rural Payments Agency): Haiku ['land-cover', 'agriculture'] / Opus ['agriculture', 'land-cover']
- **Plant Locations Clear** (National Trust): Haiku ['species-occurrence', 'tourism-recreation'] / Opus []
- **Bathing water catchments** (Scottish Environment Protection Agency): Haiku ['water-quality'] / Opus ['river', 'water-quality']
- **Crop Map of England (CROME) 2024** (Rural Payments Agency): Haiku ['land-cover', 'agriculture'] / Opus ['agriculture', 'land-cover']
- **Local Green Space (CFW6)** (SDNPA): Haiku ['greenspace', 'land-use-plan'] / Opus ['land-use-plan', 'greenspace']
- **World rectangle** (Brentwood Borough Council): Haiku [] / Opus ['basemap']
- **Landscape Feature** (National Trust): Haiku ['greenspace'] / Opus []
- **Derg And Mourne Network Contribution** (Northern Ireland Environment Agency): Haiku ['river'] / Opus ['water-quality', 'river']
- **WFD Shellfish Water Protected Areas** (ArcGIS Online | DAERA): Haiku ['protected-area', 'water-quality'] / Opus ['water-quality', 'marine-activity']
- **blackthorn_flowering (raster)** (European Environment Agency): Haiku ['species-occurrence'] / Opus []
- **CAFM Sites** (City of Edinburgh Council Mapping): Haiku ['school'] / Opus ['land-ownership', 'community-facility']
- **North of Tyne Local Nature Recovery Strategy - Opportunities in the Wi** (Northumberland County Council): Haiku ['habitat'] / Opus []
- **Landscape Feature** (National Trust): Haiku ['greenspace'] / Opus []
- **Village Boundaries** (Lichfield District Council): Haiku ['admin-boundary'] / Opus ['settlement', 'land-use-plan']
- **RPA Parcel Points (England)** (Rural Payments Agency): Haiku ['land-ownership'] / Opus ['agriculture']
- **TIGER New York** (Knowsley Metropolitan Borough Council): Haiku ['statistical-area'] / Opus ['road']
- **Landscape Feature** (National Trust): Haiku ['greenspace', 'tourism-recreation'] / Opus ['heritage-site']
- **WWNP Potential for Wider Catchment Tree Planting** (Environment Agency): Haiku ['woodland', 'flood-risk'] / Opus ['flood-risk', 'woodland']
- **Global Distribution of Special Areas under MARPOL** (UN Environment Programme World Conservat): Haiku ['marine-activity'] / Opus ['shipping', 'maritime-boundary', 'water-quality']
- **Radiactive Substances - Registration** (Scottish Environment Protection Agency): Haiku ['waste'] / Opus []
- **Landscape Feature** (National Trust): Haiku [] / Opus ['heritage-site']
- **LicensedPlugInVehiclesBusCoachVEH0142 UK DfT Poly 2023** (Department for Transport): Haiku ['active-travel'] / Opus ['public-transport']
- **Healthy and Biologically Diverse - Protected Areas - Marine and nature** (Atkins Geospatial): Haiku ['marine-activity', 'protected-area'] / Opus ['seabed-habitat', 'protected-area']
- **LicensedPlugInVehiclesBusCoachVEH0142 UK DfT Poly 2024** (Department for Transport): Haiku ['active-travel'] / Opus ['public-transport']
- **Landscape Feature** (National Trust): Haiku ['greenspace', 'tourism-recreation'] / Opus []
