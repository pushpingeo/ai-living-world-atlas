/* AI Living World Atlas: MCP server (Streamable HTTP, stateless JSON responses).
   Private for now: every request needs the key, as "Authorization: Bearer <key>", "X-Api-Key: <key>",
   or "?key=<key>" for clients that can't set headers. */
import VOCAB from "./vocab.json";
import AREAS from "./country_areas.json";

const SERVER = { name: "ai-living-world-atlas", version: "0.1.0" };
const PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"];
const FEATURE_PREF = ["arcgis-featureserver", "wfs", "arcgis-mapserver", "geojson"];

/* ---------------- tool definitions ---------------- */
const TOOLS = [
  {
    name: "find_datasets",
    description:
      "Find public map datasets covering a place, ranked so the ones whose extent best matches the area come first " +
      "(zoom out for national/global layers, in for local ones). Filter by concept (what the data is, e.g. protected-area), " +
      "ISO theme, role, service capability and minimum detail. Use `vocabulary` for valid concept and theme ids. " +
      "Returns dataset ids for get_dataset and fetch_features. Coverage: the UK, Europe, the US, Canada, Australia and New Zealand in depth, plus global datasets (protected areas, power plants, mines, terrain, water, settlements). Elsewhere, expect mainly global layers.",
    inputSchema: {
      type: "object",
      properties: {
        lon: { type: "number", description: "Longitude of a point of interest (WGS84)" },
        lat: { type: "number", description: "Latitude of a point of interest (WGS84)" },
        radius_km: { type: "number", description: "Size of the area around the point, default 5" },
        bbox: { type: "array", items: { type: "number" }, minItems: 4, maxItems: 4, description: "[west, south, east, north] instead of a point" },
        concept: { type: "string", description: "Concept id, e.g. protected-area, flood-risk, school" },
        theme: { type: "string", description: "ISO 19115 topic category code, e.g. environment, transportation" },
        role: { type: "string", enum: VOCAB.roles },
        capability: { type: "string", enum: VOCAB.capabilities, description: "Only datasets with an endpoint that can do this" },
        min_detail: { type: "string", enum: Object.keys(VOCAB.detail_levels), description: "At least this detailed (datasets with unknown detail are kept unless known_detail_only)" },
        known_detail_only: { type: "boolean" },
        text: { type: "string", description: "Words to search for in the title, publisher, tags (concepts, themes, keywords) and the start of the description. All words must match; words of 4+ letters also match as prefixes (therm → thermal); \"quoted phrases\" match exactly. Works for any area size, up to the whole world." },
        fold_duplicates: { type: "boolean", description: "Fold results with the same title and much the same extent into the best-ranked one, listed under also_available_from. Default true." },
        browser_ready: { type: "boolean", description: "Only datasets a web page can load directly (CORS)" },
        geometry: { type: "string", enum: ["point", "line", "polygon"], description: "Only datasets with layers of this geometry (datasets whose geometry isn't recorded, such as most WFS layers, are kept)" },
        include_other_countries: { type: "boolean", description: "Also return datasets from national publishers whose country doesn't touch the area. Off by default: such layers usually claim a wider extent than they hold." },
        limit: { type: "integer", minimum: 1, maximum: 100, description: "Default 20" },
      },
    },
  },
  {
    name: "get_dataset",
    description: "Full record for one dataset: publisher description, licence, themes and concepts (with where they came from), " +
      "detail and extent notes, and every endpoint with what it can do and a ready-to-use request URL.",
    inputSchema: { type: "object", properties: { id: { type: "string" } }, required: ["id"] },
  },
  {
    name: "fetch_features",
    description: "Fetch features from a dataset within an area, as GeoJSON in WGS84. Geometry is simplified to suit the area, " +
      "and results are capped, so use counts for totals and a smaller area for detail. Works for datasets with a 'query' capability.",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "Dataset id from find_datasets" },
        lon: { type: "number" }, lat: { type: "number" }, radius_km: { type: "number", description: "Default 2" },
        bbox: { type: "array", items: { type: "number" }, minItems: 4, maxItems: 4 },
        where: { type: "string", description: "Optional ArcGIS SQL filter, e.g. \"STATUS='Designated'\" (ArcGIS endpoints only)" },
        text: { type: "string", description: "Only features with this text in a name-like field (name, title, road number…), e.g. 'M9' or 'Kipoi'. ArcGIS endpoints: searched on the server; others: filtered after fetching." },
        limit: { type: "integer", minimum: 1, maximum: 500, description: "Default 100" },
        include_geometry: { type: "boolean", description: "Default true; false returns attributes only" },
      },
      required: ["id"],
    },
  },
  {
    name: "vocabulary",
    description: "The controlled lists: ISO 19115 themes, concepts (with definitions and their theme), roles, capabilities and detail levels.",
    inputSchema: { type: "object", properties: {} },
  },
];

/* ---------------- helpers ---------------- */
const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json", ...cors(), ...extra } });
const cors = () => ({
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization, content-type, x-api-key, mcp-protocol-version, mcp-session-id",
  "access-control-allow-methods": "POST, GET, OPTIONS",
});

function authorised(req, env) {
  const key = env.ATLAS_KEY;
  if (!key) return false; // no key configured: refuse everything rather than run open
  const url = new URL(req.url);
  const given = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "") ||
    req.headers.get("x-api-key") || url.searchParams.get("key") || "";
  if (given.length !== key.length) return false;
  let diff = 0;
  for (let i = 0; i < key.length; i++) diff |= key.charCodeAt(i) ^ given.charCodeAt(i);
  return diff === 0;
}

