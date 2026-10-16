/**
 * Edge-AI Multi-Sensor Food Spoilage & Smart Storage Monitor
 * Frontend Application Logic, Canvas Chart Engine, and Hardware Emulation
 */

// Application State
const state = {
  backendOnline: false,
  mlReady: false,
  audioMuted: false,
  isStreaming: false,
  streamIntervalId: null,
  pollIntervalId: null,
  manualOverride: false,
  currentDayIndex: 0,
  activeDatasetStream: null,
  datasetStreamIndex: 0,

  currentTelemetry: {
    mq135: 495.0,
    temperature: 14.2,
    humidity: 86.4,
  },

  latestInference: {
    prediction: 'Fresh',
    stage: 'EARLY',
    probability_spoiled: 0.0003,
    confidence_score: 99.9,
    threshold: 738.0,
    model_name: 'Edge-AI Stacking Hybrid',
    actuators: {
      alert_led: 'GREEN',
      buzzer: false,
      ventilation_fan: false,
      cooling_unit: false,
    },
    storage_assessment: {
      shelf_life_estimate: '4 - 6 Days (Safe for Distribution)',
      recommended_action: 'Maintain chamber temperature (13-15°C) and baseline ventilation.',
      temperature_status: 'Optimal banana storage (13-15°C)',
      humidity_status: 'Optimal relative humidity (80-90%)',
    },
  },

  history: [],
};

// Web Audio API Synthesizer for ESP32 Active Buzzer Beep
let audioCtx = null;
function playAlarmBeep() {
  if (state.audioMuted) return;
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(880, audioCtx.currentTime); // 880Hz warning pitch
    osc.frequency.exponentialRampToValueAtTime(1760, audioCtx.currentTime + 0.15);

    gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start();
    osc.stop(audioCtx.currentTime + 0.25);
  } catch (e) {
    // AudioContext permission guard
  }
}

// DOM Elements
const elements = {
  // Status Pills
  backendStatusText: document.getElementById('backendStatusText'),
  backendStatusPill: document.getElementById('backendStatusPill'),
  mlStatusText: document.getElementById('mlStatusText'),
  mlStatusPill: document.getElementById('mlStatusPill'),
  edgeStatusText: document.getElementById('edgeStatusText'),
  edgeStatusPill: document.getElementById('edgeStatusPill'),
  modelArchitectureBadge: document.getElementById('modelArchitectureBadge'),

  // Hero Spoilage Elements
  conditionBadge: document.getElementById('conditionBadge'),
  conditionGlowRing: document.getElementById('conditionGlowRing'),
  conditionIcon: document.getElementById('conditionIcon'),
  conditionStateText: document.getElementById('conditionStateText'),
  conditionStageText: document.getElementById('conditionStageText'),
  spoilageProbText: document.getElementById('spoilageProbText'),
  confidenceScoreText: document.getElementById('confidenceScoreText'),
  spoilageProgressBar: document.getElementById('spoilageProgressBar'),
  shelfLifeValue: document.getElementById('shelfLifeValue'),
  shelfRecommendationText: document.getElementById('shelfRecommendationText'),

  // Sensor KPIs
  mq135ValueText: document.getElementById('mq135ValueText'),
  mq135StatusPill: document.getElementById('mq135StatusPill'),
  mq135MiniBar: document.getElementById('mq135MiniBar'),
  tempValueText: document.getElementById('tempValueText'),
  tempFahrenheitText: document.getElementById('tempFahrenheitText'),
  tempStatusPill: document.getElementById('tempStatusPill'),
  tempMiniBar: document.getElementById('tempMiniBar'),
  humValueText: document.getElementById('humValueText'),
  humStatusPill: document.getElementById('humStatusPill'),
  humMiniBar: document.getElementById('humMiniBar'),

  // Actuators
  ledBulb: document.getElementById('ledBulb'),
  ledStateText: document.getElementById('ledStateText'),
  audioWaves: document.getElementById('audioWaves'),
  buzzerStateText: document.getElementById('buzzerStateText'),
  fanBlades: document.getElementById('fanBlades'),
  fanStateText: document.getElementById('fanStateText'),
  coolingFixture: document.querySelector('.compressor-icon'),
  coolingStateText: document.getElementById('coolingStateText'),
  manualOverrideToggle: document.getElementById('manualOverrideToggle'),

  // Sliders & Testing Controls
  mq135Slider: document.getElementById('mq135Slider'),
  mq135SliderVal: document.getElementById('mq135SliderVal'),
  tempSlider: document.getElementById('tempSlider'),
  tempSliderVal: document.getElementById('tempSliderVal'),
  humSlider: document.getElementById('humSlider'),
  humSliderVal: document.getElementById('humSliderVal'),
  sendReadingBtn: document.getElementById('sendReadingBtn'),
  livePreviewBtn: document.getElementById('livePreviewBtn'),
  ingestStatusMsg: document.getElementById('ingestStatusMsg'),

  // Streaming & Audio Buttons
  connectSerialBtn: document.getElementById('connectSerialBtn'),
  toggleAudioBtn: document.getElementById('toggleAudioBtn'),
  audioIcon: document.getElementById('audioIcon'),
  toggleStreamingBtn: document.getElementById('toggleStreamingBtn'),
  streamBtnText: document.getElementById('streamBtnText'),

  // Table & CSV
  telemetryTableBody: document.getElementById('telemetryTableBody'),
  exportCsvBtn: document.getElementById('exportCsvBtn'),
  clearHistoryBtn: document.getElementById('clearHistoryBtn'),

  // Canvas
  telemetryCanvas: document.getElementById('telemetryCanvas'),
};

