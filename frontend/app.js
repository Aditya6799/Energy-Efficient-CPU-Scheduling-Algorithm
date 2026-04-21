/**
 * ═══════════════════════════════════════════════════════════════
 *  AEAS — Adaptive Energy-Aware CPU Scheduler
 *  Frontend Application Logic
 *  Handles: Process input, API calls, Chart rendering (Plotly.js)
 * ═══════════════════════════════════════════════════════════════
 */

// ─── Configuration ─────────────────────────────────────────────
const API_BASE = '';
const FREQ_COLORS = {
    HIGH:       '#ef4444',
    MEDIUM:     '#f59e0b',
    LOW:        '#22c55e',
    IDLE:       '#475569',
    CTX_SWITCH: '#8b5cf6'
};
const ALGO_COLORS = {
    'AEAS':        '#14b8a6',
    'FCFS':        '#3b82f6',
    'SJF':         '#8b5cf6',
    'Round Robin': '#f59e0b',
    'Priority':    '#ef4444'
};
// Dynamic Plotly layout that reads CSS variables for theme support
function getPlotlyLayout() {
    const s = getComputedStyle(document.documentElement);
    return {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor:  s.getPropertyValue('--plotly-bg').trim(),
        font: { family: 'Inter, sans-serif', color: s.getPropertyValue('--plotly-font').trim(), size: 12 },
        margin: { l: 60, r: 30, t: 40, b: 50 },
        xaxis: { gridcolor: s.getPropertyValue('--plotly-grid').trim(), zerolinecolor: s.getPropertyValue('--plotly-zeroline').trim() },
        yaxis: { gridcolor: s.getPropertyValue('--plotly-grid').trim(), zerolinecolor: s.getPropertyValue('--plotly-zeroline').trim() }
    };
}
function getPlotlyTitleColor() {
    return getComputedStyle(document.documentElement).getPropertyValue('--plotly-title').trim();
}
function getPieLine() {
    return getComputedStyle(document.documentElement).getPropertyValue('--plotly-pie-line').trim();
}
const PLOTLY_CONFIG = { responsive: true, displayModeBar: true, displaylogo: false };

// ─── Preset Test Cases ─────────────────────────────────────────
const PRESETS = {
    basic: [
        { id: 'P1', arrival_time: 0, burst_time: 6, priority: 1 },
        { id: 'P2', arrival_time: 1, burst_time: 3, priority: 4 },
        { id: 'P3', arrival_time: 2, burst_time: 8, priority: 3 },
        { id: 'P4', arrival_time: 3, burst_time: 2, priority: 2 },
        { id: 'P5', arrival_time: 4, burst_time: 5, priority: 5 }
    ],
    high_load: [
        { id: 'P1', arrival_time: 0, burst_time: 10, priority: 3 },
        { id: 'P2', arrival_time: 0, burst_time: 4,  priority: 1 },
        { id: 'P3', arrival_time: 1, burst_time: 7,  priority: 5 },
        { id: 'P4', arrival_time: 1, burst_time: 2,  priority: 2 },
        { id: 'P5', arrival_time: 2, burst_time: 6,  priority: 4 },
        { id: 'P6', arrival_time: 2, burst_time: 3,  priority: 1 },
        { id: 'P7', arrival_time: 3, burst_time: 9,  priority: 5 },
        { id: 'P8', arrival_time: 3, burst_time: 1,  priority: 2 }
    ],
    same_arrival: [
        { id: 'P1', arrival_time: 0, burst_time: 5, priority: 3 },
        { id: 'P2', arrival_time: 0, burst_time: 2, priority: 1 },
        { id: 'P3', arrival_time: 0, burst_time: 8, priority: 4 },
        { id: 'P4', arrival_time: 0, burst_time: 3, priority: 2 },
        { id: 'P5', arrival_time: 0, burst_time: 6, priority: 5 },
        { id: 'P6', arrival_time: 0, burst_time: 1, priority: 1 }
    ],
    mixed_priorities: [
        { id: 'P1', arrival_time: 0, burst_time: 12, priority: 5 },
        { id: 'P2', arrival_time: 1, burst_time: 3,  priority: 1 },
        { id: 'P3', arrival_time: 2, burst_time: 7,  priority: 2 },
        { id: 'P4', arrival_time: 3, burst_time: 1,  priority: 4 },
        { id: 'P5', arrival_time: 5, burst_time: 9,  priority: 3 },
        { id: 'P6', arrival_time: 6, burst_time: 4,  priority: 1 },
        { id: 'P7', arrival_time: 8, burst_time: 2,  priority: 2 }
    ],
    single_process: [
        { id: 'P1', arrival_time: 0, burst_time: 5, priority: 3 }
    ],
    staggered_arrival: [
        { id: 'P1', arrival_time: 0,  burst_time: 3, priority: 2 },
        { id: 'P2', arrival_time: 10, burst_time: 5, priority: 4 },
        { id: 'P3', arrival_time: 20, burst_time: 2, priority: 1 },
        { id: 'P4', arrival_time: 25, burst_time: 7, priority: 3 }
    ]
};

