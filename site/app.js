/* AI Living World Atlas viewer.
   The index is one compact JSON file; details load per dataset from small shards.
   The list shows datasets covering the current view, best-fitting extent first, so
   zooming in moves you from national and global layers down to local ones. */
"use strict";

const DATA = "data/";
const MAX_LIST = 150;
const MAX_FEATURES = 1000;
const PALETTE = ["#0f6b5c", "#b4441c", "#3b5ba5", "#a1347a", "#7a6a12", "#1f7a99", "#6b3fa0", "#2f7d32"];
const LABEL = {
  role: { data: "Data", imagery: "Imagery", elevation: "Elevation", basemap: "Basemap" },
  protocols: {
    "arcgis-featureserver": "ArcGIS feature", "arcgis-mapserver": "ArcGIS map", "arcgis-imageserver": "ArcGIS image",
    "arcgis-vectortileserver": "ArcGIS vector tiles", wms: "WMS", wfs: "WFS", wmts: "WMTS", wcs: "WCS",
  },
  themes: {
    farming: "Farming", biota: "Biota", boundaries: "Boundaries", climatologyMeteorologyAtmosphere: "Climate",
    economy: "Economy", elevation: "Elevation", environment: "Environment", geoscientificInformation: "Geoscience",
    health: "Health", imageryBaseMapsEarthCover: "Imagery & land cover", intelligenceMilitary: "Military",
    inlandWaters: "Inland waters", location: "Location", oceans: "Oceans", planningCadastre: "Planning",
    society: "Society", structure: "Structure", transportation: "Transport", utilitiesCommunication: "Utilities",
  },
};
const label = (facet, v) => (LABEL[facet] && LABEL[facet][v]) || v.replace(/-/g, " ");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let META, ROWS = [];
const sel = { role: new Set(), themes: new Set(), concepts: new Set(), protocols: new Set(), caps: new Set() };
const shardCache = {};
const added = [];
let openId = null;

/* ---------- map ---------- */
const params = new URLSearchParams(location.search);
const BLANK = { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#eef1f2" } }] };
const map = new maplibregl.Map({
  container: "map",
  style: params.get("style") === "blank" ? BLANK : "https://tiles.openfreemap.org/styles/positron",
  center: [-3.2, 54.6], zoom: 4.6, hash: true, attributionControl: { compact: true },
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
map.addControl(new maplibregl.ScaleControl(), "bottom-left");
// the page can start in a hidden or half-sized panel; keep the canvas matched to its box
new ResizeObserver(() => map.resize()).observe(document.getElementById("map"));

function hoverBox(bbox) {
  const src = map.getSource("hover");
  if (!src) return;
  if (!bbox) return src.setData({ type: "FeatureCollection", features: [] });
  const [x0, y0, x1, y1] = bbox;
  src.setData({ type: "Feature", geometry: { type: "Polygon", coordinates: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]] } });
}

/* ---------- data ---------- */
const BY_ID = new Map();
const loadedTiles = new Set();
const MAX_TILES = { a: 36, b: 36 };  // don't fetch local tiles for a continent-wide view

function addRows(raw) {
  const f = META.fields;
  const ix = Object.fromEntries(f.map((k, i) => [k, i]));
  for (const a of raw) {
    if (BY_ID.has(a[ix.id])) continue;
    BY_ID.set(a[ix.id], {
      id: a[ix.id], title: a[ix.title], publisher: a[ix.publisher], ptype: META.ptypes[a[ix.ptype]],
      role: META.roles[a[ix.role]], bbox: a[ix.bbox], pass: !!a[ix.pass], score: a[ix.score],
      themes: a[ix.themes].map((i) => META.themes[i]), concepts: a[ix.concepts].map((i) => META.concepts[i]),
      protocols: a[ix.protocols].map((i) => META.protocols[i]), caps: a[ix.caps].map((i) => META.caps[i]),
      detail: a[ix.detail], cors: !!a[ix.cors], xsus: ix.xsus !== undefined && !!a[ix.xsus],
      text: (a[ix.title] + " " + a[ix.publisher]).toLowerCase(),
    });
  }
  ROWS = [...BY_ID.values()];
}

async function loadIndex() {
  META = await (await fetch(DATA + "meta.json")).json();
  if (META.only_passing) document.getElementById("f-pass").closest("label").hidden = true;  // nothing else is published
  addRows(await (await fetch(DATA + "big.json")).json());
}

/* fetch the tiles covering the view (finest level only when zoomed in enough); true if anything new arrived */
async function loadTiles(v) {
  const wanted = [];
  let tooWide = false;
  for (const { deg, name } of META.levels) {
    const cells = [];
    for (let tx = Math.floor((Math.max(v[0], -180) + 180) / deg); tx <= Math.floor((Math.min(v[2], 179.999) + 180) / deg); tx++)
      for (let ty = Math.floor((Math.max(v[1], -90) + 90) / deg); ty <= Math.floor((Math.min(v[3], 89.999) + 90) / deg); ty++)
        cells.push(`${name}_${tx}_${ty}`);
    if (cells.length > MAX_TILES[name]) { tooWide = true; continue; }
    for (const c of cells) if (META.tiles[c] && !loadedTiles.has(c)) wanted.push(c);
  }
  zoomHint = tooWide;
  if (!wanted.length) return false;
  wanted.forEach((c) => loadedTiles.add(c));
  const parts = await Promise.all(wanted.map((c) => fetch(`${DATA}t/${c}.json`).then((r) => r.json()).catch(() => [])));
  parts.forEach(addRows);
  return true;
}
let zoomHint = false;

/* Detail shards: meta.json says where they are and how they're keyed. Current layout: dz/<first 3 chars>.json.gz,
   unzipped here. A server that has already unzipped the file (or an older plain layout) is read as it comes. */
async function readShard(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  const buf = await r.arrayBuffer();
  const b = new Uint8Array(buf);
  if (b[0] === 0x1f && b[1] === 0x8b) {
    const s = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(s).text());
  }
  return JSON.parse(new TextDecoder().decode(buf));
}