// ============================================================================
// API Communication Layer
// ============================================================================

const API_BASE = '';

async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error(`Health HTTP ${res.status}`);
    const data = await res.json();
    state.backendOnline = data.backend === 'online';
    state.mlReady = data.ml === 'ready';

    elements.backendStatusText.textContent = state.backendOnline ? 'ONLINE' : 'OFFLINE';
    elements.backendStatusPill.querySelector('.pill-dot').className = `pill-dot ${state.backendOnline ? 'green' : 'red'}`;

    elements.mlStatusText.textContent = data.ml === 'ready' ? 'STACKING HYBRID' : data.ml.toUpperCase();
    elements.mlStatusPill.querySelector('.pill-dot').className = `pill-dot ${data.ml === 'ready' ? 'green' : 'amber'}`;
  } catch (err) {
    state.backendOnline = false;
    elements.backendStatusText.textContent = 'CONNECTING...';
    elements.backendStatusPill.querySelector('.pill-dot').className = 'pill-dot amber';
  }
}

async function fetchLatestReading() {
  try {
    const res = await fetch(`${API_BASE}/api/latest`);
    if (res.status === 404) {
      // Empty database, evaluate initial preview
      await executeDirectPrediction(state.currentTelemetry);
      return;
    }
    if (!res.ok) throw new Error(`Latest HTTP ${res.status}`);
    const data = await res.json();

    state.currentTelemetry.mq135 = data.mq135;
    state.currentTelemetry.temperature = data.temperature;
    state.currentTelemetry.humidity = data.humidity;

    // Synchronize UI sliders
    elements.mq135Slider.value = data.mq135;
    elements.mq135SliderVal.textContent = `${Math.round(data.mq135)} ADC`;
    elements.tempSlider.value = data.temperature;
    elements.tempSliderVal.textContent = `${data.temperature.toFixed(1)} °C`;
    elements.humSlider.value = data.humidity;
    elements.humSliderVal.textContent = `${data.humidity.toFixed(1)} %`;

    await executeDirectPrediction(state.currentTelemetry);
  } catch (err) {
    console.debug('No latest reading found yet:', err);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch(`${API_BASE}/api/history?limit=30`);
    if (!res.ok) return;
    const records = await res.json();
    state.history = records;
    renderHistoryTable(records);
    renderChart();
  } catch (err) {
    console.error('Error fetching history:', err);
  }
}

async function executeDirectPrediction(telemetry) {
  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(telemetry),
    });
    if (!res.ok) throw new Error(`Predict HTTP ${res.status}`);
    const detailed = await res.json();
    state.latestInference = detailed;
    updateUIWithPrediction(detailed);
  } catch (err) {
    console.error('Inference error:', err);
  }
}

