/**
 * PropertyIQ — Property Valuation & Real-Time Locality Intelligence System
 * Full interactive frontend controller for maps, ML valuations, What-If simulation,
 * locality benchmarks, historical analytics, and viva documentation.
 */

// Application State
const state = {
  currentTab: 'overview',
  selectedPropertyId: 'PROP-0001',
  selectedLocalityId: 'LOC-ANDW',
  propertiesPage: 1,
  propertiesLimit: 12,
  mapInstance: null,
  compactMapInstance: null,
  cachedPropertyDetail: null,
  markerClusterGroup: null,
  localities: [],
  summary: null,
  activeWhatIf: null,
  currentPredictedPriceInr: null,
  lastMarketSnapshot: null
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupAutoMarketFeed();

  await loadLocalities();
  await loadSummary();
  await loadOverviewCharts();
  setupPropertyFilters();
  await loadProperties();
  setupWhatIfControls();
  setupLocalityCompareUI();
  await loadHistoricalTrends();
  await loadModelVivaMetrics();
});

// --- NAVIGATION CONTROLLER ---
function setupNavigation() {
  const tabBtns = document.querySelectorAll('.nav-tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  state.currentTab = tabId;
  document.querySelectorAll('.nav-tab-btn').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabId}`);
  });

  // Keep live feed values synchronized immediately on tab transition
  if (state.lastMarketSnapshot) {
    updateLiveKpisAndFeed(state.lastMarketSnapshot);
  }

  // Handle lazy map initialization
  if (tabId === 'map-explorer') {
    setTimeout(initFullMapExplorer, 100);
  } else if (tabId === 'property-detail' && state.selectedPropertyId && state.cachedPropertyDetail) {
    setTimeout(() => initCompactPropertyMap(state.selectedPropertyId, state.cachedPropertyDetail), 100);
  }
}

// --- OVERVIEW / SUMMARY & LIVE FEED CONTROLLER ---
async function loadSummary() {
  try {
    const res = await fetch('/api/summary');
    const data = await res.json();
    state.summary = data;

    // Fill real totals from the database
    if (data.total_properties != null) setKpiText('kpi-total-props', Number(data.total_properties).toLocaleString());
    if (data.total_localities != null) setKpiText('kpi-total-locs', String(data.total_localities));

    // Apply live market feed to KPIs and cross-tab indicators
    if (data.latest_snapshot) {
      state.lastMarketSnapshot = data.latest_snapshot;
      updateLiveKpisAndFeed(data.latest_snapshot);
    } else {
      updateLiveKpisAndFeed(data);
    }

    // Populate Working Example Property Card Action
    document.getElementById('example-prop-action').onclick = () => {
      openPropertyDetail('PROP-0001');
    };
  } catch (err) {
    console.error('Error loading summary:', err);
  }
}

// --- LIVE AUTO-UPDATING MARKET FEED (EVERY 5 SECONDS) ---
let marketFeedTimer = null;

function setupAutoMarketFeed() {
  if (marketFeedTimer) clearInterval(marketFeedTimer);
  // Auto-refresh the market simulation feed every 5 seconds without user intervention
  marketFeedTimer = setInterval(async () => {
    await autoTickMarketFeed();
  }, 5000);
}

async function autoTickMarketFeed() {
  try {
    const res = await fetch('/api/simulation/tick', { method: 'POST' });
    if (!res.ok) return;
    const snap = await res.json();

    if (snap) {
      state.lastMarketSnapshot = snap;
      updateLiveKpisAndFeed(snap);
    }
  } catch (err) {
    console.debug('Auto-feed update error:', err);
  }
}

// Sets text on a KPI element and flashes the card when the value changes
function setKpiText(id, text) {
  const el = document.getElementById(id);
  if (!el || el.textContent === text) return;
  el.textContent = text;
  const card = el.closest('.stat-card');
  if (card) {
    card.classList.remove('kpi-flash');
    void card.offsetWidth;
    card.classList.add('kpi-flash');
  }
}

function updateLiveKpisAndFeed(snap) {
  if (!snap) return;

  const kpiUpdated = document.getElementById('kpi-last-updated');
  if (kpiUpdated) kpiUpdated.textContent = new Date().toLocaleTimeString();

  const drift = snap.overall_drift_pct != null ? snap.overall_drift_pct : 0.0;
  const isUp = drift >= 0;

  // 1. Top Header Feed Ticker
  const driftEl = document.getElementById('ticker-drift');
  if (driftEl) {
    driftEl.textContent = `${isUp ? '+' : ''}${drift}%`;
    driftEl.className = isUp ? 'trend-up' : 'trend-down';
    driftEl.classList.remove('drift-pulse');
    void driftEl.offsetWidth;
    driftEl.classList.add('drift-pulse');
  }

  const updatedEl = document.getElementById('ticker-updated');
  if (updatedEl && snap.timestamp) {
    const parts = snap.timestamp.split(' ');
    updatedEl.textContent = parts[1] || snap.timestamp;
  }

  // 2. KPI 1: Total Properties In DB
  const kpiPropsSub = document.getElementById('kpi-props-subtext');
  if (kpiPropsSub) {
    const volume = snap.simulated_daily_volume || 450;
    kpiPropsSub.textContent = `${volume} simulated sales today`;
  }

  // 3. KPI 2: Monitored Localities
  const kpiLocsSub = document.getElementById('kpi-locs-subtext');
  if (kpiLocsSub) {
    const gain = snap.gaining_localities_count != null ? snap.gaining_localities_count : 7;
    const soft = snap.softening_localities_count != null ? snap.softening_localities_count : 7;
    kpiLocsSub.textContent = `${gain} areas rising ▲ • ${soft} falling ▼`;
  }

  // 4. KPI 3: Avg Rate (₹ / Sq.Ft) — DYNAMICALLY MOVES WITH FEED DRIFT!
  const avgSqftEl = document.getElementById('kpi-avg-sqft');
  if (avgSqftEl) {
    const liveRate = snap.indicative_market_avg_sqft || Math.round(30977 * (1.0 + drift / 100.0));
    setKpiText('kpi-avg-sqft', `₹${liveRate.toLocaleString()}`);
  }

  const avgSqftTrendEl = document.getElementById('kpi-avg-sqft-trend');
  if (avgSqftTrendEl) {
    avgSqftTrendEl.textContent = `${isUp ? '+' : ''}${drift}%`;
    avgSqftTrendEl.className = `stat-trend ${isUp ? 'trend-up' : 'trend-down'}`;
  }

  const avgSqftSub = document.getElementById('kpi-avg-sqft-subtext');
  if (avgSqftSub) {
    const minR = snap.min_price_sqft || Math.round(11200 * (1.0 + drift / 100.0));
    const maxR = snap.max_price_sqft || Math.round(62000 * (1.0 + drift / 100.0));
    avgSqftSub.textContent = `Range: ₹${minR.toLocaleString()} to ₹${maxR.toLocaleString()} / sq.ft`;
  }

  // 5. KPI 4: Market Demand Index — DYNAMICALLY MOVES ON EVERY 5s TICK!
  const demandVal = snap.overall_demand_index != null ? snap.overall_demand_index : 75.7;
  const demandEl = document.getElementById('kpi-demand-idx');
  if (demandEl) {
    setKpiText('kpi-demand-idx', `${demandVal}/100`);
  }

  const demandTrendEl = document.getElementById('kpi-demand-trend');
  if (demandTrendEl) {
    if (demandVal >= 76.5) {
      demandTrendEl.textContent = 'Strong ▲';
      demandTrendEl.className = 'stat-trend trend-up';
    } else if (demandVal >= 73.0) {
      demandTrendEl.textContent = 'Steady';
      demandTrendEl.className = 'stat-trend trend-up';
    } else {
      demandTrendEl.textContent = 'Cooling ▼';
      demandTrendEl.className = 'stat-trend trend-down';
    }
  }

  const demandSub = document.getElementById('kpi-demand-idx-subtext');
  if (demandSub) {
    if (demandVal >= 76.5) {
      demandSub.textContent = 'Lots of buyers are looking right now';
    } else if (demandVal >= 73.0) {
      demandSub.textContent = 'A normal number of buyers';
    } else {
      demandSub.textContent = 'Fewer buyers than usual';
    }
  }

  // 6. Cross-Tab Dynamic Updates:
  // Tab 1: Overview Working Demonstration Example
  const exLiveRate = document.getElementById('example-prop-live-rate');
  if (exLiveRate) {
    const baseExVal = 32300000; // ₹3.23 Cr
    const indexedExVal = baseExVal * (1.0 + drift / 100.0);
    exLiveRate.textContent = `${formatInr(indexedExVal)} (${isUp ? '+' : ''}${drift}%)`;
    exLiveRate.style.color = isUp ? '#5a7d5f' : '#b5523b';
  }

  // Tab 3: Property Valuation & What-If Live Adjusted Price
  if (state.currentPredictedPriceInr) {
    const adjVal = state.currentPredictedPriceInr * (1.0 + drift / 100.0);
    const livePriceEl = document.getElementById('ml-live-market-price');
    const liveDriftEl = document.getElementById('ml-live-market-drift');
    if (livePriceEl) livePriceEl.textContent = formatInr(adjVal);
    if (liveDriftEl) {
      liveDriftEl.textContent = `${isUp ? '+' : ''}${drift}%`;
      liveDriftEl.className = isUp ? 'trend-up' : 'trend-down';
    }
  }

  // Tab 5: Locality Intelligence Live Indicative Rate
  if (snap.locality_snapshots && state.selectedLocalityId) {
    const curLocSnap = snap.locality_snapshots.find(s => s.locality_id === state.selectedLocalityId);
    if (curLocSnap) {
      const locRateEl = document.getElementById('intel-sqft-rate');
      if (locRateEl && curLocSnap.indicative_avg_price_sqft) {
        locRateEl.textContent = `₹${Math.round(curLocSnap.indicative_avg_price_sqft).toLocaleString()} / sq.ft`;
      }
      const locGrowthEl = document.getElementById('intel-growth-yoy');
      if (locGrowthEl && curLocSnap.daily_change_pct != null) {
        const locDrift = curLocSnap.daily_change_pct;
        locGrowthEl.textContent = `${locDrift >= 0 ? '+' : ''}${locDrift}% Today (Live Feed Indicative)`;
        locGrowthEl.className = locDrift >= 0 ? 'trend-up' : 'trend-down';
      }
    }
  }

  // Tab 2 & 4: Status Badges
  const dirPill = document.getElementById('showing-records-text');
  if (dirPill && dirPill.textContent.includes('records')) {
    dirPill.textContent = `1,250 records • Feed Drift: ${isUp ? '+' : ''}${drift}%`;
  }

  const mapPill = document.getElementById('map-marker-count');
  if (mapPill && mapPill.textContent.includes('properties')) {
    mapPill.textContent = `1,250 properties • Live Rate: ₹${(snap.indicative_market_avg_sqft || 30977).toLocaleString()}/sq.ft`;
  }
}

async function loadOverviewCharts() {
  // Load Matplotlib / Seaborn Analytical Visualizations
  try {
    const [trendsRes, modelsRes] = await Promise.all([
      fetch('/api/reports/historical_trends'),
      fetch('/api/reports/model_comparison')
    ]);
    const trendsData = await trendsRes.json();
    const modelsData = await modelsRes.json();

    if (trendsData.image_data_url) {
      document.getElementById('chart-img-trends').src = trendsData.image_data_url;
    }
    if (modelsData.image_data_url) {
      document.getElementById('chart-img-models').src = modelsData.image_data_url;
    }
  } catch (e) {
    console.warn('Charts load warning:', e);
  }
}

// --- LOCALITIES LOADER ---
async function loadLocalities() {
  try {
    const res = await fetch('/api/localities');
    state.localities = await res.json();

    // Populate locality selects across tabs
    const selects = ['filter-locality', 'map-filter-locality', 'intel-locality-select', 'hist-locality-select'];
    selects.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.innerHTML = id === 'intel-locality-select' ? '' : '<option value="">All Localities (Mumbai & MMR)</option>';
      state.localities.forEach(loc => {
        const opt = document.createElement('option');
        opt.value = loc.locality_id;
        opt.textContent = `${loc.locality_name} (${loc.zone}) — ₹${Math.round(loc.avg_price_sqft).toLocaleString()}/sq.ft`;
        el.appendChild(opt);
      });
    });

    if (state.localities.length > 0) {
      loadLocalityProfile(state.localities[0].locality_id);
    }
  } catch (err) {
    console.error('Error loading localities:', err);
  }
}

// --- PROPERTY SEARCH & DIRECTORY ---
function setupPropertyFilters() {
  const searchInput = document.getElementById('search-property-input');
  const locSelect = document.getElementById('filter-locality');
  const bhkSelect = document.getElementById('filter-bhk');
  const typeSelect = document.getElementById('filter-type');

  let debounceTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.propertiesPage = 1;
      loadProperties();
    }, 250);
  });

  [locSelect, bhkSelect, typeSelect].forEach(el => {
    el.addEventListener('change', () => {
      state.propertiesPage = 1;
      loadProperties();
    });
  });

  document.getElementById('prev-page-btn').addEventListener('click', () => {
    if (state.propertiesPage > 1) {
      state.propertiesPage--;
      loadProperties();
    }
  });

  document.getElementById('next-page-btn').addEventListener('click', () => {
    state.propertiesPage++;
    loadProperties();
  });
}

async function loadProperties() {
  const q = document.getElementById('search-property-input').value.trim();
  const loc = document.getElementById('filter-locality').value;
  const bhk = document.getElementById('filter-bhk').value;
  const type = document.getElementById('filter-type').value;

  const params = new URLSearchParams({
    page: state.propertiesPage,
    limit: state.propertiesLimit
  });
  if (q) params.set('q', q);
  if (loc) params.set('locality_id', loc);
  if (bhk) params.set('bhk', bhk);
  if (type) params.set('property_type', type);

  const grid = document.getElementById('properties-grid');
  grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#6b6a62;">Loading property records...</div>';

  try {
    const res = await fetch(`/api/properties?${params.toString()}`);
    const data = await res.json();

    document.getElementById('showing-records-text').textContent =
      `Showing ${data.items.length} of ${data.total} properties in database (Page ${data.page} of ${data.total_pages})`;

    document.getElementById('prev-page-btn').disabled = state.propertiesPage <= 1;
    document.getElementById('next-page-btn').disabled = state.propertiesPage >= data.total_pages;

    if (data.items.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:50px;background:#fff;border-radius:12px;border:1px dashed #c9bda4;">
          <h4 style="font-size:16px;color:#1a1a1a;margin-bottom:6px;">No matching properties found</h4>
          <p style="font-size:13px;color:#6b6a62;margin-bottom:14px;">Try searching for Andheri, Bandra, Powai, Worli, or reset filters.</p>
          <button class="btn-secondary" onclick="resetPropertyFilters()">Reset Filters</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = '';
    data.items.forEach(prop => {
      const card = document.createElement('div');
      card.className = 'property-card';
      card.innerHTML = `
        <div>
          <div class="card-top">
            <span class="property-tag">${prop.property_type}</span>
            <span class="property-id-badge">${prop.property_id}</span>
          </div>
          <h3 class="property-title">${escapeHtml(prop.property_name)}</h3>
          <p class="property-address">${escapeHtml(prop.address)}</p>
          <div class="property-specs">
            <span class="spec-chip">${prop.bhk} BHK</span>
            <span class="spec-chip">${prop.built_up_area} sq.ft</span>
            <span class="spec-chip">Floor ${prop.floor_no}/${prop.total_floors}</span>
            <span class="spec-chip">${prop.furnishing_status}</span>
          </div>
        </div>
        <div class="property-pricing">
          <div>
            <div class="price-main">${prop.price_formatted}</div>
            <div class="price-sqft">₹${Math.round(prop.price_per_sqft).toLocaleString()} / sq.ft</div>
          </div>
          <button class="btn-primary btn-sm" onclick="openPropertyDetail('${prop.property_id}')">
            Analyze Valuation
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1;color:#b5523b;text-align:center;padding:40px;">Error loading properties: ${err.message}</div>`;
  }
}