// ─── State ─────────────────────────────────────────────────────
let processCounter = 0;
let lastSimData = null;     // Cache last simulation data for re-render on theme change
let lastCompareData = null; // Cache last comparison data for re-render on theme change

// ─── DOM References ────────────────────────────────────────────
const $  = id => document.getElementById(id);
const tbody            = $('process-tbody');
const presetSelect     = $('preset-select');
const addProcessBtn    = $('add-process-btn');
const clearBtn         = $('clear-btn');
const simulateBtn      = $('simulate-btn');
const compareBtn       = $('compare-btn');
const evaluateBtn      = $('evaluate-btn');
const dvfsCheckbox     = $('dvfs-checkbox');
const dvfsStatus       = $('dvfs-status');
const loadingOverlay   = $('loading-overlay');
const resultsContainer = $('results-container');

// ═══════════════════════════════════════════════════════════════
//  PROCESS TABLE MANAGEMENT
// ═══════════════════════════════════════════════════════════════

function addProcessRow(proc = null) {
    processCounter++;
    const id  = proc?.id ?? `P${processCounter}`;
    const at  = proc?.arrival_time ?? 0;
    const bt  = proc?.burst_time ?? 1;
    const pri = proc?.priority ?? 3;

    const tr = document.createElement('tr');
    tr.dataset.pid = id;
    tr.innerHTML = `
        <td><input type="text" value="${id}" readonly class="pid-input" aria-label="Process ID"></td>
        <td><input type="number" value="${at}" min="0" step="1" class="at-input" aria-label="Arrival Time"></td>
        <td><input type="number" value="${bt}" min="1" step="1" class="bt-input" aria-label="Burst Time"></td>
        <td><input type="number" value="${pri}" min="1" max="10" step="1" class="pri-input" aria-label="Priority"></td>
        <td>
            <button class="btn-remove" title="Remove process" aria-label="Remove process ${id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </td>
    `;
    tr.querySelector('.btn-remove').addEventListener('click', () => {
        tr.style.opacity = '0';
        tr.style.transform = 'translateX(20px)';
        tr.style.transition = 'all 0.2s ease';
        setTimeout(() => tr.remove(), 200);
    });
    tbody.appendChild(tr);

    // Animate entry
    tr.style.opacity = '0';
    tr.style.transform = 'translateY(8px)';
    requestAnimationFrame(() => {
        tr.style.transition = 'all 0.25s ease';
        tr.style.opacity = '1';
        tr.style.transform = 'translateY(0)';
    });
}

function getProcesses() {
    const rows = tbody.querySelectorAll('tr');
    const processes = [];
    rows.forEach(tr => {
        processes.push({
            id:           tr.querySelector('.pid-input').value.trim(),
            arrival_time: parseFloat(tr.querySelector('.at-input').value) || 0,
            burst_time:   Math.max(0.1, parseFloat(tr.querySelector('.bt-input').value) || 1),
            priority:     parseInt(tr.querySelector('.pri-input').value) || 3
        });
    });
    return processes;
}

function loadPreset(name) {
    if (!PRESETS[name]) return;
    tbody.innerHTML = '';
    processCounter = 0;
    PRESETS[name].forEach(p => addProcessRow(p));
}