async function ingestTelemetry(telemetry) {
  try {
    showIngestStatus('Ingesting...', 'var(--cyan-primary)');
    const res = await fetch(`${API_BASE}/api/sensor-data`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(telemetry),
    });
    if (!res.ok) throw new Error(`Ingest HTTP ${res.status}`);
    const record = await res.json();

    showIngestStatus(`✓ Persisted Record #${record.id}`, 'var(--emerald-primary)');
    await executeDirectPrediction(telemetry);
    await fetchHistory();
  } catch (err) {
    showIngestStatus(`Error: ${err.message}`, 'var(--crimson-primary)');
  }
}

function showIngestStatus(msg, color) {
  elements.ingestStatusMsg.textContent = msg;
  elements.ingestStatusMsg.style.color = color;
  setTimeout(() => {
    if (elements.ingestStatusMsg.textContent === msg) {
      elements.ingestStatusMsg.textContent = '';
    }
  }, 4000);
}

// ============================================================================
// UI Renderers & State Synchronization
// ============================================================================

function updateUIWithPrediction(data) {
  const {
    prediction,
    stage,
    probability_spoiled,
    confidence_score,
    mq135_adc,
    temperature,
    humidity,
    model_name,
    actuators,
    storage_assessment,
  } = data;

  // 1. Hero Condition Badge
  const condLower = prediction.toLowerCase();
  elements.conditionBadge.className = `condition-badge state-${condLower}`;
  elements.conditionGlowRing.className = `condition-glow-ring state-${condLower}`;
  elements.conditionStateText.textContent = prediction.toUpperCase();
  elements.conditionStageText.textContent = `${stage} STAGE`;

  if (prediction === 'Fresh') {
    elements.conditionIcon.textContent = '🌿';
  } else if (prediction === 'Warning') {
    elements.conditionIcon.textContent = '⚠️';
  } else {
    elements.conditionIcon.textContent = '☣️';
    playAlarmBeep(); // Trigger acoustic warning beacon
  }

  // 2. Metrics & Probability Bar
  const probPercent = (probability_spoiled * 100).toFixed(2);
  elements.spoilageProbText.textContent = `${probPercent}%`;
  elements.confidenceScoreText.textContent = `${confidence_score.toFixed(1)}%`;
  elements.spoilageProgressBar.style.width = `${Math.min(100, Math.max(2, probPercent))}%`;

  // Model Name Badge
  if (model_name) {
    elements.modelArchitectureBadge.textContent = model_name;
  }

  // Shelf-Life & Recommendation
  if (storage_assessment) {
    elements.shelfLifeValue.textContent = storage_assessment.shelf_life_estimate || 'N/A';
    elements.shelfRecommendationText.textContent = storage_assessment.recommended_action || '';
  }

  // 3. Sensor KPIs
  elements.mq135ValueText.textContent = Math.round(mq135_adc);
  elements.tempValueText.textContent = temperature.toFixed(1);
  elements.tempFahrenheitText.textContent = `(${(temperature * 1.8 + 32).toFixed(1)}°F)`;
  elements.humValueText.textContent = humidity.toFixed(1);

  // Mini Progress Bars
  elements.mq135MiniBar.style.width = `${Math.min(100, (mq135_adc / 2500) * 100)}%`;
  elements.tempMiniBar.style.width = `${Math.min(100, Math.max(0, (temperature / 40) * 100))}%`;
  elements.humMiniBar.style.width = `${Math.min(100, Math.max(0, humidity))}%`;

  // Sensor Pills
  if (mq135_adc >= 738) {
    elements.mq135StatusPill.className = 'kpi-pill critical';
    elements.mq135StatusPill.textContent = 'SPOILED GAS';
  } else if (mq135_adc >= 620) {
    elements.mq135StatusPill.className = 'kpi-pill warning';
    elements.mq135StatusPill.textContent = 'TRANSITION';
  } else {
    elements.mq135StatusPill.className = 'kpi-pill';
    elements.mq135StatusPill.textContent = 'OPTIMAL';
  }

  if (temperature >= 13.0 && temperature <= 15.5) {
    elements.tempStatusPill.className = 'kpi-pill';
    elements.tempStatusPill.textContent = 'OPTIMAL';
  } else if (temperature > 15.5) {
    elements.tempStatusPill.className = 'kpi-pill warning';
    elements.tempStatusPill.textContent = 'HIGH RESIDUAL';
  } else {
    elements.tempStatusPill.className = 'kpi-pill warning';
    elements.tempStatusPill.textContent = 'CHILL RISK';
  }

  if (humidity >= 80.0 && humidity <= 90.0) {
    elements.humStatusPill.className = 'kpi-pill';
    elements.humStatusPill.textContent = 'OPTIMAL';
  } else {
    elements.humStatusPill.className = 'kpi-pill warning';
    elements.humStatusPill.textContent = humidity > 90 ? 'CONDENSATION' : 'DRY';
  }

  // 4. Actuators
  if (actuators) {
    // LED
    if (actuators.alert_led === 'RED_PULSING') {
      elements.ledBulb.className = 'led-bulb state-red';
      elements.ledStateText.className = 'actuator-state-badge red';
      elements.ledStateText.textContent = 'CRITICAL ALERT (PULSING RED)';
    } else if (actuators.alert_led === 'AMBER') {
      elements.ledBulb.className = 'led-bulb state-amber';
      elements.ledStateText.className = 'actuator-state-badge amber';
      elements.ledStateText.textContent = 'WARNING (AMBER)';
    } else {
      elements.ledBulb.className = 'led-bulb';
      elements.ledStateText.className = 'actuator-state-badge green';
      elements.ledStateText.textContent = 'GREEN (NORMAL)';
    }

    // Buzzer
    if (actuators.buzzer) {
      elements.audioWaves.className = 'audio-waves active';
      elements.buzzerStateText.className = 'actuator-state-badge red';
      elements.buzzerStateText.textContent = 'ACTIVE (880 Hz)';
    } else {
      elements.audioWaves.className = 'audio-waves';
      elements.buzzerStateText.className = 'actuator-state-badge off';
      elements.buzzerStateText.textContent = 'INACTIVE';
    }

    // Exhaust Fan
    if (actuators.ventilation_fan) {
      elements.fanBlades.className = 'fan-blades spinning';
      elements.fanStateText.className = 'actuator-state-badge active';
      elements.fanStateText.textContent = 'PURGING VOCs (ACTIVE)';
    } else {
      elements.fanBlades.className = 'fan-blades';
      elements.fanStateText.className = 'actuator-state-badge off';
      elements.fanStateText.textContent = 'STANDBY';
    }

    // Cooling Compressor
    if (actuators.cooling_unit) {
      elements.coolingFixture.className = 'compressor-icon chilling';
      elements.coolingStateText.className = 'actuator-state-badge active';
      elements.coolingStateText.textContent = 'COOLING (REDUCING TEMP)';
    } else {
      elements.coolingFixture.className = 'compressor-icon';
      elements.coolingStateText.className = 'actuator-state-badge off';
      elements.coolingStateText.textContent = 'OFF (TEMP OK)';
    }
  }
}