async function details(id) {
  const n = META.detail_key || 2;
  const k = id.slice(0, n);
  const url = META.detail_dir ? `${DATA}${META.detail_dir}/${k}.json${META.detail_gz ? ".gz" : ""}` : `${DATA}d/${k}.json`;
  if (!shardCache[k]) shardCache[k] = readShard(url).catch((e) => { delete shardCache[k]; throw e; });
  return (await shardCache[k])[id];
}

/* ---------- filtering and ranking ---------- */
function area(b) {
  const lat = ((b[1] + b[3]) / 2) * Math.PI / 180;
  return Math.max(0, b[2] - b[0]) * Math.max(0, b[3] - b[1]) * Math.max(Math.cos(lat), 0.05);
}
function fit(b, v, av) {
  const i = [Math.max(b[0], v[0]), Math.max(b[1], v[1]), Math.min(b[2], v[2]), Math.min(b[3], v[3])];
  if (i[0] >= i[2] || i[1] >= i[3]) return -1;
  const ai = area(i);
  const ab = Math.max(area(b), av * 1e-4);
  const cov = ai / av;          // how much of the view the dataset covers
  const spec = ai / ab;         // how much of the dataset is in view
  return cov + spec > 0 ? (2 * cov * spec) / (cov + spec) : 0;
}

function matches(r, skip) {
  for (const facet of Object.keys(sel)) {
    if (facet === skip || !sel[facet].size) continue;
    const v = r[facet];
    if (Array.isArray(v) ? !v.some((x) => sel[facet].has(x)) : !sel[facet].has(v)) return false;
  }
  return true;
}