function clearTable() {
    tbody.innerHTML = '';
    processCounter = 0;
    resultsContainer.classList.add('hidden');
}

// ═══════════════════════════════════════════════════════════════
//  API CALLS
// ═══════════════════════════════════════════════════════════════

async function apiCall(endpoint, body) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `API error: ${res.status}`);
    }
    return res.json();
}

function showLoading() { loadingOverlay.classList.add('active'); }
function hideLoading() { loadingOverlay.classList.remove('active'); }

function showError(msg) {
    hideLoading();
    alert(msg);
}

// ═══════════════════════════════════════════════════════════════
//  SIMULATE (Run AEAS)
// ═══════════════════════════════════════════════════════════════

async function runSimulate() {
    const processes = getProcesses();
    if (processes.length === 0) return showError('Please add at least one process.');

    showLoading();
    try {
        const data = await apiCall('/api/simulate', {
            processes,
            dvfs_enabled: dvfsCheckbox.checked,
            context_switch_time: parseFloat($('cs-time').value) || 0
        });
        hideLoading();
        resultsContainer.classList.remove('hidden');
        $('comparison-section').classList.add('hidden');
        $('evaluation-section').classList.add('hidden');
        renderSimulationResults(data);
    } catch (e) {
        showError(e.message);
    }
}

// ═══════════════════════════════════════════════════════════════
//  COMPARE (AEAS vs Baselines)
// ═══════════════════════════════════════════════════════════════

async function runCompare() {
    const processes = getProcesses();
    if (processes.length === 0) return showError('Please add at least one process.');

    showLoading();
    try {
        const data = await apiCall('/api/compare', {
            processes,
            dvfs_enabled: dvfsCheckbox.checked,
            context_switch_time: parseFloat($('cs-time').value) || 0
        });
        hideLoading();
        resultsContainer.classList.remove('hidden');
        $('evaluation-section').classList.add('hidden');

        // Render AEAS results first
        renderSimulationResults(data.algorithms['AEAS']);

        // Render comparison
        $('comparison-section').classList.remove('hidden');
        renderComparison(data);
    } catch (e) {
        showError(e.message);
    }
}

// ═══════════════════════════════════════════════════════════════
//  EVALUATE (Full Report)
// ═══════════════════════════════════════════════════════════════