function areaOf(lon, lat, radiusKm) {
  const dLat = radiusKm / 111.32;
  const dLon = radiusKm / (111.32 * Math.max(Math.cos((lat * Math.PI) / 180), 0.05));
  return [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
}

function queryArea(a, defaultKm) {
  if (Array.isArray(a.bbox) && a.bbox.length === 4) return a.bbox.map(Number);
  if (typeof a.lon === "number" && typeof a.lat === "number") return areaOf(a.lon, a.lat, a.radius_km || defaultKm);
  throw new Error("Give either lon and lat, or bbox [west, south, east, north].");
}

function geoArea(b) {
  const lat = ((b[1] + b[3]) / 2) * Math.PI / 180;
  return Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]) * Math.max(Math.cos(lat), 0.05);
}

function fit(b, v) {
  const i = [Math.max(b[0], v[0]), Math.max(b[1], v[1]), Math.min(b[2], v[2]), Math.min(b[3], v[3])];
  if (i[0] >= i[2] || i[1] >= i[3]) return 0;
  const av = geoArea(v);
  const ai = geoArea(i);
  const ab = Math.max(geoArea(b), av * 1e-4);
  const cov = ai / av, spec = ai / ab;
  // Size match on a log scale: a global layer for a 10 km site isn't a perfect fit, but it isn't zero either
  // (with a plain ratio every regional or global layer scored 0 for a small area, so ranking fell back to
  // quality score and local layers with inflated extents came first).
  const sizeMatch = 1 / (1 + Math.abs(Math.log10(Math.max(ab, 1e-12) / Math.max(av, 1e-12))) / 2);
  return cov * Math.min(1, Math.max(spec, sizeMatch));
}

const unwrap = (s) => (s ? s.split(",").filter(Boolean) : []);

// Dataset details come from the viewer's detail shards on GitHub Pages. Since 17 Nov they are gzipped and keyed by
// 3 characters (dz/xxx.json.gz); the old layout (d/xx.json) is tried if the new one isn't there. A file that arrives
// already unzipped is read as it is. (The viewer layout change on 17 Nov broke this for ~1 hour: keep them in step.)
async function readShard(url) {
  const r = await fetch(url, { cf: { cacheTtl: 3600 } });
  if (!r.ok) return null;
  const buf = await r.arrayBuffer();
  const b = new Uint8Array(buf);
  if (b[0] === 0x1f && b[1] === 0x8b) {
    const s = new Response(buf).body.pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(s).text());
  }
  return JSON.parse(new TextDecoder().decode(buf));
}

async function details(env, id) {
  const shard = (await readShard(`${env.DATA_BASE}dz/${id.slice(0, 3)}.json.gz`))
    || (await readShard(`${env.DATA_BASE}d/${id.slice(0, 2)}.json`));
  return (shard && shard[id]) || null;
}

const info = (e) => { try { return JSON.parse(e.info || "{}"); } catch { return {}; } };
const sep = (u) => (u.includes("?") ? "&" : "?");

function usage(e) {
  const inf = info(e);
  const caps = e.capabilities || [];
  const out = {};
  if (e.protocol === "arcgis-featureserver" || (e.protocol === "arcgis-mapserver" && caps.includes("query")))
    out.query_url = `${e.url}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson&geometry={west},{south},{east},{north}&geometryType=esriGeometryEnvelope&inSR=4326`;
  if (e.protocol === "arcgis-mapserver" && caps.includes("render"))
    out.image_url = `${e.service_url}/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&f=image&layers=show:${e.layer_name}`;
  if (e.protocol === "arcgis-mapserver" && caps.includes("tiles")) out.tile_url = `${e.service_url}/tile/{z}/{y}/{x}`;
  if (e.protocol === "arcgis-imageserver") out.image_url = `${e.service_url}/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png&f=image`;
  if (e.protocol === "wms")
    out.image_url = `${e.service_url}${sep(e.service_url)}service=WMS&request=GetMap&version=1.1.1&layers=${encodeURIComponent(e.layer_name)}&styles=&srs=EPSG:3857&bbox={bbox-epsg-3857}&width=256&height=256&format=image/png&transparent=true`;
  if (e.protocol === "wfs") {
    const fmt = (inf.output_formats || []).find((x) => /json/i.test(x));
    out.query_url = `${e.service_url}${sep(e.service_url)}service=WFS&request=GetFeature&version=1.1.0&typeName=${encodeURIComponent(e.layer_name)}&srsName=urn:ogc:def:crs:OGC:1.3:CRS84&bbox={west},{south},{east},{north},urn:ogc:def:crs:OGC:1.3:CRS84` + (fmt ? `&outputFormat=${encodeURIComponent(fmt)}` : "");
    if (!fmt) out.note = "This WFS only offers GML.";
  }
  if (e.protocol === "wmts" && inf.tile_template) out.tile_template = inf.tile_template;
  return out;
}