function update() {
  if (!META) return;
  const b = map.getBounds();
  const v = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
  loadTiles(v).then((fresh) => { if (fresh) update(); });
  const av = area(v);
  const q = document.getElementById("q").value.trim().toLowerCase();
  const onlyPass = document.getElementById("f-pass").checked;
  const onlyCors = document.getElementById("f-cors").checked;

  const inView = [];
  for (const r of ROWS) {
    if (onlyPass && !r.pass) continue;
    if (onlyCors && !r.cors) continue;
    if (q && !r.text.includes(q)) continue;
    const f = fit(r.bbox, v, av);
    if (f < 0) continue;
    r._fit = r.xsus ? f * 0.5 : f;  // an extent we suspect is overstated shouldn't win the ranking
    inView.push(r);
  }
  // facet counts: each facet counted with every other filter applied
  for (const el of document.querySelectorAll(".chips")) {
    const facet = el.dataset.facet;
    const counts = {};
    for (const r of inView) {
      if (!matches(r, facet)) continue;
      const vals = Array.isArray(r[facet]) ? r[facet] : [r[facet]];
      for (const x of vals) counts[x] = (counts[x] || 0) + 1;
    }
    const all = new Set([...Object.keys(counts), ...sel[facet]]);
    const items = [...all].sort((a, c) => (counts[c] || 0) - (counts[a] || 0));
    el.innerHTML = items.length
      ? items.map((x) => `<button class="chip ${sel[facet].has(x) ? "on" : ""} ${counts[x] ? "" : "zero"}" data-v="${esc(x)}">${esc(label(facet, x))}<span class="n">${(counts[x] || 0).toLocaleString()}</span></button>`).join("")
      : `<span class="k" style="color:var(--muted);font-size:12.5px">${facet === "concepts" && !META.tagged ? "Not tagged yet" : "None in view"}</span>`;
  }
  const hits = inView.filter((r) => matches(r, null));
  hits.sort((a, c) => c._fit - a._fit || c.score - a.score);
  document.getElementById("status").textContent =
    `${hits.length.toLocaleString()} datasets cover this view` + (hits.length > MAX_LIST ? `, best ${MAX_LIST} fits shown` : "") +
    (zoomHint ? ". Zoom in to see local datasets too." : "");
  renderList(hits.slice(0, MAX_LIST));
}

function renderList(items) {
  const ol = document.getElementById("list");
  ol.innerHTML = items.map((r) => `
    <li data-id="${r.id}" class="${r.id === openId ? "open" : ""}">
      <span class="fit" title="How well this dataset's extent matches the view"><i style="width:${Math.round(r._fit * 100)}%"></i></span>
      <div class="t">${esc(r.title)}</div>
      <div class="m">${esc(r.publisher)}${r.detail ? " · " + esc(r.detail) : ""}</div>
      <div class="tags"><span class="tag role">${esc(label("role", r.role))}</span>${r.protocols.map((p) => `<span class="tag">${esc(label("protocols", p))}</span>`).join("")}${r.themes.slice(0, 2).map((t) => `<span class="tag">${esc(label("themes", t))}</span>`).join("")}</div>
      ${r.id === openId ? '<div class="detail">Loading…</div>' : ""}
    </li>`).join("");
  if (openId) {
    const li = ol.querySelector(`li[data-id="${openId}"]`);
    if (li) showDetail(li, BY_ID.get(openId));
  }
}