async function runEvaluate() {
    const processes = getProcesses();
    if (processes.length === 0) return showError('Please add at least one process.');

    showLoading();
    try {
        // First get comparison data for charts
        const compareData = await apiCall('/api/compare', {
            processes,
            dvfs_enabled: dvfsCheckbox.checked,
            context_switch_time: parseFloat($('cs-time').value) || 0
        });
        // Then get evaluation report
        const evalData = await apiCall('/api/evaluate', {
            processes,
            dvfs_enabled: dvfsCheckbox.checked,
            context_switch_time: parseFloat($('cs-time').value) || 0
        });
        hideLoading();
        resultsContainer.classList.remove('hidden');

        renderSimulationResults(compareData.algorithms['AEAS']);
        $('comparison-section').classList.remove('hidden');
        renderComparison(compareData);
        $('evaluation-section').classList.remove('hidden');
        renderEvaluation(evalData);
    } catch (e) {
        showError(e.message);
    }
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: AEAS Simulation Results
// ═══════════════════════════════════════════════════════════════

function renderSimulationResults(data) {
    // Metrics cards
    const m = data.metrics;
    const e = data.energy;
    $('aeas-metrics').innerHTML = `
        <div class="metric-card">
            <div class="metric-value">${m.avg_waiting_time.toFixed(2)}</div>
            <div class="metric-label">Avg Waiting Time</div>
            <div class="metric-unit">time units</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${m.avg_turnaround_time.toFixed(2)}</div>
            <div class="metric-label">Avg Turnaround Time</div>
            <div class="metric-unit">time units</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${m.throughput.toFixed(4)}</div>
            <div class="metric-label">Throughput</div>
            <div class="metric-unit">proc/unit</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${m.cpu_utilization.toFixed(1)}%</div>
            <div class="metric-label">CPU Utilization</div>
            <div class="metric-unit"></div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${e.total_energy.toFixed(2)}</div>
            <div class="metric-label">Total Energy</div>
            <div class="metric-unit">Joules</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">${data.energy_savings_vs_full_power.toFixed(1)}%</div>
            <div class="metric-label">Energy Saved vs Full Power</div>
            <div class="metric-unit"></div>
        </div>
    `;

    // Energy breakdown
    $('aeas-energy-breakdown').innerHTML = `
        <div class="energy-item"><span class="energy-dot high"></span>Active Energy<span class="energy-val">${e.active_energy.toFixed(3)} J</span></div>
        <div class="energy-item"><span class="energy-dot idle"></span>Idle Energy<span class="energy-val">${e.idle_energy.toFixed(3)} J</span></div>
        <div class="energy-item"><span class="energy-dot ctx"></span>Context Switch<span class="energy-val">${e.context_switch_energy.toFixed(3)} J</span></div>
        <div class="energy-item"><span class="energy-dot medium"></span>Total<span class="energy-val">${e.total_energy.toFixed(3)} J</span></div>
    `;

    // Cache data for re-render on theme switch
    lastSimData = data;

    // Charts
    renderGanttChart(data.gantt);
    renderEnergyChart(data);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Gantt Chart (Plotly)
// ═══════════════════════════════════════════════════════════════

function renderGanttChart(gantt) {
    // Group entries so each process gets one row
    const processIds = [...new Set(gantt.map(g => g.process))];
    const traces = [];

    gantt.forEach(entry => {
        const color = FREQ_COLORS[entry.frequency] || FREQ_COLORS.IDLE;
        const yIdx = processIds.indexOf(entry.process);
        const label = entry.process === 'CTX_SWITCH' ? 'CS' : 
                     entry.process === 'IDLE' ? 'IDLE' : entry.process;

        traces.push({
            x: [entry.start, entry.end],
            y: [label, label],
            mode: 'lines',
            line: { color, width: 22 },
            showlegend: false,
            hoverinfo: 'text',
            text: `${entry.process}<br>Time: ${entry.start} → ${entry.end}<br>Freq: ${entry.frequency}<br>Duration: ${entry.duration}`
        });

        // Add label text in center
        if (entry.duration >= 0.5) {
            traces.push({
                x: [(entry.start + entry.end) / 2],
                y: [label],
                mode: 'text',
                text: [`${entry.frequency === 'IDLE' ? '' : entry.frequency.charAt(0)}`],
                textfont: { color: '#fff', size: 9, family: 'JetBrains Mono' },
                showlegend: false,
                hoverinfo: 'skip'
            });
        }
    });

    // Legend entries for frequency levels
    Object.entries(FREQ_COLORS).forEach(([freq, color]) => {
        traces.push({
            x: [null], y: [null],
            mode: 'lines',
            line: { color, width: 8 },
            name: freq,
            showlegend: true
        });
    });

    const base = getPlotlyLayout();
    const layout = {
        ...base,
        title: { text: 'Execution Timeline (Gantt)', font: { size: 14, color: getPlotlyTitleColor() } },
        xaxis: { ...base.xaxis, title: 'Time Units', dtick: 1 },
        yaxis: { ...base.yaxis, autorange: 'reversed', type: 'category' },
        legend: { orientation: 'h', y: -0.2, font: { size: 10 } },
        height: Math.max(300, processIds.length * 45 + 100)
    };

    Plotly.newPlot('gantt-chart', traces, layout, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Energy Chart
// ═══════════════════════════════════════════════════════════════

function renderEnergyChart(data) {
    const e = data.energy;
    const processEnergy = e.process_energy || {};
    const pids = Object.keys(processEnergy);

    // Per-process energy bar chart
    const barTrace = {
        x: pids,
        y: pids.map(pid => processEnergy[pid]),
        type: 'bar',
        marker: {
            color: pids.map((_, i) => {
                const hue = (175 + i * 40) % 360;
                return `hsl(${hue}, 70%, 55%)`;
            }),
            line: { width: 0 }
        },
        name: 'Process Energy',
        hovertemplate: '%{x}: %{y:.3f} J<extra></extra>'
    };

    // Breakdown pie (as subplot or separate)
    const breakdownLabels = ['Active', 'Idle', 'Context Switch'];
    const breakdownValues = [e.active_energy, e.idle_energy, e.context_switch_energy];
    const breakdownColors = ['#14b8a6', '#475569', '#8b5cf6'];

    const pieTrace = {
        labels: breakdownLabels,
        values: breakdownValues,
        type: 'pie',
        hole: 0.55,
        marker: { colors: breakdownColors, line: { color: getPieLine(), width: 2 } },
        textinfo: 'label+percent',
        textfont: { size: 11, color: getPlotlyTitleColor() },
        domain: { x: [0.65, 1], y: [0.1, 0.9] },
        showlegend: false,
        hovertemplate: '%{label}: %{value:.3f} J (%{percent})<extra></extra>'
    };

    const base = getPlotlyLayout();
    const layout = {
        ...base,
        title: { text: 'Energy Consumption Breakdown', font: { size: 14, color: getPlotlyTitleColor() } },
        xaxis: { ...base.xaxis, title: 'Process', domain: [0, 0.55] },
        yaxis: { ...base.yaxis, title: 'Energy (Joules)' },
        height: 380,
        showlegend: false
    };

    Plotly.newPlot('energy-chart', [barTrace, pieTrace], layout, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Comparison
// ═══════════════════════════════════════════════════════════════

function renderComparison(data) {
    const algos = data.algorithms;
    const comparisons = data.comparisons;
    let cardsHtml = '';

    // Algorithm cards
    Object.entries(algos).forEach(([name, algo]) => {
        const isAeas = name === 'AEAS';
        const m = algo.metrics;
        const e = algo.energy;

        let savingsHtml = '';
        if (isAeas && comparisons) {
            const avgSaved = Object.values(comparisons).reduce((s, c) => s + c.energy_saved_pct, 0) / Object.keys(comparisons).length;
            savingsHtml = `
                <div class="algo-stat">
                    <span class="stat-label">Avg Energy Saved</span>
                    <span class="stat-value" style="color: ${avgSaved > 0 ? '#22c55e' : '#ef4444'}">${avgSaved.toFixed(1)}%</span>
                </div>
            `;
        }

        cardsHtml += `
            <div class="algo-card ${isAeas ? 'aeas' : ''}">
                <div class="algo-name">${name}</div>
                <div class="algo-stat">
                    <span class="stat-label">Avg Wait</span>
                    <span class="stat-value">${m.avg_waiting_time.toFixed(2)}</span>
                </div>
                <div class="algo-stat">
                    <span class="stat-label">Avg TAT</span>
                    <span class="stat-value">${m.avg_turnaround_time.toFixed(2)}</span>
                </div>
                <div class="algo-stat">
                    <span class="stat-label">Throughput</span>
                    <span class="stat-value">${m.throughput.toFixed(4)}</span>
                </div>
                <div class="algo-stat">
                    <span class="stat-label">CPU Util</span>
                    <span class="stat-value">${m.cpu_utilization.toFixed(1)}%</span>
                </div>
                <div class="algo-stat">
                    <span class="stat-label">Energy</span>
                    <span class="stat-value">${e.total_energy.toFixed(2)} J</span>
                </div>
                ${savingsHtml}
            </div>
        `;
    });

    $('comparison-cards').innerHTML = cardsHtml;

    // Cache for re-render
    lastCompareData = data;

    // Performance comparison bar chart
    renderPerformanceChart(algos);

    // Scatter plot: energy vs performance
    renderScatterChart(algos);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Performance Comparison Chart
// ═══════════════════════════════════════════════════════════════

function renderPerformanceChart(algos) {
    const names = Object.keys(algos);

    const waitTrace = {
        x: names,
        y: names.map(n => algos[n].metrics.avg_waiting_time),
        name: 'Avg Waiting Time',
        type: 'bar',
        marker: { color: 'rgba(59, 130, 246, 0.8)', line: { width: 0 } }
    };

    const tatTrace = {
        x: names,
        y: names.map(n => algos[n].metrics.avg_turnaround_time),
        name: 'Avg Turnaround Time',
        type: 'bar',
        marker: { color: 'rgba(139, 92, 246, 0.8)', line: { width: 0 } }
    };

    const energyTrace = {
        x: names,
        y: names.map(n => algos[n].energy.total_energy),
        name: 'Total Energy (J)',
        type: 'bar',
        marker: { color: 'rgba(20, 184, 166, 0.8)', line: { width: 0 } }
    };

    const base = getPlotlyLayout();
    const layout = {
        ...base,
        title: { text: 'Performance & Energy Comparison', font: { size: 14, color: getPlotlyTitleColor() } },
        barmode: 'group',
        legend: { orientation: 'h', y: -0.2, font: { size: 11, color: getPlotlyLayout().font.color } },
        height: 380
    };

    Plotly.newPlot('performance-chart', [waitTrace, tatTrace, energyTrace], layout, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Scatter Plot (Energy vs Performance Trade-off)
// ═══════════════════════════════════════════════════════════════

function renderScatterChart(algos) {
    const titleColor = getPlotlyTitleColor();
    const traces = Object.entries(algos).map(([name, algo]) => {
        const isAeas = name === 'AEAS';
        return {
            x: [algo.energy.total_energy],
            y: [algo.metrics.avg_waiting_time],
            mode: 'markers+text',
            marker: {
                size: isAeas ? 20 : 14,
                color: ALGO_COLORS[name],
                symbol: isAeas ? 'star' : 'circle',
                line: { width: isAeas ? 2 : 1, color: titleColor }
            },
            text: [name],
            textposition: 'top center',
            textfont: { size: 11, color: titleColor, family: 'Inter' },
            name,
            showlegend: true,
            hovertemplate: `${name}<br>Energy: %{x:.2f} J<br>Avg Wait: %{y:.2f}<extra></extra>`
        };
    });

    const base = getPlotlyLayout();
    const layout = {
        ...base,
        title: { text: 'Energy vs Performance Trade-off', font: { size: 14, color: titleColor } },
        xaxis: { ...base.xaxis, title: 'Total Energy (Joules)' },
        yaxis: { ...base.yaxis, title: 'Avg Waiting Time' },
        legend: { orientation: 'h', y: -0.2, font: { size: 11, color: base.font.color } },
        height: 400,
        annotations: [{
            x: 0.02, y: 0.98, xref: 'paper', yref: 'paper',
            text: '\u2190 Lower Energy, Lower Wait = Better',
            showarrow: false,
            font: { size: 10, color: '#64748b', style: 'italic' }
        }]
    };

    Plotly.newPlot('scatter-chart', traces, layout, PLOTLY_CONFIG);
}

// ═══════════════════════════════════════════════════════════════
//  RENDER: Evaluation Report
// ═══════════════════════════════════════════════════════════════

function renderEvaluation(data) {
    const statusClass = data.recommendation_status.toLowerCase();
    let html = '';

    // Recommendation banner
    html += `
        <div class="eval-recommendation ${statusClass}">
            <div class="rec-status">${data.recommendation_status}</div>
            <div class="rec-text">${data.recommendation}</div>
        </div>
    `;

    // Best algorithm banner
    html += `
        <div class="best-algo-banner">
            <div>
                <div class="best-label">Most Efficient Algorithm</div>
                <div class="best-name">${data.best_algorithm.name}</div>
                <div class="best-score">Efficiency Score: ${data.best_algorithm.efficiency_score.toFixed(6)}</div>
            </div>
        </div>
    `;

    // Average energy savings
    html += `
        <div style="text-align:center; margin-bottom:24px;">
            <span style="font-family: var(--font-mono); font-size: 2rem; font-weight: 800; color: ${data.avg_energy_saved_pct > 0 ? '#22c55e' : '#ef4444'}">
                ${data.avg_energy_saved_pct > 0 ? '↓' : '↑'} ${Math.abs(data.avg_energy_saved_pct).toFixed(1)}%
            </span>
            <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">Average Energy Savings vs Baselines</div>
        </div>
    `;

    // Constraint checks grid
    html += `<h3 style="font-size:0.9rem; color:#e2e8f0; margin-bottom:12px;">
        ≤ 5% Performance Degradation Constraint Checks
    </h3>`;
    html += '<div class="constraint-grid">';

    Object.entries(data.constraint_checks).forEach(([name, check]) => {
        const passClass = check.constraint_pass ? 'pass' : 'fail';
        const passText  = check.constraint_pass ? '✓ PASS' : '✗ FAIL';
        const energyClass = check.energy_saved_pct > 0 ? 'positive' : (check.energy_saved_pct < 0 ? 'negative' : 'neutral-val');
        const perfClass = check.performance_change_pct <= 5 ? 'positive' : 'negative';

        html += `
            <div class="constraint-card">
                <div class="constraint-header">
                    <span class="constraint-algo">vs ${name}</span>
                    <span class="badge ${passClass}">${passText}</span>
                </div>
                <div class="constraint-stat">
                    <span class="c-label">Energy Saved</span>
                    <span class="c-value ${energyClass}">${check.energy_saved_pct.toFixed(1)}%</span>
                </div>
                <div class="constraint-stat">
                    <span class="c-label">Perf Change</span>
                    <span class="c-value ${perfClass}">${check.performance_change_pct > 0 ? '+' : ''}${check.performance_change_pct.toFixed(1)}%</span>
                </div>
                <div class="constraint-stat">
                    <span class="c-label">Max Allowed</span>
                    <span class="c-value neutral-val">≤ ${check.max_allowed_degradation}%</span>
                </div>
            </div>
        `;
    });

    html += '</div>';

    // Overall verdict
    html += `
        <div style="text-align:center; margin-top:32px; padding:20px; border-radius:12px; background: ${data.all_constraints_pass ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)'}; border: 1px solid ${data.all_constraints_pass ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}">
            <div style="font-family: var(--font-mono); font-size: 0.75rem; font-weight: 700; color: ${data.all_constraints_pass ? '#22c55e' : '#ef4444'}; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:8px;">
                ${data.all_constraints_pass ? '✓ All Constraints Satisfied' : '⚠ Some Constraints Exceeded'}
            </div>
            <div style="font-size:0.85rem; color:#94a3b8; max-width:600px; margin:0 auto; line-height:1.7;">
                AEAS reduces energy consumption significantly while maintaining acceptable performance, making it suitable for mobile and embedded systems.
            </div>
        </div>
    `;

    $('evaluation-content').innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
//  EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════

// DVFS toggle
dvfsCheckbox.addEventListener('change', () => {
    dvfsStatus.textContent = dvfsCheckbox.checked ? 'ON' : 'OFF';
    dvfsStatus.classList.toggle('off', !dvfsCheckbox.checked);
});

// Preset selector
presetSelect.addEventListener('change', (e) => {
    if (e.target.value) {
        loadPreset(e.target.value);
        e.target.value = '';
    }
});

// Buttons
addProcessBtn.addEventListener('click', () => addProcessRow());
clearBtn.addEventListener('click', clearTable);
simulateBtn.addEventListener('click', runSimulate);
compareBtn.addEventListener('click', runCompare);
evaluateBtn.addEventListener('click', runEvaluate);

// ═══════════════════════════════════════════════════════════════
//  THEME TOGGLE
// ═══════════════════════════════════════════════════════════════

const themeToggleBtn = $('theme-toggle-btn');

function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
}

function setTheme(theme) {
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('aeas-theme', theme);

    // Re-render any visible Plotly charts with new theme colors
    requestAnimationFrame(() => {
        if (lastSimData) {
            renderGanttChart(lastSimData.gantt);
            renderEnergyChart(lastSimData);
        }
        if (lastCompareData && !$('comparison-section').classList.contains('hidden')) {
            renderPerformanceChart(lastCompareData.algorithms);
            renderScatterChart(lastCompareData.algorithms);
        }
    });
}

themeToggleBtn.addEventListener('click', () => {
    const current = getCurrentTheme();
    setTheme(current === 'dark' ? 'light' : 'dark');
});

// ═══════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Restore saved theme
    const savedTheme = localStorage.getItem('aeas-theme') || 'dark';
    setTheme(savedTheme);

    // Load default preset
    loadPreset('basic');
});