/* ---------------- countries an area touches ---------------- */
// Each country with its waters (3 degrees round it), from Natural Earth. A national publisher's layer is about its
// own country whatever extent it declares, so search leaves out those whose country doesn't touch the area.
const EUROPE = new Set("AD AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS SE SI SK SM UA VA XK".split(" "));
const ringsOf = (g) => (g.type === "Polygon" ? [g.coordinates[0]] : g.coordinates.map((p) => p[0]));
const COUNTRIES = AREAS.features.map((f) => {
  const rings = ringsOf(f.geometry);
  const xs = rings.flat().map((p) => p[0]), ys = rings.flat().map((p) => p[1]);
  return { iso: f.properties.iso2, rings, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
});
function inRing([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
// Countries whose area meets the box: a vertex of the country inside the box, or a point of the box inside the
// country. Edges crossing with no vertex either side are missed, which the 3-degree margin makes rare.
function countriesTouching(v) {
  const [w, s, e, n] = v;
  const pts = [[(w + e) / 2, (s + n) / 2], [w, s], [w, n], [e, s], [e, n]];
  const out = new Set();
  for (const c of COUNTRIES) {
    if (c.bbox[0] > e || c.bbox[2] < w || c.bbox[1] > n || c.bbox[3] < s) continue;
    if (c.rings.some((r) => r.some(([x, y]) => x >= w && x <= e && y >= s && y <= n)) || pts.some((p) => c.rings.some((r) => inRing(p, r)))) out.add(c.iso);
  }
  if ([...out].some((c) => EUROPE.has(c))) out.add("EU");
  return out;
}


/* ---------------- spatial index (18 Nov) ---------------- */
// Quadtree cell keys, built by atlas/api_data.py (cell_keys): keep the two in step. A dataset sits at the finest level
// where its extent spans at most 2 x 2 cells, with one key per cell, prefixed by its home country (and by concept in
// the concept keys). A search reads, for each home it keeps: the exact cells over the area at every coarser level (the
// bigger datasets) and every key under the area's own cells (the area's size and smaller). Keys are our own digits and
// ISO codes, so they go into the SQL as literals (D1 allows only 100 bound parameters).
const MAX_LEVEL = 18;
function cellLevel(x0, y0, x1, y1) {
  for (let lv = MAX_LEVEL; lv >= 0; lv--) {
    const w = 360 / 2 ** lv, h = 180 / 2 ** lv;
    if (Math.floor((x1 + 180) / w) - Math.floor((x0 + 180) / w) <= 1 && Math.floor((y1 + 90) / h) - Math.floor((y0 + 90) / h) <= 1) return lv;
  }
  return 0;
}
function quadkey(ix, iy, lv) {
  let k = "";
  for (let b = lv - 1; b >= 0; b--) k += String(((iy >> b) & 1) * 2 + ((ix >> b) & 1));
  return k;
}
function cellsAt(v, lv) {
  const w = 360 / 2 ** lv, h = 180 / 2 ** lv, top = 2 ** lv - 1, out = [];
  const cx = (x) => Math.min(Math.max(Math.floor((x + 180) / w), 0), top), cy = (y) => Math.min(Math.max(Math.floor((y + 90) / h), 0), top);
  for (let ix = cx(v[0]); ix <= cx(v[2]); ix++) for (let iy = cy(v[1]); iy <= cy(v[3]); iy++) out.push(quadkey(ix, iy, lv));
  return out;
}
// SQL selecting the ids of datasets whose cells meet area v, for the given homes and optional concept.
// Ranges are read at the finest level where the area spans at most RANGE_SPAN cells a side: finer ranges hug the area
// more closely (fewer keys read from outside it) at the cost of more terms.
const RANGE_SPAN = 4;
function spanLevel(a, span) {
  for (let lv = MAX_LEVEL; lv >= 0; lv--) {
    const w = 360 / 2 ** lv, h = 180 / 2 ** lv;
    if (Math.floor((a[2] + 180) / w) - Math.floor((a[0] + 180) / w) < span && Math.floor((a[3] + 90) / h) - Math.floor((a[1] + 90) / h) < span) return lv;
  }
  return 0;
}
// OR terms as a balanced tree: SQLite refuses expressions more than 100 deep, which a flat chain of 160 ORs is.
const orTree = (t) => (t.length === 1 ? t[0] : `(${orTree(t.slice(0, t.length >> 1))} OR ${orTree(t.slice(t.length >> 1))})`);
// SQL selecting the ids (with repeats) of datasets whose cells meet area v, for the given homes and optional concept.
function cellSelect(v, homes, concept, span = RANGE_SPAN, box = true) {
  const e = 1e-9; // a hair wider, so a dataset whose extent only touches the area's edge isn't lost to rounding
  const a = [Math.max(-180, v[0] - e), Math.max(-90, v[1] - e), Math.min(180, v[2] + e), Math.min(90, v[3] + e)];
  const lq = spanLevel(a, span);
  const pre = concept ? `c:${concept}|` : "";
  const lit = (k) => `'${k.replace(/'/g, "''")}'`;
  const exact = [], ranges = [];
  for (const h of homes) {
    for (let lv = 0; lv < lq; lv++) for (const c of cellsAt(a, lv)) exact.push(lit(`${pre}${h}:${c}`));
    for (const c of cellsAt(a, lq)) ranges.push(`(key >= ${lit(`${pre}${h}:${c}`)} AND key < ${lit(`${pre}${h}:${c}4`)})`);
  }
  // Plain SELECT (DISTINCT here makes SQLite scan the id index instead); "id IN (...)" dedupes.
  // x0..y1: the dataset's extent rounded outwards, so datasets whose cell meets the area but whose extent doesn't are
  // dropped here, before any lookup.
  return `SELECT id FROM ds_cell WHERE ${orTree([`key IN (${exact.join(",") || "''"})`, ...ranges])}` + (box ?
    ` AND x0 <= ${+a[2].toFixed(6)} AND x1 >= ${+a[0].toFixed(6)} AND y0 <= ${+a[3].toFixed(6)} AND y1 >= ${+a[1].toFixed(6)}` : "");
}

/* ---------------- tools ---------------- */
const CAND = 3000;

// Publisher types in the order an agent should trust a copy: a government's own service before an aggregator's.
const AUTH = { "central-gov": 1, "regional-gov": 1, "international": 1, "public-body": 0.95, "local-gov": 0.9,
  "academic": 0.8, "curated-collection": 0.7, "civil-society": 0.7, "business": 0.6, "unknown": 0.5 };
// Areas larger than this (square degrees) without text: the extent indexes don't narrow much, so candidates are read
// best-score-first and the read stops at the cap, instead of sorting every row by fit (that overloaded D1, 17 Nov).
const BIG_AREA = 25; // ~5° x 5°; 400 still let a Gulf of Mexico search (234) read most of the table (18 Nov)
const COUNT_CAP = 10000;
// Large areas without a concept: up to PROBE cell keys, read through the cells; more, and the SAMPLE best-scored
// datasets world-wide are read instead (18 Nov).
const PROBE = 20000, SAMPLE = 60000;
const HUGE = 20000; // square degrees (an ocean, a few continents): always many datasets, so no probe
// The cell paths return every match as a slim row (what ranking and folding need), up to SLIM_CAP; full rows are then
// read for the kept results only.
const SLIM = "d.id, d.title, d.publisher, d.ptype, d.score, d.xmin, d.ymin, d.xmax, d.ymax, d.xsus";
const SLIM_CAP = 20000;

// User text -> FTS5 query: words ANDed, 4+ letter words as prefixes, "quoted phrases" kept. Never passes FTS syntax through.
function ftsQuery(text) {
  const parts = [];
  const s = String(text || "");
  for (const m of s.matchAll(/"([^"]+)"|([^\s"]+)/g)) {
    const words = (m[1] || m[2]).normalize("NFKD").replace(/[\u0300-\u036f]/g, "").match(/[\p{L}\p{N}]+/gu) || [];
    if (!words.length) continue;
    if (m[1]) parts.push(`"${words.join(" ")}"`);
    else for (const w of words) {
      if (/^(and|or|not|near|the|of|in|for)$/i.test(w)) continue; // search operators and filler aren't search words
      parts.push(w.length >= 4 ? `"${w}"*` : `"${w}"`);
    }
  }
  return parts.join(" ");
}

