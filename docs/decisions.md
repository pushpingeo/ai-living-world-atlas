# Decisions

Judgment calls made while building, newest at the bottom. Any of these can be overruled.

## 2026-11-15: Initial build

**Scope: a harvested index, not a hand-curated list.** Quality filtering does the curation. The original 30–50 hand-picked services design is dropped.

**Seeds from the Dateno registry.** About 43.6k catalogues, CC BY 4.0, with software type, owner type and API endpoints. Attribution goes in the README and in the published data.

**The unit is the layer.** One row per ArcGIS layer, WMS layer or WFS feature type. Merging the same data published several ways (FeatureServer + MapServer + WMS + portal record) into one dataset comes later. The spike measures how much duplication there is.

**ArcGIS Online hosted services only come in through a public catalogue.** We never list a whole `services.arcgis.com` organisation, which is where the test layers and personal content live. A self-hosted ArcGIS Server found through a catalogue link gets its whole directory walked, because it belongs to that body.

**Hub feeds use `/api/feed/dcat-us/1.1.json`**, not `/data.json`, which returned broken output on several sites.

**Trust score (0–100).**
- Authority, up to 30: owner type from the registry. Where that's unknown, government or academic domain rules.
- Metadata, up to 40: a real title, an abstract, keywords, licence text, a usable extent.
- Liveness, up to 20: the service responds, and the sample layer returns data.
- Licence clarity, up to 10: a recognised open licence, or at least some stated terms.

A layer **passes** at 60 or more, with no junk flags, a failed check not recorded, and an abstract of 50+ characters. The abstract rule is deliberate: a layer with no description can't be found or trusted, whatever else it has.

**Titles.** If a layer's own name looks like code (`ADP_AVL_Greenbelt_Revised`) and a catalogue record names it properly, the catalogue title is used for display and scoring. The raw name is kept.

**Junk flags look at the title only**, not the service name. Hosted "_view" services are the normal, correct way to publish on ArcGIS Online, so they shouldn't count against a layer.

**Liveness checks.** Feature layers get a `returnCountOnly` query. Map and image layers get a 64×64 image request. Cache-only tile services get one tile at the layer's centre, and a missing tile counts as "unchecked", not failed. WMS gets a small GetMap; WFS gets one feature. The spike samples up to 2 layers per service. The full index will spread checks over a month.

**Themes.** The backbone is the 19 ISO 19115 topic categories. INSPIRE's 34 themes and data.gov.uk's themes are crosswalked to them (see `vocab/themes.yaml`). "Declared" means the source stated it, either as a theme field or as an exact keyword match. AI tagging comes later and is recorded separately.

**Country is the seed catalogue's country for now.** Some UK catalogues publish data for other countries (WorldPop, for example). Deriving coverage from the extent comes later.

**Crawl etiquette.** A named user agent, 2 concurrent requests per host, robots.txt respected, one retry with backoff on 429/5xx.
