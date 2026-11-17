/* AI Living World Atlas: MCP server (Streamable HTTP, stateless JSON responses).
   Private for now: every request needs the key, as "Authorization: Bearer <key>", "X-Api-Key: <key>",
   or "?key=<key>" for clients that can't set headers. */
import VOCAB from "./vocab.json";

const SERVER = { name: "ai-living-world-atlas", version: "0.1.0" };
const PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"];
const FEATURE_PREF = ["arcgis-featureserver", "wfs", "arcgis-mapserver"];

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
        text: { type: "string", description: "Words that must appear in the title or publisher" },
        browser_ready: { type: "boolean", description: "Only datasets a web page can load directly (CORS)" },
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

async function details(env, id) {
  const r = await fetch(`${env.DATA_BASE}d/${id.slice(0, 2)}.json`, { cf: { cacheTtl: 3600 } });
  if (!r.ok) return null;
  const shard = await r.json();
  return shard[id] || null;
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
    out.query_url = `${e.service_url}${sep(e.service_url)}service=WFS&request=GetFeature&version=1.0.0&typeName=${encodeURIComponent(e.layer_name)}&srsName=EPSG:4326&bbox={west},{south},{east},{north}` + (fmt ? `&outputFormat=${encodeURIComponent(fmt)}` : "");
    if (!fmt) out.note = "This WFS only offers GML.";
  }
  if (e.protocol === "wmts" && inf.tile_template) out.tile_template = inf.tile_template;
  return out;
}

/* ---------------- tools ---------------- */
const CAND = 3000;

async function findDatasets(env, a) {
  const v = queryArea(a, 5);
  const where = ["xmin <= ?", "xmax >= ?", "ymin <= ?", "ymax >= ?"];
  const params = [v[2], v[0], v[3], v[1]];
  if (!a.include_low_quality) where.push("pass = 1");
  if (a.browser_ready) where.push("cors = 1");
  if (a.role) { where.push("role = ?"); params.push(a.role); }
  if (a.concept) { where.push("concepts LIKE ?"); params.push(`%,${a.concept},%`); }
  if (a.theme) { where.push("themes LIKE ?"); params.push(`%,${a.theme},%`); }
  if (a.capability) { where.push("caps LIKE ?"); params.push(`%,${a.capability},%`); }
  if (a.text) { where.push("(title LIKE ? OR publisher LIKE ?)"); params.push(`%${a.text}%`, `%${a.text}%`); }
  if (a.min_detail) {
    const m = VOCAB.detail_levels[a.min_detail];
    if (m === undefined) throw new Error(`min_detail must be one of ${Object.keys(VOCAB.detail_levels).join(", ")}`);
    where.push(a.known_detail_only ? "detail_m <= ?" : "(detail_m <= ? OR detail_m IS NULL)");
    params.push(m);
  }
  // Candidates nearest in size to the area come first, so the cap drops the far-too-big and far-too-small ones.
  const va = Math.max((v[2] - v[0]) * (v[3] - v[1]), 1e-9);
  const cond = where.join(" AND ");
  const sql = `SELECT * FROM datasets WHERE ${cond} ORDER BY CASE WHEN area > 0 THEN MAX(area / ?, ? / area) ELSE 1e18 END LIMIT ${CAND}`;
  const [{ results }, cnt] = await Promise.all([
    env.DB.prepare(sql).bind(...params, va, va).all(),
    env.DB.prepare(`SELECT COUNT(*) AS n FROM datasets WHERE ${cond}`).bind(...params).first(),
  ]);
  const ranked = results
    .map((r) => ({ r, f: fit([r.xmin, r.ymin, r.xmax, r.ymax], v) * (r.xsus ? 0.2 : 1) }))
    .sort((x, y) => y.f - x.f || y.r.score - x.r.score)
    .slice(0, Math.min(a.limit || 20, 100));
  return {
    area: v.map((n) => +n.toFixed(5)),
    matches: cnt ? cnt.n : results.length,
    results: ranked.map(({ r, f }) => ({
      id: r.id, title: r.title, publisher: r.publisher, publisher_type: r.ptype, role: r.role,
      fit: +f.toFixed(3), coverage: r.coverage, detail: r.detail || null,
      themes: unwrap(r.themes), themes_source: r.themes_src || null, concepts: unwrap(r.concepts),
      protocols: unwrap(r.protocols), capabilities: unwrap(r.caps),
      licence: r.licence || "not stated", open_licence: !!r.open_licence, quality_score: r.score,
      extent_may_be_overstated: !!r.xsus, browser_ready: !!r.cors,
      bbox: [r.xmin, r.ymin, r.xmax, r.ymax].map((n) => +n.toFixed(5)),
    })),
    note: "fit = how well the dataset's extent matches the area (1 = same size and place).",
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
    let url;
    const [x0, y0, x1, y1] = v.map((n) => n.toFixed(6));
    if (e.protocol === "wfs") {
      const fmt = (info(e).output_formats || []).find((x) => /json/i.test(x));
      if (!fmt) { errors.push("WFS offers GML only"); continue; }
      url = `${e.service_url}${sep(e.service_url)}service=WFS&request=GetFeature&version=1.0.0&typeName=${encodeURIComponent(e.layer_name)}&outputFormat=${encodeURIComponent(fmt)}&srsName=EPSG:4326&bbox=${x0},${y0},${x1},${y1}&maxFeatures=${limit}`;
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
      const r = await fetch(url, { headers: { "user-agent": "AI-Living-World-Atlas-MCP/0.1" }, signal: AbortSignal.timeout(25000) });
      if (!r.ok) { errors.push(`${e.protocol}: HTTP ${r.status}`); continue; }
      let gj = await r.json();
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