const normTitle = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[^\p{L}\p{N}]+/gu, " ").trim();
function overlapShare(a, b) {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  if (w <= 0 || h <= 0) return 0;
  const area = (x) => Math.max((x[2] - x[0]) * (x[3] - x[1]), 1e-12);
  return (w * h) / Math.max(area(a), area(b)); // share of the larger: both extents must be much the same
}

async function findDatasets(env, a) {
  const v = queryArea(a, 5);
  if (a.geometry && !["point", "line", "polygon"].includes(a.geometry)) throw new Error("geometry must be point, line or polygon");
  let mdm;
  if (a.min_detail) {
    mdm = VOCAB.detail_levels[a.min_detail];
    if (mdm === undefined) throw new Error(`min_detail must be one of ${Object.keys(VOCAB.detail_levels).join(", ")}`);
  }
  const touched = a.include_other_countries ? null : [...countriesTouching(v)].filter((c) => /^[A-Z]{2}$/.test(c));
  // touched includes "EU" when the area meets a European country; datasets about Europe as a whole have home "EU".
  // The filters, with column prefix P: "d." normally, "+d." on the cell path, where the unary plus stops SQLite from
  // reaching for the extent or rank indexes instead of starting from the cell keys.
  const filters = (P) => {
    const where = [`${P}xmin <= ?`, `${P}xmax >= ?`, `${P}ymin <= ?`, `${P}ymax >= ?`];
    const params = [v[2], v[0], v[3], v[1]];
    if (!a.include_low_quality) where.push(`${P}pass = 1`);
    if (a.browser_ready) where.push(`${P}cors = 1`);
    if (a.role) { where.push(`${P}role = ?`); params.push(a.role); }
    if (a.concept) { where.push(`${P}concepts LIKE ?`); params.push(`%,${a.concept},%`); }
    if (a.theme) { where.push(`${P}themes LIKE ?`); params.push(`%,${a.theme},%`); }
    if (a.capability) { where.push(`${P}caps LIKE ?`); params.push(`%,${a.capability},%`); }
    if (a.geometry) { where.push(`(${P}gtypes LIKE ? OR ${P}gtypes = '' OR ${P}gtypes IS NULL)`); params.push(`%,${a.geometry},%`); }
    if (touched) where.push(`(${P}home = '' OR ${P}home IS NULL${touched.length ? ` OR ${P}home IN (${touched.map((c) => `'${c}'`).join(",")})` : ""})`);
    if (mdm !== undefined) { where.push(a.known_detail_only ? `${P}detail_m <= ?` : `(${P}detail_m <= ? OR ${P}detail_m IS NULL)`); params.push(mdm); }
    return [where.join(" AND "), params];
  };
  const [cond, params] = filters("d.");
  const va = Math.max((v[2] - v[0]) * (v[3] - v[1]), 1e-9);
  const q = a.text ? ftsQuery(a.text) : "";
  if (a.text && !q) throw new Error("text has no searchable words");
  const sizeOrder = "CASE WHEN d.area > 0 THEN MAX(d.area / ?, ? / d.area) ELSE 1e18 END";
  let sql, countSql = null, binds, countBinds, how, index = "extent", sampled = false, slim = false, probeRows = 0;
  // The cell index serves every search except text (which has its own index) and a search across all countries.
  // An area over many countries (all of Europe is 50) gets coarser ranges, which keeps the SQL well under D1's 100 KB.
  const homes = touched ? ["", ...touched] : null, span = (touched && touched.length > 8 ? 2 : RANGE_SPAN);
  const cells = touched && !a.include_low_quality && !q ? cellSelect(v, homes, a.concept, span) : null;
  let useCells = !!cells && (a.concept || va <= BIG_AREA);
  if (cells && !useCells && va <= HUGE) {
    // A large area without a concept: cheap through the cells where the area holds few datasets (Nigeria: 2k), costly
    // where it holds many (the US: 90k). Count the keys (without the extent test, so the count reads at most PROBE).
    const pr = await env.DB.prepare(`SELECT COUNT(*) AS n FROM (${cellSelect(v, homes, null, span, false)} LIMIT ${PROBE})`).all();
    probeRows = pr.meta?.rows_read ?? 0;
    useCells = pr.results[0].n < PROBE;
  }
  if (q) {
    // Full-text: only rows matching the words are read, whatever the area.
    const fts = "SELECT id, rank FROM ds_fts WHERE ds_fts MATCH ? ORDER BY rank LIMIT 20000";
    sql = `SELECT d.*, f.rank AS rel FROM (${fts}) f CROSS JOIN datasets d ON d.id = f.id WHERE ${cond} ORDER BY f.rank LIMIT ${CAND}`;
    countSql = `SELECT COUNT(*) AS n FROM (SELECT 1 FROM (${fts}) f CROSS JOIN datasets d ON d.id = f.id WHERE ${cond} LIMIT ${COUNT_CAP})`;
    binds = [q, ...params]; countBinds = [q, ...params]; how = "text";
  } else if (useCells) {
    // Spatial index: only datasets with a cell over the area (and of the concept, if given) are looked up, and every
    // match comes back as a slim row, so the count is exact and ranking sees them all (no SQL sort or count).
    const [pcond, pparams] = filters("+d.");
    sql = `SELECT ${SLIM} FROM datasets d WHERE d.id IN (${cells}) AND ${pcond} LIMIT ${SLIM_CAP + 1}`;
    binds = pparams; how = va > BIG_AREA ? "large-area" : "area"; index = "cells"; slim = true;
  } else if (va > BIG_AREA && cells) {
    // A large area holding many datasets: read the best-scored datasets world-wide (their extent and home come from
    // the rank index, no lookup), keep those in the area, and look up only the first few thousand of them.
    const [pcond, pparams] = filters("+d.");
    const near = touched.length ? ` AND (home = '' OR home IS NULL OR home IN (${touched.map((c) => `'${c}'`).join(",")}))` : " AND (home = '' OR home IS NULL)";
    const top = `SELECT id FROM (SELECT id, xmin, xmax, ymin, ymax, home FROM datasets ORDER BY pass DESC, score DESC LIMIT ${SAMPLE}) ` +
      `WHERE xmin <= ? AND xmax >= ? AND ymin <= ? AND ymax >= ?${near} LIMIT ${2 * CAND}`;
    sql = `SELECT ${SLIM} FROM (${top}) c CROSS JOIN datasets d ON d.id = c.id WHERE ${pcond}`;
    binds = [v[2], v[0], v[3], v[1], ...pparams]; how = "large-area"; index = "rank"; sampled = true; slim = true;
  } else if (va > BIG_AREA) {
    sql = `SELECT d.* FROM datasets d WHERE ${cond} ORDER BY d.pass DESC, d.score DESC LIMIT ${CAND}`;
    countSql = `SELECT COUNT(*) AS n FROM (SELECT 1 FROM datasets d WHERE ${cond} LIMIT ${COUNT_CAP})`;
    binds = params; countBinds = params; how = "large-area";
  } else {
    // Candidates nearest in size to the area come first, so the cap drops the far-too-big and far-too-small ones.
    sql = `SELECT d.* FROM datasets d WHERE ${cond} ORDER BY ${sizeOrder} LIMIT ${CAND}`;
    countSql = `SELECT COUNT(*) AS n FROM (SELECT 1 FROM datasets d WHERE ${cond} LIMIT ${COUNT_CAP})`;
    binds = [...params, va, va]; countBinds = params; how = "area";
  }
  const [res, cntRes] = await Promise.all([env.DB.prepare(sql).bind(...binds).all(),
    countSql ? env.DB.prepare(countSql).bind(...countBinds).all() : null]);
  const over = slim && res.results.length > SLIM_CAP; // more matches than we take: rank the first SLIM_CAP
  const results = over ? res.results.slice(0, SLIM_CAP) : res.results;
  const cnt = countSql ? cntRes.results[0] : { n: results.length };
  // Text matches: relevance (FTS rank, more negative is better) first, then publisher authority; fit matters less,
  // since a world-wide search makes every extent look small. Area searches: fit, then authority, then score.
  const best = results.length && q ? Math.min(...results.map((r) => r.rel)) : 0;
  const ranked = results
    .map((r) => {
      const f = fit([r.xmin, r.ymin, r.xmax, r.ymax], v) * (r.xsus ? 0.2 : 1);
      const auth = AUTH[r.ptype] ?? 0.5;
      const rel = q ? (best < 0 ? r.rel / best : 1) : 1; // 1 for the best match, smaller for weaker ones
      return { r, f, s: q ? rel * auth * (0.8 + 0.2 * Math.sqrt(f)) : f * auth };
    })
    .sort((x, y) => y.s - x.s || y.r.score - x.r.score);
  const limit = Math.min(a.limit || 20, 100);
  const kept = [];
  const fold = a.fold_duplicates !== false;
  for (const x of ranked) {
    if (kept.length >= limit && !fold) break;
    const b = [x.r.xmin, x.r.ymin, x.r.xmax, x.r.ymax], t = fold ? normTitle(x.r.title) : "";
    const twin = fold && kept.find((k) => k.t === t && overlapShare(k.b, b) > 0.5);
    if (twin) { (twin.also = twin.also || []).push({ id: x.r.id, publisher: x.r.publisher, publisher_type: x.r.ptype }); continue; }
    if (kept.length < limit) kept.push({ ...x, t, b }); // when full, keep scanning only to fold twins
  }
  const n = cnt ? cnt.n : results.length;
  const capped = countSql ? n >= COUNT_CAP : sampled || over;
  let fullRows = null;
  if (slim && kept.length) {
    // Full rows for the kept results only (ids are ours, but quote them anyway; D1 allows 100 bound parameters)
    const ids = kept.map((k) => `'${String(k.r.id).replace(/'/g, "''")}'`).join(",");
    fullRows = await env.DB.prepare(`SELECT * FROM datasets WHERE id IN (${ids})`).all();
    const byId = new Map(fullRows.results.map((r) => [r.id, r]));
    for (const k of kept) k.r = byId.get(k.r.id) || k.r;
  }
  return {
    area: v.map((n) => +n.toFixed(5)),
    matches: n,
    ...(capped ? { matches_capped: true } : {}),
    results: kept.map(({ r, f, also }) => ({
      id: r.id, title: r.title, publisher: r.publisher, publisher_type: r.ptype, role: r.role,
      fit: +f.toFixed(3), coverage: r.coverage, detail: r.detail || null,
      themes: unwrap(r.themes), themes_source: r.themes_src || null, concepts: unwrap(r.concepts),
      protocols: unwrap(r.protocols), capabilities: unwrap(r.caps),
      licence: r.licence || "not stated", open_licence: !!r.open_licence, quality_score: r.score,
      extent_may_be_overstated: !!r.xsus, browser_ready: !!r.cors,
      geometry: unwrap(r.gtypes), country: r.home || null,
      bbox: [r.xmin, r.ymin, r.xmax, r.ymax].map((n) => +n.toFixed(5)),
      ...(also && also.length ? { also_available_from: also.slice(0, 10) } : {}),
    })),
    ...(touched ? { countries_in_area: touched } : {}),
    search: how,
    ...(a.debug ? { rows_read: (res.meta?.rows_read ?? 0) + (cntRes?.meta?.rows_read ?? 0) + probeRows + (fullRows?.meta?.rows_read ?? 0),
      query_rows_read: res.meta?.rows_read ?? null, count_rows_read: cntRes ? (cntRes.meta?.rows_read ?? null) : 0, probe_rows_read: probeRows,
      detail_rows_read: fullRows?.meta?.rows_read ?? 0, index } : {}),
    note: "fit = how well the dataset's extent matches the area (1 = same size and place)." +
      (sampled ? " Large area holding many datasets: candidates (and matches) are the best-scored datasets in it, not every one; add text or a concept to narrow."
        : over ? ` matches counts up to ${SLIM_CAP}; a smaller area or a concept narrows it.` : capped ? ` matches counts up to ${COUNT_CAP}.` : "") +
      (touched ? " National publishers' datasets are included only for the countries in the area (include_other_countries to widen)." : ""),
  };
}

