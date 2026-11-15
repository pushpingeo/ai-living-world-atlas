"""What each endpoint can actually do, and what kind of thing it serves.

Agents pick an endpoint by capability: 'I need features I can filter' -> query; 'I need a picture
behind my map' -> tiles or render; 'I need pixel values' -> pixels. These verbs are the same across
ArcGIS and OGC so they can be compared.
"""
from __future__ import annotations

import json
import re

WEB_MERCATOR = {3857, 102100, 102113, 900913}

IMAGERY_WORDS = re.compile(r"\b(aerial|ortho|orthophoto|orthoimage|imagery|satellite|sentinel|landsat|planetscope|photograph|photo mosaic|rgb|false colour|false color|ndvi|apgb)\b", re.I)
ELEVATION_WORDS = re.compile(r"\b(lidar|dtm|dsm|dem|elevation|height model|terrain model|hillshade|bathymetr\w*|contours?)\b", re.I)
BASEMAP_WORDS = re.compile(r"\b(base ?map|background map|basemaps?|zoomstack|topographic map|street map|light grey|dark grey|vectormap|open ?street ?map|osm|reference map|canvas|world map)\b", re.I)


def tiling(tile_info: dict | None) -> dict:
    """Summarise an ArcGIS tileInfo block."""
    if not tile_info:
        return {}
    sr = tile_info.get("spatialReference") or {}
    wkid = sr.get("latestWkid") or sr.get("wkid")
    lods = tile_info.get("lods") or []
    levels = [l.get("level") for l in lods if l.get("level") is not None]
    origin = tile_info.get("origin") or {}
    std = wkid in WEB_MERCATOR and abs((origin.get("x") or 0) + 20037508.34) < 1 and tile_info.get("rows") in (256, 512)
    return {
        "tile_crs": wkid, "web_mercator_standard": bool(std), "tile_size": tile_info.get("rows"),
        "zoom_min": min(levels) if levels else None, "zoom_max": max(levels) if levels else None,
        "tile_format": tile_info.get("format"),
    }


def arcgis(stype: str, sj: dict, lj: dict | None = None) -> tuple[list[str], dict]:
    """Capabilities and specifics for an ArcGIS service (sj) or one of its layers (lj)."""
    caps_s = {c.strip().lower() for c in (sj.get("capabilities") or "").split(",") if c.strip()}
    caps_l = {c.strip().lower() for c in ((lj or {}).get("capabilities") or "").split(",") if c.strip()}
    caps = caps_s | caps_l
    out, info = [], {"protocol": f"arcgis-{stype.lower()}"}
    tiled = bool(sj.get("singleFusedMapCache") or sj.get("tileInfo")) and stype in ("MapServer", "ImageServer", "VectorTileServer")
    if stype == "FeatureServer":
        if "query" in caps or not caps:
            out.append("query")
        if "extract" in caps:
            out.append("download")
    elif stype == "MapServer":
        if "map" in caps:
            out.append("render")
        if "query" in caps and "tilesonly" not in caps:
            out.append("query")
        if lj and (lj.get("type") == "Raster Layer"):
            out = [c for c in out if c != "query"]
    elif stype == "ImageServer":
        if "image" in caps or not caps:
            out.append("render")
        for k, v in (("download", "download"), ("pixels", "pixels"), ("catalog", "catalog")):
            if k in caps:
                out.append(v)
        rfs = [r.get("name") for r in (sj.get("rasterFunctionInfos") or []) if r.get("name") and r.get("name") != "None"]
        if sj.get("allowRasterFunction") and rfs:
            out.append("raster-functions")
        info.update({
            "bands": sj.get("bandCount"), "pixel_type": sj.get("pixelType"),
            "data_type": (sj.get("serviceDataType") or "").replace("esriImageServiceDataType", "").lower() or None,
            "mosaic": "catalog" in caps, "raster_functions": rfs[:20],
            "band_names": [b for b in (sj.get("bandNames") or [])][:20] if sj.get("bandNames") else None,
            "multidimensional": bool(sj.get("hasMultidimensions")),
            "max_image_size": [sj.get("maxImageWidth"), sj.get("maxImageHeight")],
            "max_download_images": sj.get("maxDownloadImageCount"),
        })
        if sj.get("hasMultidimensions"):
            out.append("multidimensional")
    elif stype == "VectorTileServer":
        out.append("tiles")
        info["style_url"] = "resources/styles/root.json"
    if tiled and "tiles" not in out:
        out.append("tiles")
    if (lj or sj).get("timeInfo"):
        out.append("time")
    if lj is not None:
        aq = lj.get("advancedQueryCapabilities") or {}
        info.update({
            "max_record_count": lj.get("maxRecordCount") or sj.get("maxRecordCount"),
            "paging": aq.get("supportsPagination"),
            "query_formats": [f.strip() for f in (lj.get("supportedQueryFormats") or sj.get("supportedQueryFormats") or "").split(",") if f.strip()],
            "supports_statistics": aq.get("supportsStatistics"),
        })
    else:
        info["max_record_count"] = sj.get("maxRecordCount")
    if tiled:
        info.update(tiling(sj.get("tileInfo")))
        info["tiles_only"] = "tilesonly" in caps or ("map" not in caps and stype == "MapServer")
    return out, {k: v for k, v in info.items() if v not in (None, [], "", {})}


def role(row_like: dict) -> str:
    """data | imagery | elevation | basemap. Text clues only count alongside the right service shape."""
    caps = set(row_like.get("capabilities") or [])
    info = row_like.get("_info") or {}
    # titles only: abstracts mention imagery and terrain far too casually to be evidence
    text = " ".join(str(row_like.get(k) or "") for k in ("title", "service_title", "portal_title"))
    stype = row_like.get("service_type", "")
    is_raster = stype in ("arcgis-imageserver", "wcs") or row_like.get("geometry_type") == "raster"
    tile_only = "tiles" in caps and "query" not in caps
    if is_raster and (info.get("data_type") == "elevation" or ELEVATION_WORDS.search(text)):
        return "elevation"
    if is_raster and (info.get("data_type") in ("rgb", "processed") or (info.get("bands") or 0) >= 3 or IMAGERY_WORDS.search(text)):
        return "imagery"
    if (tile_only or stype in ("wmts", "arcgis-vectortileserver", "wms")) and IMAGERY_WORDS.search(text):
        return "imagery"
    if (tile_only or stype in ("wmts", "arcgis-vectortileserver")) and BASEMAP_WORDS.search(text):
        return "basemap"
    if stype == "wms" and BASEMAP_WORDS.search(row_like.get("title") or ""):
        return "basemap"
    return "data"


def dumps(info: dict) -> str:
    return json.dumps(info, separators=(",", ":"), default=str) if info else ""