window.resetPropertyFilters = () => {
  document.getElementById('search-property-input').value = '';
  document.getElementById('filter-locality').value = '';
  document.getElementById('filter-bhk').value = '';
  document.getElementById('filter-type').value = '';
  state.propertiesPage = 1;
  loadProperties();
};

// --- PROPERTY DETAILS & ML VALUATION ---
window.openPropertyDetail = async (propertyId) => {
  state.selectedPropertyId = propertyId;
  switchTab('property-detail');
  window.scrollTo({ top: 0, behavior: 'smooth' });

  try {
    const res = await fetch(`/api/properties/${propertyId}`);
    if (!res.ok) throw new Error('Property not found');
    const data = await res.json();
    renderPropertyDetailPage(data);
  } catch (err) {
    alert('Error loading property: ' + err.message);
  }
};

function renderPropertyDetailPage(data) {
  const p = data.property;
  const l = data.locality;

  document.getElementById('detail-prop-title').textContent = p.property_name;
  document.getElementById('detail-prop-address').textContent = p.address;
  document.getElementById('detail-prop-id-badge').textContent = p.property_id;
  document.getElementById('detail-prop-type-tag').textContent = p.property_type;
  document.getElementById('detail-actual-price').textContent = p.price_formatted;
  document.getElementById('detail-actual-sqft').textContent = `₹${Math.round(p.price_per_sqft).toLocaleString()} / sq.ft`;

  // Specification Table
  document.getElementById('spec-built-up').textContent = `${p.built_up_area} sq.ft`;
  document.getElementById('spec-carpet').textContent = `${p.carpet_area} sq.ft`;
  document.getElementById('spec-bhk').textContent = `${p.bhk} BHK (${p.bathrooms} Baths)`;
  document.getElementById('spec-floor').textContent = `Floor ${p.floor_no} of ${p.total_floors}`;
  document.getElementById('spec-age').textContent = `${p.property_age} Years`;
  document.getElementById('spec-furnishing').textContent = p.furnishing_status;
  document.getElementById('spec-parking').textContent = p.parking_type;
  document.getElementById('spec-road').textContent = p.road_type;
  document.getElementById('spec-locality').textContent = `${p.locality_name} (${l.zone || 'MMR'})`;

  // Nearby Transit and Amenities List
  const amenitiesContainer = document.getElementById('detail-amenities-list');
  amenitiesContainer.innerHTML = '';
  (data.amenities || []).slice(0, 6).forEach(a => {
    const item = document.createElement('div');
    item.className = 'status-pill';
    item.style.justifyContent = 'space-between';
    item.innerHTML = `
      <span><strong>${a.category}:</strong> ${escapeHtml(a.name)}</span>
      <span style="font-weight:700;color:#6b8f71;">Rating: ${a.rating} / 5.0</span>
    `;
    amenitiesContainer.appendChild(item);
  });

  // Reset What-If Controls to current property specs
  document.getElementById('wif-built-up').value = p.built_up_area;
  document.getElementById('wif-bhk').value = p.bhk;
  document.getElementById('wif-age').value = p.property_age;
  document.getElementById('wif-parking').value = p.parking_spaces;
  document.getElementById('wif-furnishing').value = p.furnishing_status;
  document.getElementById('wif-road').value = p.road_type;

  // Cache detail data so the compact map can re-init on tab switch
  state.cachedPropertyDetail = data;

  // Auto-run valuation on first view
  runPropertyValuation(p.property_id);

  // Initialize compact location map
  initCompactPropertyMap(p.property_id, data);
}