function renderHistoryTable(records) {
  if (!records || records.length === 0) {
    elements.telemetryTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">No telemetry readings recorded in database yet. Use the Test Harness above to ingest sensor readings!</td>
      </tr>
    `;
    return;
  }

  const rows = records.map((r) => {
    const cond = r.prediction ? r.prediction.toLowerCase() : 'fresh';
    const badgeClass = cond === 'spoiled' ? 'spoiled' : (cond === 'warning' ? 'warning' : 'fresh');

    const formattedDate = r.timestamp ? new Date(r.timestamp).toLocaleTimeString() : 'Recent';
    const actuatorSummary = cond === 'spoiled' ? '🚨 Buzzer ON | Fan ON' : (cond === 'warning' ? '⚠️ Fan ON' : 'Normal');

    return `
      <tr>
        <td>#${r.id}</td>
        <td>${formattedDate}</td>
        <td><strong>${Math.round(r.mq135)}</strong> ADC</td>
        <td>${r.temperature.toFixed(1)} °C</td>
        <td>${r.humidity.toFixed(1)} %</td>
        <td><span class="table-badge ${badgeClass}">${r.prediction}</span></td>
        <td><small style="color:var(--text-muted)">${actuatorSummary}</small></td>
      </tr>
    `;
  }).join('');

  elements.telemetryTableBody.innerHTML = rows;
}

// ============================================================================
// Interactive Dynamic Canvas Chart Engine
// ============================================================================

function renderChart() {
  const canvas = elements.telemetryCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // Handle Hi-DPI Retina Displays
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = rect.width;
  const height = rect.height;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);

  ctx.clearRect(0, 0, width, height);

  // If no history, generate representative trend or empty grid
  const dataPoints = state.history.slice(0, 25).reverse();
  const padding = { top: 25, right: 30, bottom: 35, left: 45 };
  const graphWidth = width - padding.left - padding.right;
  const graphHeight = height - padding.top - padding.bottom;

  // Draw Grid Lines
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1;
  const gridRows = 4;
  for (let i = 0; i <= gridRows; i++) {
    const y = padding.top + (graphHeight / gridRows) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    // Axis label (ADC scale 0 to 1500)
    const val = Math.round(1500 - (1500 / gridRows) * i);
    ctx.fillStyle = '#64748b';
    ctx.font = '10px "JetBrains Mono"';
    ctx.textAlign = 'right';
    ctx.fillText(val, padding.left - 8, y + 3);
  }

  // Draw Threshold Line (738 ADC)
  const thresholdY = padding.top + graphHeight * (1 - 738 / 1500);
  ctx.beginPath();
  ctx.setLineDash([4, 4]);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.5;
  ctx.moveTo(padding.left, thresholdY);
  ctx.lineTo(width - padding.right, thresholdY);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.fillStyle = '#ef4444';
  ctx.font = 'bold 10px "JetBrains Mono"';
  ctx.textAlign = 'right';
  ctx.fillText('738 ADC (Threshold)', width - padding.right, thresholdY - 6);

  if (dataPoints.length < 2) {
    ctx.fillStyle = '#94a3b8';
    ctx.font = '13px "Inter"';
    ctx.textAlign = 'center';
    ctx.fillText('Waiting for telemetry stream... Ingest readings above to draw real-time curves.', width / 2, height / 2);
    return;
  }

  // Coordinate mapper
  const getX = (idx) => padding.left + (idx / (dataPoints.length - 1)) * graphWidth;
  const getY = (val, maxVal) => padding.top + graphHeight * (1 - Math.min(1.0, Math.max(0, val / maxVal)));

  // 1. Draw MQ135 Gas Line & Gradient Fill (Cyan)
  ctx.beginPath();
  dataPoints.forEach((d, i) => {
    const x = getX(i);
    const y = getY(d.mq135, 1500);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Gradient fill under gas curve
  const gasFill = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  gasFill.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
  gasFill.addColorStop(1, 'rgba(56, 189, 248, 0.0)');
  ctx.lineTo(getX(dataPoints.length - 1), height - padding.bottom);
  ctx.lineTo(getX(0), height - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = gasFill;
  ctx.fill();

  // 2. Draw Temperature Curve (Amber, scaled 0 to 40)
  ctx.beginPath();
  dataPoints.forEach((d, i) => {
    const x = getX(i);
    const y = getY(d.temperature * (1500 / 40), 1500);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // 3. Draw Humidity Curve (Green, scaled 0 to 100)
  ctx.beginPath();
  dataPoints.forEach((d, i) => {
    const x = getX(i);
    const y = getY(d.humidity * (1500 / 100), 1500);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#10b981';
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // Draw node points for latest reading
  const lastIdx = dataPoints.length - 1;
  const lastPoint = dataPoints[lastIdx];
  const lastX = getX(lastIdx);
  const lastGasY = getY(lastPoint.mq135, 1500);

  ctx.beginPath();
  ctx.arc(lastX, lastGasY, 5, 0, 2 * Math.PI);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#38bdf8';
  ctx.stroke();
}

// Window resize chart repaint
window.addEventListener('resize', () => {
  renderChart();
});

// ============================================================================
// Event Listeners & Hardware Simulation Triggers
// ============================================================================

// Slider Events
elements.mq135Slider.addEventListener('input', (e) => {
  const val = parseFloat(e.target.value);
  elements.mq135SliderVal.textContent = `${Math.round(val)} ADC`;
  state.currentTelemetry.mq135 = val;
  executeDirectPrediction(state.currentTelemetry);
});

elements.tempSlider.addEventListener('input', (e) => {
  const val = parseFloat(e.target.value);
  elements.tempSliderVal.textContent = `${val.toFixed(1)} °C`;
  state.currentTelemetry.temperature = val;
  executeDirectPrediction(state.currentTelemetry);
});

elements.humSlider.addEventListener('input', (e) => {
  const val = parseFloat(e.target.value);
  elements.humSliderVal.textContent = `${val.toFixed(1)} %`;
  state.currentTelemetry.humidity = val;
  executeDirectPrediction(state.currentTelemetry);
});

// Button: Ingest Telemetry to Backend
elements.sendReadingBtn.addEventListener('click', () => {
  ingestTelemetry(state.currentTelemetry);
});

// Button: Instant Preview
elements.livePreviewBtn.addEventListener('click', () => {
  executeDirectPrediction(state.currentTelemetry);
  showIngestStatus('Preview inference calculated', 'var(--cyan-primary)');
});

// 1-Click Real Benchmark Dataset Days
document.querySelectorAll('.btn-day').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const day = btn.dataset.day;
    try {
      showIngestStatus(`Loading real dataset ${day}...`, 'var(--cyan-primary)');
      const res = await fetch(`${API_BASE}/api/dataset/sample/${day}?count=10`);
      if (!res.ok) throw new Error(`Failed to load dataset: HTTP ${res.status}`);
      const dataset = await res.json();

      if (dataset.samples && dataset.samples.length > 0) {
        state.activeDatasetStream = dataset.samples;
        state.datasetStreamIndex = 0;

        // Apply first sample
        const sample = dataset.samples[0];
        elements.mq135Slider.value = sample.mq135;
        elements.mq135SliderVal.textContent = `${Math.round(sample.mq135)} ADC`;
        elements.tempSlider.value = sample.temperature;
        elements.tempSliderVal.textContent = `${sample.temperature.toFixed(1)} °C`;
        elements.humSlider.value = sample.humidity;
        elements.humSliderVal.textContent = `${sample.humidity.toFixed(1)} %`;

        state.currentTelemetry = {
          mq135: sample.mq135,
          temperature: sample.temperature,
          humidity: sample.humidity,
        };

        // Automatically persist into SQLite to reflect in telemetry table & charts
        await ingestTelemetry(state.currentTelemetry);
      }
    } catch (err) {
      showIngestStatus(`Error: ${err.message}`, 'var(--crimson-primary)');
    }
  });
});

// Streaming Toggle (Simulates continuous ESP32 edge device)
elements.toggleStreamingBtn.addEventListener('click', () => {
  if (state.isStreaming) {
    clearInterval(state.streamIntervalId);
    state.isStreaming = false;
    elements.toggleStreamingBtn.className = 'btn-secondary';
    elements.streamBtnText.textContent = 'Start Live Edge Stream';
  } else {
    state.isStreaming = true;
    elements.toggleStreamingBtn.className = 'btn-secondary active';
    elements.streamBtnText.textContent = 'Pause Edge Stream';

    state.streamIntervalId = setInterval(async () => {
      // If we have an active day sample stream, iterate through it; otherwise cycle days
      if (state.activeDatasetStream && state.activeDatasetStream.length > 0) {
        state.datasetStreamIndex = (state.datasetStreamIndex + 1) % state.activeDatasetStream.length;
        const s = state.activeDatasetStream[state.datasetStreamIndex];
        state.currentTelemetry = {
          mq135: s.mq135,
          temperature: s.temperature,
          humidity: s.humidity,
        };
      } else {
        // Natural progression simulation: Day 1 (495) -> Day 2 (540) -> Day 3 (650) -> Day 4 (820) -> Day 5 (1150)
        const days = [
          { mq: 495, temp: 14.1, hum: 86.5 },
          { mq: 540, temp: 14.5, hum: 85.8 },
          { mq: 660, temp: 16.2, hum: 84.1 },
          { mq: 825, temp: 19.8, hum: 78.4 },
          { mq: 1140, temp: 22.4, hum: 75.2 },
        ];
        state.currentDayIndex = (state.currentDayIndex + 1) % days.length;
        const d = days[state.currentDayIndex];
        // Add realistic ADC jitter (+- 5)
        const jitter = Math.floor(Math.random() * 11) - 5;
        state.currentTelemetry = {
          mq135: d.mq + jitter,
          temperature: parseFloat((d.temp + (Math.random() * 0.4 - 0.2)).toFixed(1)),
          humidity: parseFloat((d.hum + (Math.random() * 0.6 - 0.3)).toFixed(1)),
        };
      }

      // Sync slider UI
      elements.mq135Slider.value = state.currentTelemetry.mq135;
      elements.mq135SliderVal.textContent = `${Math.round(state.currentTelemetry.mq135)} ADC`;
      elements.tempSlider.value = state.currentTelemetry.temperature;
      elements.tempSliderVal.textContent = `${state.currentTelemetry.temperature.toFixed(1)} °C`;
      elements.humSlider.value = state.currentTelemetry.humidity;
      elements.humSliderVal.textContent = `${state.currentTelemetry.humidity.toFixed(1)} %`;

      await ingestTelemetry(state.currentTelemetry);
    }, 2500);
  }
});

// ============================================================================
// Web Serial Direct USB Hardware Ingestion
// ============================================================================
let webSerialPort = null;
let webSerialReader = null;
let webSerialKeepReading = false;

async function connectWebSerial() {
  if (!('serial' in navigator)) {
    alert('Web Serial is supported in Google Chrome or Microsoft Edge. Alternatively, run:\npython serial_bridge.py');
    return;
  }

  if (webSerialPort) {
    // Disconnect
    webSerialKeepReading = false;
    try {
      if (webSerialReader) await webSerialReader.cancel();
      await webSerialPort.close();
    } catch (e) {
      console.warn('Error during serial close:', e);
    }
    webSerialPort = null;
    elements.connectSerialBtn.innerHTML = '<span>🔌 Connect USB ESP32</span>';
    elements.connectSerialBtn.className = 'btn-primary';
    elements.edgeStatusText.textContent = 'STANDBY';
    elements.edgeStatusPill.querySelector('.pill-dot').className = 'pill-dot cyan pulse';
    showIngestStatus('ESP32 Disconnected', 'var(--text-muted)');
    return;
  }

  try {
    webSerialPort = await navigator.serial.requestPort();
    await webSerialPort.open({ baudRate: 115200 });

    elements.connectSerialBtn.innerHTML = '<span>🔌 Disconnect ESP32</span>';
    elements.connectSerialBtn.className = 'btn-secondary active';
    elements.edgeStatusText.textContent = 'HARDWARE LIVE';
    elements.edgeStatusPill.querySelector('.pill-dot').className = 'pill-dot green pulse';
    showIngestStatus('ESP32 Hardware Connected via USB!', 'var(--emerald-primary)');

    webSerialKeepReading = true;
    const textDecoder = new TextDecoderStream();
    webSerialPort.readable.pipeTo(textDecoder.writable);
    const reader = textDecoder.readable.getReader();
    webSerialReader = reader;

    let lineBuffer = '';
    let currentReading = { mq135: null, temperature: null, humidity: null };

    while (webSerialKeepReading) {
      const { value, done } = await reader.read();
      if (done) break;
      lineBuffer += value;
      const lines = lineBuffer.split('\n');
      lineBuffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
          try {
            const parsed = JSON.parse(trimmed);
            if (parsed.mq135 !== undefined) {
              const payload = {
                mq135: parseFloat(parsed.mq135),
                temperature: parseFloat(parsed.temperature || 25.0),
                humidity: parseFloat(parsed.humidity || 65.0),
              };
              await ingestTelemetry(payload);
            }
          } catch(e) {}
          continue;
        }

        if (trimmed.startsWith('MQ135:')) {
          const val = parseFloat(trimmed.replace('MQ135:', '').trim());
          if (!isNaN(val)) currentReading.mq135 = val;
        } else if (trimmed.startsWith('Temperature:')) {
          const val = parseFloat(trimmed.replace('Temperature:', '').trim());
          if (!isNaN(val)) currentReading.temperature = val;
        } else if (trimmed.startsWith('Humidity:')) {
          const val = parseFloat(trimmed.replace('Humidity:', '').trim());
          if (!isNaN(val)) currentReading.humidity = val;
        } else if (trimmed === '---' || trimmed.startsWith('===') || trimmed.startsWith('Prediction:')) {
          if (currentReading.mq135 !== null) {
            const payload = {
              mq135: currentReading.mq135,
              temperature: currentReading.temperature !== null ? currentReading.temperature : 25.0,
              humidity: currentReading.humidity !== null ? currentReading.humidity : 65.0,
            };
            await ingestTelemetry(payload);
            currentReading = { mq135: null, temperature: null, humidity: null };
          }
        }
      }
    }
  } catch (err) {
    console.error('Serial Error:', err);
    showIngestStatus(`Serial: ${err.message}`, 'var(--crimson-primary)');
    if (webSerialPort) {
      try { await webSerialPort.close(); } catch(e) {}
      webSerialPort = null;
    }
    elements.connectSerialBtn.innerHTML = '<span>🔌 Connect USB ESP32</span>';
    elements.connectSerialBtn.className = 'btn-primary';
  }
}

if (elements.connectSerialBtn) {
  elements.connectSerialBtn.addEventListener('click', connectWebSerial);
}

// Audio Toggle Button
elements.toggleAudioBtn.addEventListener('click', () => {
  state.audioMuted = !state.audioMuted;
  elements.audioIcon.textContent = state.audioMuted ? '🔇' : '🔊';
  elements.toggleAudioBtn.title = state.audioMuted ? 'Unmute Alarm Sound' : 'Mute Alarm Sound';
});

// Manual Override Toggle
elements.manualOverrideToggle.addEventListener('change', async (e) => {
  state.manualOverride = e.target.checked;
  try {
    if (state.manualOverride) {
      // Turn on fan and cooling as a manual test
      await fetch(`${API_BASE}/api/actuators/override?ventilation_fan=true&cooling_unit=true`, { method: 'POST' });
    } else {
      await fetch(`${API_BASE}/api/actuators/override?reset_overrides=true`, { method: 'POST' });
    }
    await executeDirectPrediction(state.currentTelemetry);
  } catch (err) {
    console.error('Error toggling override:', err);
  }
});

// Reset History Button
elements.clearHistoryBtn.addEventListener('click', async () => {
  if (confirm('Clear all historical telemetry records from the database?')) {
    try {
      await fetch(`${API_BASE}/api/history/reset`, { method: 'POST' });
      state.history = [];
      renderHistoryTable([]);
      renderChart();
      showIngestStatus('Database history reset', 'var(--cyan-primary)');
    } catch (err) {
      alert(`Error resetting history: ${err.message}`);
    }
  }
});

// Export CSV Button
elements.exportCsvBtn.addEventListener('click', () => {
  if (!state.history || state.history.length === 0) {
    alert('No telemetry records available to export.');
    return;
  }

  const headers = ['ID', 'UTC_Timestamp', 'MQ135_ADC', 'Temperature_C', 'Humidity_RH', 'Prediction'];
  const rows = state.history.map((r) => [
    r.id,
    r.timestamp,
    r.mq135,
    r.temperature,
    r.humidity,
    `"${r.prediction}"`,
  ]);

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `food_storage_telemetry_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

// ============================================================================
// Initialization Cycle
// ============================================================================

async function initializeApp() {
  await fetchHealth();
  await fetchLatestReading();
  await fetchHistory();

  // Background polling every 2.5s
  state.pollIntervalId = setInterval(async () => {
    if (!state.isStreaming) {
      await fetchHealth();
      await fetchHistory();
    }
  }, 2500);
}

// Kick off when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);
