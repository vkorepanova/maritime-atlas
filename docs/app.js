import * as maplibregl from 'https://unpkg.com/maplibre-gl@6.19.0/dist/maplibre-gl.mjs';

const BASE = new URL('./', import.meta.url);
const DATA = new URL('./data/', BASE);
const EMPTY = () => ({ type: 'FeatureCollection', features: [] });
const q = (selector) => document.querySelector(selector);
const number = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });
const views = {
  density: { title: 'Плотность AIS', description: 'Число уникальных судно-часов в пространственной ячейке. Это не масса груза.', count: 'Ячеек', heading: 'ПЛОТНОСТЬ СУДОХОДСТВА', detail: 'AIS-наблюдения / плотность' },
  flows: { title: 'Морские грузовые коридоры', description: 'Тоннаж указывается только при наличии проверенного источника для направления и года.', count: 'Маршрутов', heading: 'ГРУЗОВЫЕ КОРИДОРЫ', detail: 'Расчётные трассы / проверенный тоннаж' },
  vessels: { title: 'Позиции отдельных судов', description: 'Последняя принятая позиция AISStream. Данные не являются гарантированно полными или непрерывными.', count: 'Судов', heading: 'ДВИЖЕНИЕ СУДОВ', detail: 'AISStream / локальный приёмник' }
};
const state = { view: 'density', local: false, density: EMPTY(), flows: EMPTY(), vessels: EMPTY(), densityMeta: { kind: 'geojson' }, mapReady: false };