async function runPropertyValuation(propertyId) {

  try {
    const res = await fetch(`/api/valuation/${propertyId}`, { method: 'POST' });
    const data = await res.json();

    const val = data.valuation;
    document.getElementById('ml-pred-price').textContent = val.predicted_price_formatted;
    document.getElementById('ml-pred-sqft').textContent = `₹${Math.round(val.predicted_price_per_sqft).toLocaleString()} / sq.ft`;
    document.getElementById('ml-model-name').textContent = val.model_used;
    document.getElementById('ml-model-r2').textContent = `${(val.model_r2_score * 100).toFixed(1)}%`;
    document.getElementById('ml-model-mae').textContent = `₹${val.model_mae_lakhs} L`;

    const delta = data.delta_vs_baseline;
    const deltaEl = document.getElementById('ml-delta-baseline');
    deltaEl.textContent = `${delta.diff_formatted} (${delta.diff_percentage >= 0 ? '+' : ''}${delta.diff_percentage}%)`;
    deltaEl.className = delta.diff_percentage >= 0 ? 'trend-up' : 'trend-down';

    // Store predicted price for live market indexing
    state.currentPredictedPriceInr = val.predicted_price_inr;
    if (state.lastMarketSnapshot) {
      updateLiveKpisAndFeed(state.lastMarketSnapshot);
    }

    // Model Comparison Grid
    const allModels = data.all_model_predictions || {};
    document.getElementById('val-lr-price').textContent = allModels.linear_regression?.predicted_price_formatted || '—';
    document.getElementById('val-dt-price').textContent = allModels.decision_tree?.predicted_price_formatted || '—';
    document.getElementById('val-rf-price').textContent = allModels.random_forest?.predicted_price_formatted || '—';

    // Set active base for What-If
    state.activeWhatIf = {
      basePropertyId: propertyId,
      originalValuation: val.predicted_price_inr,
      originalFormatted: val.predicted_price_formatted
    };
    document.getElementById('wif-orig-val').textContent = val.predicted_price_formatted;
    document.getElementById('wif-scen-val').textContent = val.predicted_price_formatted;
    document.getElementById('wif-delta-val').textContent = '±₹0.00 (0.0%)';
  } catch (err) {
    alert('Valuation calculation failed: ' + err.message);
  }
}

