# Publisher registry: design (18 Nov 2026)

Proposal for Rob to agree before building. It comes before the `trusted` field and licence classes
(`docs/trusted-services-design.md`), because both depend on knowing who a dataset really comes from.

## The problem in numbers

From the published index (266,692 datasets, 18 Nov):

- **6,984 distinct publisher strings.** Many are the same body written differently: NOAA appears under 32 names,
  USGS under 31. Some are credit lines rather than names (up to 175 characters).
- **Names alone can't be trusted for matching.** Searching for "NSTA" finds 656 datasets, almost all German
  ("Landes*anst*alt"). The real NSTA has 191, all on ArcGIS Online.
- **ArcGIS Online hides publishers behind one host.** arcgis.com carries 27.5k datasets from 1,558 publishers. The
  organisation id in the URL (`services.arcgis.com/<org>/...`) separates them: 502 orgs cover 22k of those datasets.
- **Some types are wrong.** Geo-System Sp. z o.o. (a Polish software firm hosting council services) is listed as a
  public body with 2,061 datasets; "The Ancient Geographers" is a public body in Italy.
- **The long tail is long.** The top 200 domains cover 73% of datasets, the top 1,000 cover 98%. There are 400
  government or international publisher names with 100+ passing datasets, and 1,067 with 20+.

## What the registry is

One file, `vocab/publishers.yaml`, reviewed by Rob and kept in git. One entry per real body:

```yaml
- id: bgs                          # short, stable; never reused
  name: British Geological Survey  # the name we show
  country: GB                      # ISO code, or "" for international bodies
  type: public-body                # overrides the crawl's publisher_type
  role: geological-survey          # national-mapping, geological-survey, hydrographic, met-service,
                                   # environment-agency, energy-regulator, statistics, nature-agency,
                                   # international, research, local-gov ... (short controlled list)
  trusted: true                    # authoritative for what it publishes, from its own servers
  match:
    hosts: [bgs.ac.uk]             # its own servers (subdomains included)
    agol_orgs: []                  # ArcGIS Online organisation ids it publishes from
    names: ["British Geological Survey", "BGS"]   # exact credit strings, after tidying case and spaces
  evidence: https://www.bgs.ac.uk/  # where we checked who they are
  added: 2026-11-19
```

Other entries can be marked `hosting_only: true`: platforms that serve other people's data (Geo-System, govConnect,
HALE»connect, generic arcgis.com). These are never credited as the publisher, and never trusted.

## How datasets are matched (at publish time, no recrawl)

1. **Host or ArcGIS Online org** of the dataset's endpoints: the strong match. A dataset served from bgs.ac.uk is BGS's.
2. **Exact name**, only if no host or org matched: tidies the publisher name, but never makes a dataset trusted. So an
   Esri Living Atlas copy that credits NOAA shows as NOAA's data but isn't "trusted" (that's the copy-detection
   work in the trusted-services design).
3. No match: the dataset keeps what the crawl found, as today.

A registry entry overrides the crawl's publisher type and country for the datasets it matches. That also fixes the
`home` country used to keep foreign layers out of searches.

## Keeping it maintained: a weekly candidate list

Rob shouldn't have to curate 7,000 names. A weekly `publishers` workflow (after the Monday sweep) does the work:

- **Candidates:** unregistered hosts and ArcGIS Online orgs, ranked by passing datasets, then by signals: a
  government domain (.gov, .gov.uk, .gouv.fr, .govt.nz, gc.ca, admin.ch, europa.eu...), a government or
  international publisher type, the share of its endpoints still answering in the liveness sweep, licence and
  description coverage. Each comes pre-filled (name variants seen, hosts, orgs, country, suggested type and role).
- **Review as a GitHub issue** with one checkbox per candidate, which works from a phone. Rob ticks the ones to add
  and closes the issue; a workflow (only acting when Rob closes it) writes the ticked ones into publishers.yaml and
  the unticked ones into `vocab/publishers_declined.yaml`, so they don't come back. Ten to twenty a week, a few
  minutes. Anything needing a correction (a different name, not trusted) can be typed as a comment under the
  item, and the atlas chat picks it up.
- **Drift report** in the same issue: registered hosts that stopped answering, orgs that went quiet, and big new
  name variants for a registered body.

**Getting to a couple of hundred:** a first, larger issue of about 250 candidates, grouped by country, with the
national agencies Rob named (BGS, Ordnance Survey, NSTA) and their equivalents elsewhere (mapping and geological
surveys, hydrographic and met offices, environment and energy regulators) at the top, plus the international bodies
already in the global wave (UNEP-WCMC, GEBCO, EMODnet, FAO, ESA/Copernicus, NOAA, USGS, NASA). One sitting of perhaps
half an hour; after that, weekly top-ups.

Two gaps the first list will show: **Ordnance Survey has only 4 datasets in the atlas**, all on ArcGIS Online (its
own APIs need a key), and **NSTA only via its ArcGIS Online org**. Registering them doesn't add data; it marks what
we already have.

## What Tobler sees (all additive; noted in docs/mcp-tools.md before release)

- `find_datasets` and `get_dataset`: `publisher_id` (when matched) and `trusted` (true/false).
- `find_datasets` input `trusted_only: true`. Trusted datasets also get a small ranking boost.
- `publisher` shows the registry name when matched; `get_dataset` keeps the original credit line as
  `publisher_credit`. *This changes the text of an existing field*, so it needs a note to Tobler first.
- Two new D1 columns, so a full reload. Doing licence classes in the same release means one reload, not two.

## Effort

About a day for the registry, matcher and weekly issue workflow; half a day for `trusted`, `trusted_only` and the
ranking boost; half a day for licence classes (same release). The first 250-candidate list comes out of the first
workflow run.

## Decisions for Rob

1. **Approval by GitHub issue checkboxes** (proposed), or would you rather edit a file?
2. **Should `publisher` show the registry name** when matched (original kept in `get_dataset`), or stay as crawled?
3. **Trusted means "authoritative body, own servers"** (host or org match only). Agreed? It leaves Esri copies and
   name-only matches out.
4. **Licence defaults from the registry** (for example, a body whose published policy is OGL for everything):
   leave out for now? It would turn "not stated" into an inferred licence, which has commercial consequences, so I'd
   only do it per publisher, with the policy URL as evidence and labelled "inferred", as for US federal works.