async function getDataset(env, a) {
  const row = await env.DB.prepare("SELECT * FROM datasets WHERE id = ?").bind(a.id).first();
  if (!row) throw new Error(`No dataset with id ${a.id}`);
  const d = (await details(env, a.id)) || {};
  return {
    id: row.id, title: row.title, publisher: row.publisher, publisher_type: row.ptype, role: row.role,
    description: d.abstract || "", licence: d.licence || row.licence || "not stated", open_licence: !!row.open_licence,
    catalogue_page: d.landing_page || null, keywords: d.keywords || [],
    themes: unwrap(row.themes), themes_source: row.themes_src || null, concepts: unwrap(row.concepts),
    tagging_reason: d.tag_reason || null,
    coverage: row.coverage, detail: row.detail || null, detail_m: row.detail_m, detail_source: d.detail_source || null,
    bbox: [row.xmin, row.ymin, row.xmax, row.ymax], extent_source: d.extent_source || "declared", extent_flags: d.extent_flags || [],
    quality_score: row.score, passes_quality_bar: !!row.pass,
    endpoints: (d.endpoints || []).map((e, i) => ({
      index: i, protocol: e.protocol, url: e.url.split("#")[0], layer: e.layer_name, capabilities: e.capabilities,
      ...(e.plan ? { plan: e.plan } : {}),
      browser_ready: e.cors, last_check: e.check, details: info(e), use: usage(e),
    })),
  };
}