// --- WHAT-IF SENSITIVITY PLAYGROUND ---
function setupWhatIfControls() {
  const recalcBtn = document.getElementById('btn-recalc-whatif');
  if (recalcBtn) {
    recalcBtn.addEventListener('click', async () => {
      if (!state.selectedPropertyId) return;

      const overrides = {
        built_up_area: parseFloat(document.getElementById('wif-built-up').value),
        bhk: parseInt(document.getElementById('wif-bhk').value),
        property_age: parseInt(document.getElementById('wif-age').value),
        parking_spaces: parseInt(document.getElementById('wif-parking').value),
        furnishing_status: document.getElementById('wif-furnishing').value,
        road_type: document.getElementById('wif-road').value
      };

      try {
        recalcBtn.disabled = true;
        recalcBtn.textContent = 'Recalculating...';

        const res = await fetch('/api/valuation/what-if', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            property_id: state.selectedPropertyId,
            scenario_overrides: overrides
          })
        });
        const result = await res.json();

        document.getElementById('wif-orig-val').textContent = result.original_valuation.predicted_price_formatted;
        document.getElementById('wif-scen-val').textContent = result.scenario_valuation.predicted_price_formatted;

        const deltaVal = document.getElementById('wif-delta-val');
        deltaVal.textContent = `${result.absolute_difference_formatted} (${result.percentage_difference >= 0 ? '+' : ''}${result.percentage_difference}%)`;
        deltaVal.className = result.percentage_difference >= 0 ? 'c-delta trend-up' : 'c-delta trend-down';

        showNotification(`What-If recalculation complete: ${result.absolute_difference_formatted} change`, 'info');
      } catch (err) {
        alert('What-If recalculation failed: ' + err.message);
      } finally {
        recalcBtn.disabled = false;
        recalcBtn.textContent = 'Recalculate Scenario';
      }
    });
  }
}

