# US licences: what the data says (17 Nov 2026)

Findings only. No licence has been changed. Counts are passing US datasets from `results/spike-us` (70,831).

## The short version

The handover said licence detection doesn't recognise "public domain" wording. That turns out to be wrong:
the open-licence pattern in `atlas/quality.py` already matches "public domain", and the 6 US datasets that say so
are already marked open. The real problem is that **US services almost never state a licence in anything we crawl**.

- 49 of 70,831 passing US datasets are marked open (0.07%).
- 15,552 (22%) have no licence text at all.
- Most of the rest have credits rather than a licence: the ArcGIS `copyrightText` field, which US publishers use
  for "who made this" ("Source: U.S. Census Bureau", "King County", "NOAA Office for Coastal Management").
- Wording a looser pattern could pick up is rare: "no restrictions on use" 21, "freely distributed" 13. Worth
  adding, but it moves a few dozen datasets, not thousands.

So better wording rules won't fix US licences. There are two routes, and the second is your decision.

## Route 1: join to catalogue records (engineering, no licence judgement)

Licences for US data usually live in the catalogue, not the service: the `licenseInfo` on an ArcGIS Hub or Portal
item, or the licence on a data.gov record. We already read `licenseInfo` from portal items
(`crawl_portals.py`), but only 158 of 2,076 US catalogues gave records we could join. This is gap 2b in the
handover. Possible ways in:
- Federated ArcGIS Server services often carry a `serviceItemId`, pointing at the Portal item with the licence.
  We don't store it yet.
- data.gov's CKAN API lists the ArcGIS REST URLs for many federal and state datasets, which gives a join on URL.

Expected result: real, publisher-stated licences, kept as "unknown" where the publisher says nothing.

## Route 2: a rule for US federal works (your call: commercial consequences)

Works made by US federal employees aren't covered by copyright in the US (17 U.S.C. §105). A rule could mark
datasets from federal agencies as "US government work: public domain in the US". 6,106 passing datasets have a
`central-gov` publisher (NOAA ~2,800, USFS ~1,150, Census 766, BLM ~800, BOEM 129, USGS 67...).

Reasons for caution:
- It's inferred, not stated by the publisher. Principle: "Licence unknown stays unknown".
- Federal services often carry data from contractors, universities and states, which §105 doesn't cover. One of
  the most common US credits is "NOAA NCCOS, Marine Geospatial Ecology Lab, Duke University".
- §105 is a US rule. Rights outside the US aren't settled by it.
- It doesn't apply to state and local government (51k of the 70k), which make up most of the US index.

If you want it, a safer form is a separate field ("likely public domain: US federal work"), shown as such and not
counted as an open licence until a publisher statement or catalogue record confirms it.

## Suggestion

Do route 1 first (gap 2b). Add the "no restrictions" and "freely distributed" wording as a small tweak. Decide on
route 2 once we see how far route 1 gets.