// Name-like text fields of an ArcGIS layer, read from its description (cached by Cloudflare for a day).
const NAMEY = /name|title|label|number|ref|road|route|site|project|plant|mine|facility|nom|nombre|naam/i;
async function textFields(url) {
  try {
    const r = await fetch(`${url}?f=json`, { headers: { "user-agent": "AI-Living-World-Atlas-MCP/0.1" }, cf: { cacheTtl: 86400 }, signal: AbortSignal.timeout(10000) });
    const j = await r.json();
    return (j.fields || []).filter((f) => f.type === "esriFieldTypeString" && NAMEY.test(`${f.name} ${f.alias || ""}`)).map((f) => f.name).slice(0, 8);
  } catch { return []; }
}
const sqlText = (s) => String(s).replace(/'/g, "''").toUpperCase().slice(0, 80);

async function fetchFeatures(env, a) {
  const d = await details(env, a.id);
  if (!d) throw new Error(`No dataset with id ${a.id}`);
  const v = queryArea(a, 2);
  const limit = Math.min(a.limit || 100, 500);
  const eps = (d.endpoints || []).filter((e) => (e.capabilities || []).includes("query") && FEATURE_PREF.includes(e.protocol))
    .sort((x, y) => FEATURE_PREF.indexOf(x.protocol) - FEATURE_PREF.indexOf(y.protocol));
  if (!eps.length) throw new Error("This dataset has no endpoint that can return features. Use get_dataset for image or tile endpoints.");
  const errors = [];
  for (const e of eps) {
    if (e.protocol === "geojson") {
      // A download-only dataset the atlas hosts as one GeoJSON file (e.g. GEM's trackers): filter it here.
      try { return await fileFeatures(e, d, a, v, limit); } catch (err) { errors.push(`geojson: ${String(err.message || err)}`); continue; }
    }
    let url, alts = [];
    const [x0, y0, x1, y1] = v.map((n) => n.toFixed(6));
    if (e.protocol === "wfs") {
      const fmt = (info(e).output_formats || []).find((x) => /json/i.test(x));
      if (!fmt) { errors.push("WFS offers GML only"); continue; }
      // The bbox must say it's in degrees: without a CRS, WFS reads it in the layer's own CRS (e.g. British
      // National Grid metres), so a lon/lat box lands off Cornwall and returns nothing. CRS84 keeps lon/lat order.
      const head = `${e.service_url}${sep(e.service_url)}service=WFS&request=GetFeature&typeName=${encodeURIComponent(e.layer_name)}&outputFormat=${encodeURIComponent(fmt)}&maxFeatures=${limit}`;
      const crs84 = "urn:ogc:def:crs:OGC:1.3:CRS84";
      url = `${head}&version=1.1.0&srsName=${crs84}&bbox=${x0},${y0},${x1},${y1},${crs84}`;
      alts = [`${head}&version=1.0.0&srsName=EPSG:4326&bbox=${x0},${y0},${x1},${y1},EPSG:4326`];
    } else {
      const tol = ((v[2] - v[0]) / 1000).toPrecision(2);
      let where = a.where || "1=1";
      if (a.text) {
        const fields = await textFields(e.url);
        if (fields.length) where = `(${where}) AND (${fields.map((f) => `UPPER(${f}) LIKE '%${sqlText(a.text)}%'`).join(" OR ")})`;
        else e._filterAfter = true;
      }
      url = `${e.url}/query?where=${encodeURIComponent(where)}&geometry=${x0},${y0},${x1},${y1}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&outSR=4326&f=geojson&resultRecordCount=${limit}&maxAllowableOffset=${tol}&geometryPrecision=6&returnGeometry=${a.include_geometry === false ? "false" : "true"}`;
    }
    try {
      let r, gj;
      for (const u of [url, ...alts]) {
        r = await fetch(u, { headers: { "user-agent": "AI-Living-World-Atlas-MCP/0.1" }, signal: AbortSignal.timeout(25000) });
        if (!r.ok) continue;
        const t = await r.text();
        try { gj = JSON.parse(t); } catch { gj = { error: { message: t.trimStart().startsWith("<") ? "the server answered in XML (an exception report)" : "not JSON" } }; }
        if (Array.isArray(gj.features)) break;
      }
      if (!r.ok && !gj) { errors.push(`${e.protocol}: HTTP ${r.status}`); continue; }
      if (!Array.isArray(gj.features) && a.text && !e._filterAfter && e.protocol !== "wfs") {
        // The server refused the text filter (some don't allow UPPER or LIKE): fetch without it and filter here.
        e._filterAfter = true;
        const plain = url.replace(/where=[^&]*/, `where=${encodeURIComponent(a.where || "1=1")}`).replace(/resultRecordCount=\d+/, "resultRecordCount=2000");
        const r2 = await fetch(plain, { headers: { "user-agent": "AI-Living-World-Atlas-MCP/0.1" }, signal: AbortSignal.timeout(25000) });
        gj = r2.ok ? await r2.json() : {};
      }
      if (!Array.isArray(gj.features)) { errors.push(`${e.protocol}: ${gj.error?.message || "not GeoJSON"}`); continue; }
      let raw = gj.features;
      if (a.text && (e.protocol === "wfs" || e._filterAfter)) {
        const t = String(a.text).toLowerCase();
        raw = raw.filter((f) => Object.values(f.properties || {}).some((x) => typeof x === "string" && x.toLowerCase().includes(t)));
      }
      const feats = raw.slice(0, limit).map((f) => ({
        type: "Feature",
        geometry: a.include_geometry === false ? null : f.geometry,
        properties: Object.fromEntries(Object.entries(f.properties || {}).slice(0, 40)
          .map(([k, val]) => [k, typeof val === "string" && val.length > 300 ? val.slice(0, 300) + "…" : val])),
      }));
      return {
        dataset: a.id, endpoint: { protocol: e.protocol, url: e.url.split("#")[0] }, area: v.map((n) => +n.toFixed(5)),
        returned: feats.length, may_be_more: feats.length >= limit || !!gj.exceededTransferLimit || !!gj.properties?.exceededTransferLimit,
        licence: d.licence || "not stated",
        type: "FeatureCollection", features: feats,
      };
    } catch (err) {
      errors.push(`${e.protocol}: ${err.name === "TimeoutError" ? "timed out" : String(err.message || err)}`);
    }
  }
  throw new Error("Couldn't fetch features: " + errors.join("; "));
}

function featBbox(g) {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  const walk = (c) => { if (typeof c[0] === "number") { w = Math.min(w, c[0]); e = Math.max(e, c[0]); s = Math.min(s, c[1]); n = Math.max(n, c[1]); } else c.forEach(walk); };
  if (g && g.coordinates) walk(g.coordinates);
  return [w, s, e, n];
}

// Hosted files (atlas/files.py): files/<id>/index.json lists gzipped GeoJSON tiles with their extents; only tiles
// touching the area are read. A plain .geojson (the first layout) still works.
const MAX_TILES = 40;       // without text: the nearest tiles are enough to return a sample
const MAX_TILES_TEXT = 300; // with text: every tile in the area, or a name search misses (tiles are small and gzipped)
async function fileFeatures(e, d, a, v, limit) {
  const t = a.text ? String(a.text).toLowerCase() : "";
  const keep = (f) => {
    const b = featBbox(f.geometry);
    if (b[0] > v[2] || b[2] < v[0] || b[1] > v[3] || b[3] < v[1]) return false;
    return !t || Object.values(f.properties || {}).some((x) => typeof x === "string" && x.toLowerCase().includes(t));
  };
  let hits = [], source = null, partial = false;
  if (/index\.json$/.test(e.url)) {
    const r = await fetch(e.url, { cf: { cacheTtl: 3600 }, signal: AbortSignal.timeout(15000) });
    if (!r.ok) throw new Error(`index: HTTP ${r.status}`);
    const idx = await r.json();
    source = idx.atlas_source || null;
    const base = e.url.replace(/index\.json$/, "");
    const near = idx.tiles.filter((x) => !(x.bbox[0] > v[2] || x.bbox[2] < v[0] || x.bbox[1] > v[3] || x.bbox[3] < v[1]));
    const cap = t ? MAX_TILES_TEXT : MAX_TILES;
    if (near.length > cap) partial = true;
    // tiles in batches of 12 at a time: a world-wide text search reads ~200 small tiles (21 s one by one, cold)
    const todo = near.slice(0, cap);
    for (let i = 0; i < todo.length; i += 12) {
      const batch = todo.slice(i, i + 12);
      const got = await Promise.all(batch.map((tile) => readShard(`${base}${tile.key}.json.gz`)));
      got.forEach((gj, j) => {
        if (!gj || !Array.isArray(gj.features)) throw new Error(`tile ${batch[j].key} unreadable`);
        for (const f of gj.features) if (keep(f)) hits.push(f);
      });
      if (hits.length >= limit * 4 && !t) { partial = partial || i + 12 < near.length; break; }
    }
  } else {
    const r = await fetch(e.url, { cf: { cacheTtl: 3600 }, signal: AbortSignal.timeout(25000) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const gj = await r.json();
    if (!Array.isArray(gj.features)) throw new Error("not GeoJSON");
    source = gj.atlas_source || null;
    hits = gj.features.filter(keep);
  }
  const feats = hits.slice(0, limit).map((f) => ({
    type: "Feature", geometry: a.include_geometry === false ? null : f.geometry,
    properties: Object.fromEntries(Object.entries(f.properties || {}).slice(0, 40)
      .map(([k, val]) => [k, typeof val === "string" && val.length > 300 ? val.slice(0, 300) + "…" : val])),
  }));
  return {
    dataset: a.id, endpoint: { protocol: "geojson", url: e.url }, area: v.map((n) => +n.toFixed(5)),
    returned: feats.length, matched: hits.length, ...(partial ? { matched_is_partial: true } : {}),
    may_be_more: partial || hits.length > feats.length,
    licence: d.licence || "not stated", ...(source ? { source } : {}),
    ...(a.where ? { note: "where isn't supported for hosted files; use text" } : {}),
    type: "FeatureCollection", features: feats,
  };
}

const HANDLERS = {
  find_datasets: findDatasets,
  get_dataset: getDataset,
  fetch_features: fetchFeatures,
  vocabulary: async () => VOCAB,
};

/* ---------------- MCP JSON-RPC ---------------- */
async function rpc(env, msg) {
  const { id, method, params = {} } = msg;
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  const fail = (code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });
  switch (method) {
    case "initialize": {
      const v = PROTOCOLS.includes(params.protocolVersion) ? params.protocolVersion : PROTOCOLS[0];
      return ok({
        protocolVersion: v, capabilities: { tools: {} }, serverInfo: SERVER,
        instructions: "An index of public map services (UK, Canada, Australia, NZ, US, plus global sources so far), ranked by how well each dataset's extent fits your area. " +
          "Typical flow: find_datasets for a place and concept, get_dataset for licence and endpoints, fetch_features for data. " +
          "Publisher text is quoted as published; themes and concepts marked 'ai' were assigned by a model from fixed lists.",
      });
    }
    case "ping": return ok({});
    case "tools/list": return ok({ tools: TOOLS });
    case "tools/call": {
      const h = HANDLERS[params.name];
      if (!h) return fail(-32602, `Unknown tool ${params.name}`);
      try {
        const result = await h(env, params.arguments || {});
        return ok({ content: [{ type: "text", text: JSON.stringify(result) }], structuredContent: result });
      } catch (err) {
        return ok({ content: [{ type: "text", text: String(err.message || err) }], isError: true });
      }
    }
    default:
      if (method && method.startsWith("notifications/")) return null;
      return fail(-32601, `Method not found: ${method}`);
  }
}

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors() });
    const url = new URL(req.url);
    if (url.pathname === "/" && req.method === "GET")
      return json({ name: SERVER.name, mcp_endpoint: "/mcp", auth: "Bearer key required" });
    if (url.pathname !== "/mcp") return json({ error: "not found" }, 404);
    if (!authorised(req, env)) return json({ error: "unauthorised" }, 401, { "www-authenticate": "Bearer" });
    if (req.method === "GET") return new Response("Server-sent events are not used by this server.", { status: 405, headers: cors() });
    if (req.method !== "POST") return json({ error: "method not allowed" }, 405);
    let body;
    try { body = await req.json(); } catch { return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400); }
    if (Array.isArray(body)) {
      const out = (await Promise.all(body.map((m) => rpc(env, m)))).filter(Boolean);
      return out.length ? json(out) : new Response(null, { status: 202, headers: cors() });
    }
    const res = await rpc(env, body);
    return res ? json(res) : new Response(null, { status: 202, headers: cors() });
  },
};