// --- COMPACT MAP FOR PROPERTY DETAIL ---
function initCompactPropertyMap(propertyId, preloadedData) {
  const container = document.getElementById('compact-property-map');
  if (!container) return;

  if (state.compactMapInstance) {
    state.compactMapInstance.remove();
    state.compactMapInstance = null;
  }

  const p = preloadedData?.property;
  if (!p) return;

  const lat = p.latitude;
  const lng = p.longitude;

  const map = L.map('compact-property-map').setView([lat, lng], 14);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // Property pin
  const propIcon = L.divIcon({
    className: 'custom-map-icon',
    html: '<div style="background:#6b8f71;color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.3);">P</div>',
    iconSize: [24, 24]
  });

  L.marker([lat, lng], { icon: propIcon }).addTo(map)
    .bindPopup(`<strong>${escapeHtml(p.property_name)}</strong><br>${p.price_formatted}<br>Simulated property coordinates`)
    .openPopup();

  // 1km and 2km proximity circles
  L.circle([lat, lng], { radius: 1000, color: '#6b8f71', fillOpacity: 0.05, weight: 1.5 }).addTo(map);
  L.circle([lat, lng], { radius: 2000, color: '#9a978c', fillOpacity: 0.02, weight: 1, dashArray: '4, 4' }).addTo(map);

  // Nearby amenities pins
  (preloadedData.amenities || []).forEach(a => {
    const badgeText = a.category === 'Hospital' ? 'MED' : a.category === 'School' ? 'EDU' : a.category === 'Metro Station' ? 'METRO' : 'COMM';
    const amnIcon = L.divIcon({
      className: 'amenity-icon',
      html: `<div style="background:#1a1a1a;color:#fff;padding:2px 5px;border-radius:3px;font-size:9px;font-weight:700;letter-spacing:0.04em;">${badgeText}</div>`,
      iconSize: [36, 16]
    });
    L.marker([a.latitude, a.longitude], { icon: amnIcon }).addTo(map)
      .bindPopup(`<strong>${escapeHtml(a.name)}</strong><br>${a.category} (Rating: ${a.rating}/5.0)`);
  });

  state.compactMapInstance = map;
}