/* ---------- details ---------- */
async function showDetail(li, r) {
  const box = li.querySelector(".detail");
  let d;
  try { d = await details(r.id); } catch (e) {
    console.warn(e);
    if (box) box.innerHTML = '<p class="no">Couldn\'t load the details for this dataset. Try again in a moment.</p>';
    return;
  }
  if (!box || !d) return;
  const eps = d.endpoints.map((e, i) => {
    const how = addMethod(e);
    return `<tr><td class="p">${esc(label("protocols", e.protocol))}${e.plan ? `<div class="k">${esc(e.plan)}</div>` : ""}</td>
      <td class="c">${esc((e.capabilities || []).join(", "))}${e.cors === false ? ' <span class="no" title="The server did not allow browser access from other sites">· may not draw here</span>' : ""}${e.status === "failing" ? ' <span class="no" title="The service did not answer at its last check. It is dropped if it stays down for two weeks.">· not answering</span>' : e.check === "fail" ? ' <span class="no" title="The service answered, but asking it for a sample of this layer failed at the last check">· sample request failed</span>' : ""}</td>
      <td>${how ? `<button data-add="${i}">Add</button>` : `<button disabled title="This kind of endpoint can't be drawn in the viewer yet">—</button>`}
        <button data-copy="${i}" title="Copy the address">URL</button></td></tr>`;
  }).join("");
  box.innerHTML = `
    ${d.abstract ? `<p class="abs">${esc(d.abstract)}</p>` : '<p class="k">No description from the publisher.</p>'}
    <p><span class="k">Licence:</span> ${esc(d.licence || "not stated")}${d.landing_page ? ` · <a href="${esc(d.landing_page)}" target="_blank" rel="noopener">catalogue page</a>` : ""}</p>
    ${r.themes.length ? `<p><span class="k">Themes${d.themes_source === "ai" ? " (AI-assigned)" : d.themes_source === "declared" ? " (publisher)" : ""}:</span> ${r.themes.map((t) => esc(label("themes", t))).join(", ")}${r.concepts.length ? ` · <span class="k">Concepts:</span> ${r.concepts.map((c) => esc(label("concepts", c))).join(", ")}` : ""}</p>` : ""}
    ${d.extent_flags && d.extent_flags.length ? `<p class="no">${d.extent_source === "measured" ? "Extent measured from the data (the service's own extent looked wrong)." : "The stated extent looks overstated (" + esc(d.extent_flags.join(", ")) + "); the data may cover much less."}</p>` : ""}
    <p><span class="k">Coverage:</span> ${esc(d.coverage || "?")}${d.detail_m ? ` · <span class="k">Detail:</span> ~${Math.round(d.detail_m)} m (${esc(d.detail_source)})` : ""} · <span class="k">Score:</span> ${r.score}</p>
    <table class="eps">${eps}</table>`;
  box.onclick = (ev) => ev.stopPropagation();
  box.querySelectorAll("[data-add]").forEach((b) => (b.onclick = () => addLayer(r, d.endpoints[+b.dataset.add], b)));
  box.querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => {
    navigator.clipboard?.writeText(d.endpoints[+b.dataset.copy].url.split("#")[0]);
    b.textContent = "Copied"; setTimeout(() => (b.textContent = "URL"), 1200);
  }));
}

/* ---------- adding layers ---------- */
const info = (e) => { try { return JSON.parse(e.info || "{}"); } catch { return {}; } };
const sep = (u) => (u.includes("?") ? "&" : "?");

function addMethod(e) {
  const caps = e.capabilities || [];
  const inf = info(e);
  switch (e.protocol) {
    case "arcgis-featureserver": return caps.includes("query") ? "features" : null;
    case "wfs": return wfsJson(e) ? "features" : null;  // GML-only servers can't be drawn here yet
    case "wms": return "image";
    case "arcgis-imageserver": return caps.includes("render") ? "image" : null;
    case "arcgis-mapserver":
      if (caps.includes("render")) return "image";
      if (caps.includes("tiles") && inf.web_mercator_standard) return "tiles";
      return null;
    case "wmts": return inf.tile_template && inf.web_mercator_standard ? "tiles" : null;
    default: return null;
  }
}

function wfsJson(e) {
  const f = (info(e).output_formats || []);
  return f.find((x) => /json/i.test(x)) || null;
}

function rasterUrl(e) {
  const svc = e.service_url;
  const name = e.layer_name;
  switch (e.protocol) {
    case "wms":
      return `${svc}${sep(svc)}service=WMS&request=GetMap&version=1.1.1&layers=${encodeURIComponent(name)}&styles=&srs=EPSG:3857&bbox={bbox-epsg-3857}&width=256&height=256&format=image/png&transparent=true`;
    case "arcgis-imageserver":
      return `${svc}/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png&f=image`;
    case "arcgis-mapserver":
      if (addMethod(e) === "tiles") return `${svc}/tile/{z}/{y}/{x}`;
      return `${svc}/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&f=image&layers=show:${encodeURIComponent(name)}`;
    case "wmts": {
      const inf = info(e);
      const tms = (inf.tile_matrix_sets || []).find((s) => /google|3857|900913|webmercator/i.test(s)) || (inf.tile_matrix_sets || [])[0];
      return inf.tile_template.replace("{TileMatrixSet}", tms).replace("{TileMatrix}", "{z}").replace("{TileRow}", "{y}")
        .replace("{TileCol}", "{x}").replace("{Style}", "default");
    }
  }
}

