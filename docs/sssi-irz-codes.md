# SSSI Impact Risk Zones: decoding `irzcode`

Natural England's SSSI Impact Risk Zones layer (England; atlas record `uk-ne-sssi-impact-risk-zones`) has one attribute,
`IRZURL`, a link to Natural England's online checker. Its `irzcode` parameter is 13 digits, one per development
category. This page says how to read it; `vocab/sssi_irz_codes.json` has the same table for code.

Example: `https://irz.geodata.org.uk/IRZ/step2.html?irzcode=0300000630000&...` means Infrastructure level 3, Air pollution
level 6 and Combustion level 3; every other category is 0 (no consultation for it in this zone).

## Rules

- Position *n* of the code belongs to category *n* in the table below.
- `0`: no consultation needed for that category in this zone.
- Any other digit: consult Natural England if the proposal matches that level's text. Read the text: level numbers aren't
  comparable across categories.
- All zeros (`0000000000000`): no consultation categories (1,026 zones).
- First digit `1`: consult on all planning applications. First digit `2`: all except householder applications.

## Categories and levels

Zones per level are counts of the 208,189 zones on 23 Nov 2026 (a zone usually has several categories).

| Pos | Key | Category | Level | Consult Natural England on… | Zones |
|---|---|---|---|---|---|
| 1 | `ac` | All Consultations | 1 | ALL PLANNING APPLICATIONS | 40,716 |
| 1 | `ac` | All Consultations | 2 | ALL PLANNING APPLICATIONS EXCEPT HOUSEHOLDER APPLICATIONS | 41,841 |
| 1 | `ac` | All Consultations | 3 | All planning applications (except householder applications) where the proposed development is outside or extends outside existing settlements/urban areas and will increase lighting levels or affect greenspace, farmland, semi natural habitats, trees/woodland, waterbodies, rural buildings/structures (manmade or natural) or linear landscape features such as hedgerows, streams and rivers through direct loss, fragmentation or change of use. | 23,921 |
| 1 | `ac` | All Consultations | 4 | All planning applications (except householder applications) where the proposed development is outside or extends outside existing settlements/urban areas and will increase lighting levels or affect trees/woodland, waterbodies, rural buildings/structures (manmade or natural) or linear landscape features such as hedgerows, streams and rivers through direct loss, fragmentation or change of use. | 8,350 |
| 2 | `in` | Infrastructure | 1 | Pipelines and underground cables, pylons and overhead cables (excluding upgrades and refurbishment of existing network). Any transport proposal including new or extended footways, cycleways, roads/car parks, railways and waterways (excluding routine maintenance). Airports, helipads and other aviation proposals. | 90,154 |
| 2 | `in` | Infrastructure | 2 | Pylons and overhead cables. Airports, helipads and other aviation proposals. | 247 |
| 2 | `in` | Infrastructure | 3 | Airports, helipads and other aviation proposals. | 33,227 |
| 3 | `ws` | Wind and Solar | 1 | Solar schemes with a footprint > 0.5ha, all wind turbines. | 50,492 |
| 3 | `ws` | Wind and Solar | 2 | Wind turbines. | 11,472 |
| 4 | `og` | Minerals, Oil and Gas | 1 | Planning applications for quarries, including: new proposals, Review of Minerals Permissions (ROMP), extensions, variations to conditions etc. Oil & gas exploration/extraction. | 102,747 |
| 4 | `og` | Minerals, Oil and Gas | 2 | Planning applications for quarries: new proposals or extensions, outside or extending outside existing settlements/urban areas affecting greenspace, farmland or semi natural habitats. Oil & gas exploration/extraction. | 2,923 |
| 4 | `og` | Minerals, Oil and Gas | 3 | Oil & gas exploration/extraction. | 3,914 |
| 5 | `rn` | Rural Non-Residential | 1 | Any non-residential development outside of existing settlements/urban areas where the net additional gross internal floorspace following development is 30m² or more. | 0 |
| 5 | `rn` | Rural Non-Residential | 2 | Large non-residential developments outside of existing settlements/urban areas where the net additional gross internal floorspace is > 1,000m² or the footprint exceeds 0.2ha. | 49,609 |
| 5 | `rn` | Rural Non-Residential | 3 | Large non-residential developments outside of existing settlements/urban areas where the footprint exceeds 1ha. | 15,680 |
| 6 | `re` | Residential | 1 | Any residential developments with a total net gain in residential units. | 4,533 |
| 6 | `re` | Residential | 2 | Residential development of 10 units or more. | 16,259 |
| 6 | `re` | Residential | 3 | Residential development of 25 units or more. | 0 |
| 6 | `re` | Residential | 4 | Residential development of 50 units or more. | 31,635 |
| 6 | `re` | Residential | 5 | Residential development of 100 units or more. | 26,231 |
| 6 | `re` | Residential | 6 | Residential development of 500 units or more. | 0 |
| 7 | `rr` | Rural Residential | 1 | Any residential developments outside of existing settlements/urban areas with a total net gain in residential units. | 25,822 |
| 7 | `rr` | Rural Residential | 2 | Any residential development of 10 or more units outside of existing settlements/urban areas. | 20,927 |
| 7 | `rr` | Rural Residential | 3 | Any residential development of 25 or more units outside existing settlements/urban areas. | 0 |
| 7 | `rr` | Rural Residential | 4 | Any residential development of 50 or more units outside existing settlements/urban areas. | 32,269 |
| 7 | `rr` | Rural Residential | 5 | Any residential development of 100 or more units outside existing settlements/urban areas. | 6,562 |
| 7 | `rr` | Rural Residential | 6 | Any residential development of 500 or more units outside existing settlements/urban areas. | 0 |
| 8 | `ap` | Air Pollution | 1 | Any development that could cause AIR POLLUTION or DUST either in its construction or operation (including: industrial/commercial processes, livestock & poultry units, slurry lagoons/manure stores). | 22,044 |
| 8 | `ap` | Air Pollution | 2 | Any development that could cause AIR POLLUTION (including: industrial/commercial processes, livestock & poultry units, slurry lagoons/manure stores). | 24,265 |
| 8 | `ap` | Air Pollution | 3 | Any industrial/agricultural development that could cause AIR POLLUTION (including: industrial processes, livestock & poultry units with a floorspace > 500m², slurry lagoons > 200m² & manure stores > 250 tonnes). | 44,337 |
| 8 | `ap` | Air Pollution | 4 | Any industrial/agricultural development that could cause AIR POLLUTION (including: industrial processes, livestock & poultry units with a floorspace > 500m², slurry lagoons > 750m² & manure stores > 3500 tonnes). | 14,887 |
| 8 | `ap` | Air Pollution | 5 | Livestock & poultry units with a floorspace > 500m², slurry lagoons > 750m² & manure stores > 3500 tonnes. | 13,573 |
| 8 | `ap` | Air Pollution | 6 | Livestock & poultry units with a floorspace > 500m², slurry lagoons > 4000m². | 3,246 |
| 9 | `cb` | Combustion | 1 | All general combustion processes. Incl: energy from waste incineration, other incineration, landfill gas generation plant, pyrolysis/gasification, anaerobic digestion, sewage treatment works, other incineration/combustion. | 46,309 |
| 9 | `cb` | Combustion | 2 | General combustion processes >20MW energy input. Incl: energy from waste incineration, other incineration, landfill gas generation plant, pyrolysis/gasification, anaerobic digestion, sewage treatment works, other incineration/combustion. | 44,337 |
| 9 | `cb` | Combustion | 3 | General combustion processes >50MW energy input. Including: energy from waste incineration, other incineration, landfill gas generation plant, pyrolysis/gasification, anaerobic digestion, sewage treatment works, other incineration/combustion. | 26,064 |
| 10 | `wa` | Waste | 1 | Mechanical and biological waste treatment, inert landfill, non-hazardous landfill, hazardous landfill, household civic amenity recycling facilities construction, demolition and excavation waste, other waste management. | 46,309 |
| 10 | `wa` | Waste | 2 | Landfill. Including: inert landfill, non-hazardous landfill, hazardous landfill. | 57,817 |
| 11 | `cp` | Compost | 1 | Any composting proposal. Incl: open windrow composting, in-vessel composting, anaerobic digestion, other waste management. | 46,309 |
| 11 | `cp` | Compost | 2 | Any composting proposal with more than 500 tonnes maximum annual operational throughput. Incl: open windrow composting, in-vessel composting, anaerobic digestion, other waste management. | 22,863 |
| 11 | `cp` | Compost | 3 | Any composting proposal with more than 75000 tonnes maximum annual operational throughput. Incl: open windrow composting, in-vessel composting, anaerobic digestion, other waste management. | 21,474 |
| 12 | `dc` | Discharge | 1 | Any discharge of water or liquid waste including to mains sewer. | 1,786 |
| 12 | `dc` | Discharge | 2 | Any discharge of water or liquid waste that is discharged to ground (ie to seep away) or to surface water, such as a beck or stream. | 21,327 |
| 12 | `dc` | Discharge | 3 | Any discharge of water or liquid waste of more than 2m³/day that is discharged to ground (ie to seep away) or to surface water, such as a beck or stream. | 10,424 |
| 12 | `dc` | Discharge | 4 | Any discharge of water or liquid waste of more than 5m³/day that is discharged to ground (ie to seep away) or to surface water, such as a beck or stream. | 21,913 |
| 12 | `dc` | Discharge | 5 | Any discharge of water or liquid waste of more than 20m³/day that is discharged to ground (ie to seep away) or to surface water, such as a beck or stream. | 29,173 |
| 12 | `dc` | Discharge | 6 | Any discharge of water or liquid waste of more than 20m³/day to ground (ie to seep away) or to surface water, such as a beck or stream (NB This does not include discharges to mains sewer which are unlikely to pose a risk at this location). | 0 |
| 13 | `wt` | Water Supply | 1 | Any development needing its own water supply eg remote rural housing that is not connected to a mains water supply, OR large infrastructure such as warehousing/industry where the total net additional gross internal floorspace following development is > 1,000m². | 58,286 |
| 13 | `wt` | Water Supply | 2 | Large infrastructure such as warehousing/industry where the total net additional gross internal floorspace following development is 1,000m² or more. | 21,457 |

## Source and checks

- The split comes from the checker's own script (`step2.html`: the positions are `ac, in, ws, og, rn, re, rr, ap, cb, wa, cp,
  dc, wt`) and the level texts from its templates (`/templates/<key><digit>.html`), read 23 Nov 2026 through the `probe`
  workflow (round 28; the workspace can't reach irz.geodata.org.uk).
- All 208,189 zones were read the same day: 3,120 distinct codes, and every non-zero digit has a level text.
- Natural England updates the zones every two months and could change the texts. Re-read the templates if a new digit
  appears (the check above is quick to rerun).
- This is screening help, not Natural England's advice: its checker also asks follow-up questions, and in some zones gives
  standing advice. Natural England's user guidance: https://irz.geodata.org.uk/IRZ/guidance/SSSI_IRZ_User_Guidance.pdf