// --- FULL-SIZE MAP EXPLORER ---
function initFullMapExplorer() {
  if (state.mapInstance) {
    state.mapInstance.invalidateSize();
    return;
  }

  const map = L.map('full-map-explorer').setView([19.1200, 72.8800], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  state.mapInstance = map;
  state.markerClusterGroup = L.markerClusterGroup({
    chunkedLoading: true,
    maxClusterRadius: 50
  });
  map.addLayer(state.markerClusterGroup);

  // Setup Map Filters
  ['map-filter-locality', 'map-filter-bhk', 'map-filter-type'].forEach(id => {
    document.getElementById(id).addEventListener('change', refreshMapMarkers);
  });

  refreshMapMarkers();
}

async function refreshMapMarkers() {
  if (!state.mapInstance || !state.markerClusterGroup) return;

  const loc = document.getElementById('map-filter-locality').value;
  const bhk = document.getElementById('map-filter-bhk').value;
  const type = document.getElementById('map-filter-type').value;

  const params = new URLSearchParams();
  if (loc) params.set('locality_id', loc);
  if (bhk) params.set('bhk', bhk);
  if (type) params.set('property_type', type);

  try {
    const res = await fetch(`/api/map/properties?${params.toString()}`);
    const data = await res.json();

    document.getElementById('map-marker-count').textContent =
      `Displaying ${data.total_count} property coordinates in view (Clustered for performance)`;

    state.markerClusterGroup.clearLayers();

    const markers = [];
    data.markers.forEach(m => {
      const marker = L.marker([m.lat, m.lng]);
      const popupHtml = `
        <div style="font-family:var(--font-sans);min-width:200px;">
          <div style="font-size:11px;color:#6b8f71;font-weight:700;">${m.property_type} • ${m.bhk} BHK</div>
          <h4 style="margin:2px 0 4px 0;font-size:14px;color:#1a1a1a;">${escapeHtml(m.property_name)}</h4>
          <div style="font-size:12px;color:#4a4a45;margin-bottom:6px;">${escapeHtml(m.address)}</div>
          <div style="font-size:15px;font-weight:800;color:#1a1a1a;margin-bottom:8px;">${m.price_formatted} <span style="font-size:11px;color:#6b6a62;font-weight:normal;">(₹${Math.round(m.price_per_sqft).toLocaleString()}/sq.ft)</span></div>
          <button style="background:#6b8f71;color:#fff;border:none;padding:5px 10px;border-radius:4px;font-size:11px;cursor:pointer;width:100%;font-weight:600;" onclick="openPropertyDetail('${m.property_id}')">
            View Details & ML Valuation
          </button>
        </div>
      `;
      marker.bindPopup(popupHtml);
      markers.push(marker);
    });

    state.markerClusterGroup.addLayers(markers);

    if (markers.length > 0 && loc) {
      const group = new L.featureGroup(markers);
      state.mapInstance.fitBounds(group.getBounds().pad(0.1));
    }
  } catch (err) {
    console.error('Error refreshing map markers:', err);
  }
}

// --- LOCALITY INTELLIGENCE & COMPARISON ---
async function loadLocalityProfile(localityId) {
  try {
    const res = await fetch(`/api/localities/${localityId}`);
    const data = await res.json();

    document.getElementById('intel-loc-name').textContent = data.locality_name;
    document.getElementById('intel-loc-zone').textContent = `${data.zone}, ${data.city}`;

    // Live Feed Indicative Pricing Sync
    let liveSqft = data.pricing.avg_price_sqft;
    let liveGrowth = `+${data.pricing.yoy_price_change_pct}% YoY`;
    if (state.lastMarketSnapshot && state.lastMarketSnapshot.locality_snapshots) {
      const curLoc = state.lastMarketSnapshot.locality_snapshots.find(s => s.locality_id === localityId);
      if (curLoc && curLoc.indicative_avg_price_sqft) {
        liveSqft = curLoc.indicative_avg_price_sqft;
        const drift = curLoc.daily_change_pct;
        liveGrowth = `${drift >= 0 ? '+' : ''}${drift}% Today (Live Feed)`;
      }
    }
    document.getElementById('intel-sqft-rate').textContent = `₹${Math.round(liveSqft).toLocaleString()} / sq.ft`;
    document.getElementById('intel-growth-yoy').textContent = `${liveGrowth} • 5-Yr CAGR: ${data.pricing.historical_cagr_5yr}%`;

    // Demographics
    document.getElementById('intel-population').textContent = data.demographics.population.toLocaleString();
    document.getElementById('intel-density').textContent = `${data.demographics.population_density_per_sqkm.toLocaleString()} / sq.km`;
    document.getElementById('intel-income').textContent = `₹${data.demographics.avg_household_income_lakhs} Lakhs/yr`;
    document.getElementById('intel-tier').textContent = data.demographics.socioeconomic_tier;

    // Infrastructure & Cluster
    document.getElementById('intel-transit-score').textContent = `${data.transit_and_infra.transit_score} / 10`;
    document.getElementById('intel-infra-rating').textContent = `${data.transit_and_infra.infrastructure_rating} / 10`;
    document.getElementById('intel-cluster-label').textContent = data.clustering.cluster_label;
    document.getElementById('intel-highway').textContent = data.transit_and_infra.highway_connectivity;

    // Development projects list
    const projContainer = document.getElementById('intel-projects-list');
    projContainer.innerHTML = '';
    if (data.development_projects.length === 0) {
      projContainer.innerHTML = '<div style="color:#6b6a62;font-size:13px;">No direct mega-infrastructure projects in immediate micro-zone.</div>';
    } else {
      data.development_projects.forEach(p => {
        const item = document.createElement('div');
        item.className = 'panel';
        item.style.padding = '12px 16px';
        item.style.marginBottom = '10px';
        item.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <strong>${escapeHtml(p.project_name)}</strong>
            <span class="badge-verified">${p.status}</span>
          </div>
          <div style="font-size:12px;color:#6b6a62;margin-top:4px;">
            ${p.impact_zone} • Est. Completion ${p.expected_completion_year} • Budget ₹${p.estimated_budget_cr} Cr
          </div>
        `;
        projContainer.appendChild(item);
      });
    }
  } catch (err) {
    console.error('Error loading locality profile:', err);
  }
}

function setupLocalityCompareUI() {
  const intelSelect = document.getElementById('intel-locality-select');
  if (intelSelect) {
    intelSelect.addEventListener('change', () => {
      loadLocalityProfile(intelSelect.value);
    });
  }

  const compareBtn = document.getElementById('btn-run-compare');
  if (compareBtn) {
    compareBtn.addEventListener('click', async () => {
      const l1 = document.getElementById('cmp-loc-1').value;
      const l2 = document.getElementById('cmp-loc-2').value;
      const l3 = document.getElementById('cmp-loc-3').value;

      const ids = [l1, l2, l3].filter(id => id);
      if (ids.length < 2) {
        alert('Please select at least 2 localities to compare.');
        return;
      }

      try {
        const res = await fetch('/api/localities/compare', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ locality_ids: ids })
        });
        const compData = await res.json();
        renderLocalityCompareTable(compData);
      } catch (err) {
        alert('Comparison failed: ' + err.message);
      }
    });
  }
}

function renderLocalityCompareTable(data) {
  const table = document.getElementById('locality-compare-table');
  let headerHtml = '<tr><th>Metric</th>';
  data.forEach(d => {
    headerHtml += `<th>${escapeHtml(d.locality_name)}</th>`;
  });
  headerHtml += '</tr>';

  let rows = [
    { label: 'Zone', key: 'zone' },
    { label: 'Avg Price / sq.ft', format: d => `₹${Math.round(d.avg_price_sqft).toLocaleString()}` },
    { label: 'YoY Growth (%)', format: d => `+${d.yoy_price_change_pct}%` },
    { label: '5-Year CAGR (%)', format: d => `+${d.historical_cagr_5yr}%` },
    { label: 'Transit Score', format: d => `${d.transit_score} / 10` },
    { label: 'Infra Rating', format: d => `${d.infra_rating} / 10` },
    { label: 'Pop. Density', format: d => `${d.population_density.toLocaleString()} / km²` },
    { label: 'Household Income', format: d => `₹${d.avg_income_lakhs} L/yr` },
    { label: 'K-Means Cluster', key: 'cluster_label' }
  ];

  let bodyHtml = '';
  rows.forEach(r => {
    bodyHtml += `<tr><td><strong>${r.label}</strong></td>`;
    data.forEach(d => {
      const val = r.format ? r.format(d) : d[r.key];
      bodyHtml += `<td>${val}</td>`;
    });
    bodyHtml += '</tr>';
  });

  table.innerHTML = `<thead>${headerHtml}</thead><tbody>${bodyHtml}</tbody>`;
}

// --- HISTORICAL TRENDS & ANALYTICS ---
async function loadHistoricalTrends() {
  const locSelect = document.getElementById('hist-locality-select');
  if (locSelect) {
    locSelect.addEventListener('change', () => {
      fetchHistoricalTrends(locSelect.value);
    });
  }
  await fetchHistoricalTrends();
}

async function fetchHistoricalTrends(localityId = '') {
  try {
    const url = localityId ? `/api/historical/trends?locality_id=${localityId}` : '/api/historical/trends';
    const res = await fetch(url);
    const data = await res.json();

    const tbody = document.getElementById('hist-trends-tbody');
    tbody.innerHTML = '';
    (data.yearly_trends || []).forEach(row => {
      const tr = document.createElement('tr');
      const yoyDisplay = row.yoy_growth_pct !== null
        ? `<span class="${row.yoy_growth_pct >= 0 ? 'trend-up' : 'trend-down'}">${row.yoy_growth_pct >= 0 ? '+' : ''}${row.yoy_growth_pct}%</span>`
        : '<span style="color:#9a978c;">Baseline Year</span>';

      tr.innerHTML = `
        <td><strong>${row.year}</strong></td>
        <td>₹${Math.round(row.avg_price_sqft).toLocaleString()}</td>
        <td>₹${Math.round(row.median_price_sqft).toLocaleString()}</td>
        <td>${row.transaction_volume} txns</td>
        <td>${yoyDisplay}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error fetching historical trends:', err);
  }
}

// --- ML MODELS & VIVA CHEATSHEET ---
async function loadModelVivaMetrics() {
  try {
    const [metricsRes, clusterRes, fiRes, kmeansPlotRes] = await Promise.all([
      fetch('/api/models/metrics'),
      fetch('/api/clustering/status'),
      fetch('/api/reports/feature_importance'),
      fetch('/api/reports/kmeans_clusters')
    ]);

    const metricsData = await metricsRes.json();
    const clusterData = await clusterRes.json();
    const fiData = await fiRes.json();
    const kmeansPlot = await kmeansPlotRes.json();

    // Populate Metrics Table
    const models = metricsData.models || {};
    if (models.linear_regression) {
      document.getElementById('m-lr-r2').textContent = models.linear_regression.r2_score;
      document.getElementById('m-lr-mae').textContent = `₹${models.linear_regression.mae_lakhs} L`;
      document.getElementById('m-lr-rmse').textContent = `₹${models.linear_regression.rmse_lakhs} L`;
    }
    if (models.decision_tree) {
      document.getElementById('m-dt-r2').textContent = models.decision_tree.r2_score;
      document.getElementById('m-dt-mae').textContent = `₹${models.decision_tree.mae_lakhs} L`;
      document.getElementById('m-dt-rmse').textContent = `₹${models.decision_tree.rmse_lakhs} L`;
    }
    if (models.random_forest) {
      document.getElementById('m-rf-r2').textContent = `${models.random_forest.r2_score} (Best Model)`;
      document.getElementById('m-rf-mae').textContent = `₹${models.random_forest.mae_lakhs} L`;
      document.getElementById('m-rf-rmse').textContent = `₹${models.random_forest.rmse_lakhs} L`;
    }

    // Embed Feature Importance and K-Means Charts
    if (fiData.image_data_url) {
      document.getElementById('chart-img-fi').src = fiData.image_data_url;
    }
    if (kmeansPlot.image_data_url) {
      document.getElementById('chart-img-kmeans').src = kmeansPlot.image_data_url;
    }

    // K-Means Summary Cards
    const profiles = clusterData.cluster_profiles || {};
    const clusterContainer = document.getElementById('kmeans-profiles-container');
    clusterContainer.innerHTML = '';
    Object.values(profiles).forEach(p => {
      const card = document.createElement('div');
      card.className = 'panel';
      card.style.marginBottom = '12px';
      card.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <h4 style="font-size:14.5px;color:#1a1a1a;">Cluster ${p.cluster_id}: ${p.label}</h4>
          <span class="status-pill">${p.locality_count} Localities</span>
        </div>
        <div style="font-size:12.5px;color:#4a4a45;margin-top:6px;">
          Localities: <strong>${p.localities.join(', ')}</strong><br>
          Mean Price: <strong>₹${Math.round(p.mean_price_sqft).toLocaleString()}/sq.ft</strong> • Mean Transit: <strong>${p.mean_transit_score}/10</strong> • 5-Yr Growth: <strong>+${p.mean_cagr_5yr}%</strong>
        </div>
      `;
      clusterContainer.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading viva metrics:', err);
  }
}

// --- UTILITIES ---
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatInr(val) {
  if (val == null || isNaN(val)) return '—';
  if (val >= 10000000) {
    return `₹${(val / 10000000).toFixed(2)} Cr`;
  } else if (val >= 100000) {
    return `₹${(val / 100000).toFixed(2)} Lakh`;
  }
  return `₹${Math.round(val).toLocaleString()}`;
}

function showNotification(msg, type = 'info') {
  const el = document.createElement('div');
  el.style.position = 'fixed';
  el.style.bottom = '20px';
  el.style.right = '20px';
  el.style.background = type === 'success' ? '#5a7d5f' : type === 'error' ? '#b5523b' : '#2a2a27';
  el.style.color = '#fff';
  el.style.padding = '12px 20px';
  el.style.borderRadius = '8px';
  el.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
  el.style.fontSize = '13.5px';
  el.style.fontWeight = '600';
  el.style.zIndex = '9999';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