function featureUrl(e, v) {
  const [x0, y0, x1, y1] = v.map((n) => n.toFixed(6));
  if (e.protocol === "wfs") {
    const s = e.service_url;
    // The bbox must state its CRS, or WFS reads it in the layer's own CRS (e.g. British National Grid) and finds nothing.
    const crs84 = "urn:ogc:def:crs:OGC:1.3:CRS84";
    return `${s}${sep(s)}service=WFS&request=GetFeature&version=1.1.0&typeName=${encodeURIComponent(e.layer_name)}&outputFormat=${encodeURIComponent(wfsJson(e))}&srsName=${crs84}&bbox=${x0},${y0},${x1},${y1},${crs84}&maxFeatures=${MAX_FEATURES}`;
  }
  // ask the server to simplify to about one screen pixel, so a national layer doesn't arrive at survey precision
  const tol = ((v[2] - v[0]) / map.getCanvas().clientWidth).toPrecision(2);
  return `${e.url}/query?where=1%3D1&geometry=${x0},${y0},${x1},${y1}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&outSR=4326&f=geojson&resultRecordCount=${MAX_FEATURES}&maxAllowableOffset=${tol}&geometryPrecision=5`;
}

function viewBox() {
  const b = map.getBounds();
  return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
}

function addLayer(r, e, btn) {
  const how = addMethod(e);
  const id = "L" + Math.random().toString(36).slice(2, 8);
  const color = PALETTE[added.length % PALETTE.length];
  const entry = { id, title: r.title, kind: how, e, color, opacity: how === "features" ? 1 : 0.8, status: "loading", layers: [] };
  added.push(entry);
  if (how === "features") {
    map.addSource(id, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    entry.layers = [
      map.addLayer({ id: id + "-f", type: "fill", source: id, filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": color, "fill-opacity": 0.18 } }) && id + "-f",
      map.addLayer({ id: id + "-l", type: "line", source: id, filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": color, "line-width": 1.4 } }) && id + "-l",
      map.addLayer({ id: id + "-p", type: "circle", source: id, filter: ["==", ["geometry-type"], "Point"], paint: { "circle-color": color, "circle-radius": 4, "circle-stroke-color": "#fff", "circle-stroke-width": 1 } }) && id + "-p",
    ];
    for (const lid of entry.layers) map.on("click", lid, (ev) => popup(ev, entry));
    refreshFeatures(entry);
  } else {
    map.addSource(id, { type: "raster", tiles: [rasterUrl(e)], tileSize: 256 });
    map.addLayer({ id: id + "-r", type: "raster", source: id, paint: { "raster-opacity": entry.opacity } }, firstLabelLayer());
    entry.layers = [id + "-r"];
    entry.status = "ok";
  }
  if (btn) { btn.textContent = "Added"; btn.disabled = true; }
  renderAdded();
}

function firstLabelLayer() {
  const ls = map.getStyle().layers || [];
  const l = ls.find((x) => x.type === "symbol");
  return l ? l.id : undefined;
}

async function refreshFeatures(entry) {
  entry.status = "loading"; renderAdded();
  entry.ctrl?.abort();  // a newer view replaces any request still running
  const ctrl = (entry.ctrl = new AbortController());
  const timeout = setTimeout(() => ctrl.abort("timeout"), 30000);
  try {
    const r = await fetch(featureUrl(entry.e, viewBox()), { signal: ctrl.signal });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const gj = await r.json();
    if (!gj || !Array.isArray(gj.features)) throw new Error(gj?.error?.message || "not GeoJSON");
    map.getSource(entry.id)?.setData(gj);
    entry.status = gj.features.length >= MAX_FEATURES ? `first ${MAX_FEATURES} features in view` : `${gj.features.length} features in view`;
  } catch (err) {
    if (ctrl.signal.aborted && ctrl.signal.reason !== "timeout") return;  // superseded by a newer request
    entry.status = "error";
    entry.error = ctrl.signal.reason === "timeout" ? "The service took more than 30 seconds to answer. Try zooming in."
      : /Failed to fetch|NetworkError|Load failed/i.test(String(err))
      ? "The server blocked access from this page (no CORS) or is down."
      : String(err.message || err);
  } finally {
    clearTimeout(timeout);
  }
  renderAdded();
}

function popup(ev, entry) {
  const f = ev.features && ev.features[0];
  if (!f) return;
  const rows = Object.entries(f.properties || {}).slice(0, 14)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
  new maplibregl.Popup({ maxWidth: "320px" }).setLngLat(ev.lngLat)
    .setHTML(`<strong>${esc(entry.title)}</strong><table>${rows}</table>`).addTo(map);
}

function renderAdded() {
  const sec = document.getElementById("added");
  sec.hidden = !added.length;
  document.getElementById("added-list").innerHTML = added.map((a, i) => `
    <li><div class="row"><span class="sw" style="background:${a.color}"></span><span class="nm" title="${esc(a.title)}">${esc(a.title)}</span>
      <button class="x" data-rm="${i}" title="Remove">✕</button></div>
      <div class="st ${a.status === "error" ? "err" : ""}">${a.status === "error" ? esc(a.error) : a.kind === "features" ? esc(a.status) : a.status === "loading" ? "Loading…" : "Map image"}</div>
      <input type="range" min="0" max="1" step="0.05" value="${a.opacity}" data-op="${i}" aria-label="Opacity"></li>`).join("");
  sec.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => removeLayer(+b.dataset.rm)));
  sec.querySelectorAll("[data-op]").forEach((s) => (s.oninput = () => setOpacity(+s.dataset.op, +s.value)));
}

function setOpacity(i, v) {
  const a = added[i];
  a.opacity = v;
  for (const lid of a.layers) {
    const t = map.getLayer(lid)?.type;
    if (t === "raster") map.setPaintProperty(lid, "raster-opacity", v);
    if (t === "fill") map.setPaintProperty(lid, "fill-opacity", v * 0.2);
    if (t === "line") map.setPaintProperty(lid, "line-opacity", v);
    if (t === "circle") { map.setPaintProperty(lid, "circle-opacity", v); map.setPaintProperty(lid, "circle-stroke-opacity", v); }
  }
}

function removeLayer(i) {
  const a = added.splice(i, 1)[0];
  for (const lid of a.layers) if (map.getLayer(lid)) map.removeLayer(lid);
  if (map.getSource(a.id)) map.removeSource(a.id);
  renderAdded();
}

// raster errors arrive as map errors tagged with the source id
map.on("error", (ev) => {
  const a = added.find((x) => x.id === ev.sourceId);
  if (!a || a.status === "error") return;
  a.status = "error";
  a.error = "Tiles failed to load: the server may block access from this page (no CORS), need a key, or be down.";
  renderAdded();
});

/* ---------- wiring ---------- */
let timer;
const later = (fn, ms = 120) => { clearTimeout(timer); timer = setTimeout(fn, ms); };

document.getElementById("q").addEventListener("input", () => later(update, 200));
document.getElementById("f-pass").addEventListener("change", update);
document.getElementById("f-cors").addEventListener("change", update);
document.getElementById("controls").addEventListener("click", (ev) => {
  const c = ev.target.closest(".chip");
  if (!c) return;
  const facet = c.parentElement.dataset.facet;
  const v = c.dataset.v;
  sel[facet].has(v) ? sel[facet].delete(v) : sel[facet].add(v);
  update();
});
const list = document.getElementById("list");
list.addEventListener("click", (ev) => {
  const li = ev.target.closest("li");
  if (!li) return;
  openId = openId === li.dataset.id ? null : li.dataset.id;
  update();
});
list.addEventListener("mouseover", (ev) => {
  const li = ev.target.closest("li");
  hoverBox(li ? BY_ID.get(li.dataset.id)?.bbox : null);
});
list.addEventListener("mouseleave", () => hoverBox(null));

map.on("load", async () => {
  map.addSource("hover", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addLayer({ id: "hover-fill", type: "fill", source: "hover", paint: { "fill-color": "#0f6b5c", "fill-opacity": 0.06 } });
  map.addLayer({ id: "hover-line", type: "line", source: "hover", paint: { "line-color": "#0f6b5c", "line-width": 2 } });
  try {
    await loadIndex();
  } catch (err) {
    document.getElementById("status").textContent = "Couldn't load the index: " + err;
    return;
  }
  update();
  map.on("moveend", () => {
    later(update);
    for (const a of added) if (a.kind === "features") refreshFeatures(a);
  });
});