function url(file) { return new URL(file, DATA).href; }
async function getJson(path, fallback) {
  try {
    const response = await fetch(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const value = await response.json();
    return value;
  } catch (error) {
    console.warn('Data unavailable:', path, error);
    return fallback;
  }
}
function escape(value) {
  return String(value ?? '—').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}
function row(label, value) { return `<div class="popup-line"><strong>${escape(label)}:</strong> ${escape(value)}</div>`; }
function modeData() { return state[state.view]; }
function flowsFiltered() {
  const category = q('#cargo-filter').value;
  const verified = q('#verified-only').checked;
  return { ...state.flows, features: (state.flows.features || []).filter(f =>
    (category === 'all' || f.properties.cargo_category === category) && (!verified || f.properties.cargo_tonnes != null)
  ) };
}
function vesselsFiltered() {
  const text = q('#vessel-search').value.trim().toLowerCase();
  return { ...state.vessels, features: (state.vessels.features || []).filter(f =>
    !text || String(f.properties.name ?? '').toLowerCase().includes(text) || String(f.properties.mmsi ?? '').includes(text)
  ) };
}
function currentData() { return state.view === 'flows' ? flowsFiltered() : state.view === 'vessels' ? vesselsFiltered() : state.density; }
function showLegend() {
  const lines = state.view === 'density'
    ? [['#d8e9f0', 'Мало судно-часов'], ['#629ab4', 'Средняя плотность'], ['#194b72', 'Высокая плотность']]
    : state.view === 'flows'
    ? [['#41667e', 'Сухие грузы'], ['#a38b62', 'Уголь'], ['#7e88a6', 'Энергоносители'], ['#4e8e94', 'Контейнеры'], ['dashed', 'Нет подтверждённого тоннажа']]
    : [['#3e7894', 'Позиция судна AIS'], ['#a1adb7', 'Позиция старше 60 мин']];
  q('#legend').innerHTML = lines.map(([color, label]) => `<div class="legend-item"><span class="legend-swatch ${color === 'dashed' ? 'legend-dashed' : ''}" style="${color === 'dashed' ? '' : `background:${color}`} "></span>${escape(label)}</div>`).join('');
}
function setText(sel, value) { q(sel).textContent = value; }
function updatePanel() {
  const meta = views[state.view];
  setText('#metric-title', meta.title);
  setText('#metric-info', meta.description);
  setText('#metric-count-label', meta.count);
  setText('#map-heading', meta.heading);
  setText('#map-subheading', meta.detail);
  q('#flow-filters').hidden = state.view !== 'flows';
  q('#vessel-filters').hidden = state.view !== 'vessels';
  const data = currentData();
  setText('#metric-count', number.format(data.features.length));
  if (state.view === 'density') {
    const raster = state.densityMeta.kind === 'raster';
    setText('#metric-period', raster ? (state.densityMeta.period || 'см. источник') : (data.metadata?.period_end?.slice(0, 10) || 'нет данных'));
    setText('#data-status', raster ? 'Слой плотности импортирован из GeoTIFF. Период и единицы необходимо сверить с источником.' : data.features.length ? `AIS-ячейки: ${data.features.length}. Показатель: уникальные MMSI × часы.` : 'Нет данных плотности. Загрузите GeoTIFF World Bank либо соберите AIS и выполните build-density.');
    setText('#source-note', raster ? state.densityMeta.source : (data.metadata?.source || 'Источник пока отсутствует'));
  } else if (state.view === 'flows') {
    const confirmed = data.features.filter(f => f.properties.cargo_tonnes != null).length;
    setText('#metric-period', String(state.flows.metadata?.period || '—'));
    setText('#data-status', `Маршрутов: ${data.features.length}; с данными о тоннаже: ${confirmed}. Линии без тоннажа - только ориентиры.`);
    setText('#source-note', state.flows.metadata?.geometry_accuracy === 'sea_network_unverified' ? 'Линии рассчитаны по морской сети SeaRoute; не являются подтверждёнными AIS-траекториями.' : 'Геометрия схематичная; не является фактической AIS-траекторией.');
  } else {
    const stamps = data.features.map(f => Date.parse(f.properties.timestamp_utc)).filter(Number.isFinite);
    const latest = stamps.length ? new Date(Math.max(...stamps)).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC' : 'нет данных';
    setText('#metric-period', latest);
    setText('#data-status', data.features.length ? `${data.features.length} последних известных позиций AIS. Некоторые могут устареть.` : 'Нет позиций. Укажите ключ AISStream в .env и запустите локальный приёмник.');
    setText('#source-note', state.local ? 'Локальный API / приёмник AISStream. Поток не сохраняется на GitHub автоматически.' : 'GitHub Pages - статическая копия. Реальный поток через GitHub Pages недоступен.');
  }
  const count = state.view === 'density' && state.densityMeta.kind === 'raster' ? 'растровый слой' : `${data.features.length} объектов`;
  setText('#map-message', count);
  showLegend();
}
const map = new maplibregl.Map({
  container: 'map', style: 'https://tiles.openfreemap.org/styles/positron',
  center: [20, 12], zoom: 1.65, minZoom: 1, maxZoom: 15,
  attributionControl: true, preserveDrawingBuffer: true
});
map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
map.addControl(new maplibregl.ScaleControl({ maxWidth: 120, unit: 'nautical' }), 'bottom-right');

function syncLayers() {
  if (!state.mapReady) return;
  for (const [id, isActive] of [['density-fill', state.view === 'density'], ['density-image', state.view === 'density'], ['flows-known', state.view === 'flows'], ['flows-unknown', state.view === 'flows'], ['vessel-points', state.view === 'vessels']]) {
    if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', isActive ? 'visible' : 'none');
  }
  map.getSource('flows')?.setData(flowsFiltered());
  map.getSource('vessels')?.setData(vesselsFiltered());
  map.getSource('density')?.setData(state.density);
  updatePanel();
}
function attachPopup(layer, formatter) {
  map.on('click', layer, event => {
    const feature = event.features?.[0];
    if (!feature) return;
    new maplibregl.Popup({ maxWidth: '310px' }).setLngLat(event.lngLat).setHTML(formatter(feature.properties)).addTo(map);
  });
  map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = ''; });
}
function addLayers() {
  map.addSource('density', { type: 'geojson', data: state.density });
  map.addLayer({ id: 'density-fill', type: 'fill', source: 'density', paint: {
    'fill-color': ['interpolate', ['linear'], ['coalesce', ['get', 'ship_hours'], 0], 0, '#e5eff4', 1, '#b5d1df', 10, '#699db9', 100, '#286185', 1000, '#123c5d'],
    'fill-opacity': 0.8
  }});
  if (state.densityMeta.kind === 'raster') {
    map.addSource('density-image-source', { type: 'image', url: url(state.densityMeta.file || 'density.png'), coordinates: [[-180,85.051129],[180,85.051129],[180,-85.051129],[-180,-85.051129]] });
    map.addLayer({ id: 'density-image', type: 'raster', source: 'density-image-source', paint: { 'raster-opacity': 0.87 } });
  }
  map.addSource('flows', { type: 'geojson', data: flowsFiltered() });
  const cargoColor = ['match', ['get', 'cargo_category'], 'dry_bulk', '#41667e', 'coal', '#a38b62', 'energy', '#7e88a6', 'container', '#4e8e94', '#73838d'];
  map.addLayer({ id: 'flows-unknown', type: 'line', source: 'flows', filter: ['==', ['get', 'status'], 'tonnage_unverified'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: {
    'line-color': cargoColor, 'line-width': 2, 'line-dasharray': [3, 2], 'line-opacity': 0.74
  }});
  map.addLayer({ id: 'flows-known', type: 'line', source: 'flows', filter: ['!=', ['get', 'status'], 'tonnage_unverified'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: {
    'line-color': cargoColor, 'line-width': ['interpolate', ['linear'], ['to-number', ['get', 'cargo_tonnes'], 0], 0, 1.5, 1000000, 2.5, 100000000, 6, 1000000000, 12], 'line-opacity': 0.9
  }});
  map.addSource('vessels', { type: 'geojson', data: vesselsFiltered() });
  map.addLayer({ id: 'vessel-points', type: 'circle', source: 'vessels', paint: {
    'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, 3.8, 8, 7],
    'circle-color': ['case', ['==', ['get', 'stale'], true], '#a1adb7', '#3e7894'],
    'circle-stroke-color': '#fff', 'circle-stroke-width': 1.3, 'circle-opacity': 0.88
  }});
  attachPopup('density-fill', p => `<div class="popup-title">Плотность судоходства</div>${row('Судно-часы', number.format(p.ship_hours))}${row('Судов по MMSI', number.format(p.vessels))}${row('Позиционных сообщений', number.format(p.positions))}`);
  const flowPopup = p => `<div class="popup-title">${escape(p.name_ru)}</div>${row('Груз', p.cargo_ru)}${row('Через', p.via)}${row('Год', p.year)}${row('Тоннаж, т', p.cargo_tonnes === null || p.cargo_tonnes === 'null' ? 'Нет подтверждённых данных' : number.format(Number(p.cargo_tonnes)))}${row('Траектория', p.geometry_method === 'searoute_network' ? 'Расчёт по морской сети' : 'Схематичная')}${p.source_url && p.source_url !== 'null' ? row('Источник', p.source_url) : ''}`;
  attachPopup('flows-known', flowPopup);
  attachPopup('flows-unknown', flowPopup);
  attachPopup('vessel-points', p => `<div class="popup-title">${escape(p.name)}</div>${row('MMSI', p.mmsi)}${row('Скорость, уз', p.speed_knots)}${row('Курс, °', p.course_degrees)}${row('Приём UTC', p.timestamp_utc)}${row('Источник', p.source)}`);
  state.mapReady = true;
  syncLayers();
}
function setView(view) {
  state.view = view;
  for (const tab of document.querySelectorAll('.tab')) {
    const active = tab.dataset.view === view;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  }
  syncLayers();
}
function saveFile(data, filename, type) {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(blob);
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
}
function exportData(format) {
  const data = currentData();
  if (format === 'geojson') return saveFile(JSON.stringify(data, null, 2), `${state.view}.geojson`, 'application/geo+json');
  if (format === 'csv') {
    const items = data.features.map(f => ({...f.properties, geometry: JSON.stringify(f.geometry)}));
    const fields = [...new Set(items.flatMap(Object.keys))];
    const escapeCsv = value => `"${String(value ?? '').replaceAll('"','""')}"`;
    return saveFile([fields.join(','), ...items.map(item => fields.map(key => escapeCsv(item[key])).join(','))].join('\n'), `${state.view}.csv`, 'text/csv;charset=utf-8');
  }
  try { map.getCanvas().toBlob(blob => blob && saveFile(blob, `${state.view}.png`, 'image/png')); }
  catch { alert('Экспорт PNG недоступен для этого картографического источника. GeoJSON и CSV сохраняются отдельно.'); }
}

for (const tab of document.querySelectorAll('.tab')) tab.addEventListener('click', () => setView(tab.dataset.view));
q('#cargo-filter').addEventListener('change', syncLayers);
q('#verified-only').addEventListener('change', syncLayers);
q('#vessel-search').addEventListener('input', syncLayers);
for (const format of ['geojson', 'csv', 'png']) q(`#download-${format}`).addEventListener('click', () => exportData(format));

async function loadVessels() {
  const endpoint = state.local ? '/api/vessels' : url('vessels.geojson');
  state.vessels = await getJson(endpoint, EMPTY());
  state.vessels.features = (state.vessels.features || []).map(f => ({...f, properties: {...f.properties, stale: Date.now() - (Date.parse(f.properties.timestamp_utc) || 0) > 3600000}}));
  if (state.view === 'vessels') syncLayers();
}
async function initialize() {
  const health = await getJson('/api/health', {});
  state.local = health.mode === 'local';
  setText('#connection-status', state.local ? 'Локальный API подключён' : 'GitHub Pages / статические слои');
  [state.density, state.flows, state.densityMeta] = await Promise.all([
    getJson(url('density.geojson'), EMPTY()),
    getJson(url('flows.geojson'), EMPTY()),
    getJson(url('density_meta.json'), { kind: 'geojson' })
  ]);
  await loadVessels();
  if (map.loaded()) addLayers(); else map.once('load', addLayers);
  window.setInterval(loadVessels, 15000);
}
initialize();
