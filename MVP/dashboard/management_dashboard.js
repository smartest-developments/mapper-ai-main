(function () {
  const data = window.MVP_DASHBOARD_DATA || { runs: [], summary: {} };

  const state = {
    selectedRunId: null,
    entitySizeChart: null,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function fmtInt(value) {
    return typeof value === 'number' ? value.toLocaleString('en-US') : 'n/a';
  }

  function fmtPct(value) {
    return typeof value === 'number' ? `${value.toFixed(2)}%` : 'n/a';
  }

  function toMissedPct(recallPct) {
    if (typeof recallPct !== 'number') {
      return null;
    }
    const missed = 100 - recallPct;
    return Math.max(0, Math.min(100, missed));
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function getAllRuns() {
    return Array.isArray(data.runs) ? data.runs : [];
  }

  function getStatus(run) {
    return run && typeof run.run_status === 'string' ? run.run_status : 'incomplete';
  }

  function getSuccessfulRuns() {
    return getAllRuns().filter((run) => getStatus(run) === 'success');
  }

  function getRun(runId) {
    return getAllRuns().find((run) => run.run_id === runId) || null;
  }

  function getQualityRuns(runs) {
    return runs.filter((run) => Boolean(run.quality_available));
  }

  function parseRunDate(run) {
    const runId = typeof run?.run_id === 'string' ? run.run_id : '';
    const match = runId.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
    if (match) {
      const [, y, m, d, hh, mm, ss] = match;
      return new Date(Number(y), Number(m) - 1, Number(d), Number(hh), Number(mm), Number(ss));
    }
    if (typeof run?.run_datetime === 'string') {
      const parsed = new Date(run.run_datetime);
      if (!Number.isNaN(parsed.getTime())) {
        return parsed;
      }
    }
    return null;
  }

  function formatRunLabel(run) {
    const date = parseRunDate(run);
    const sourceName =
      (typeof run?.source_input_name === 'string' && run.source_input_name.trim()) ||
      (typeof run?.run_label === 'string' && run.run_label.trim()) ||
      '';
    if (!date || Number.isNaN(date.getTime())) {
      return sourceName || run.run_id;
    }
    const formatted = new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date);
    return sourceName ? `${sourceName} | ${formatted}` : formatted;
  }

  function ensureSelectedRun() {
    const filtered = getSuccessfulRuns();
    if (!filtered.length) {
      state.selectedRunId = null;
      return;
    }
    if (filtered.some((run) => run.run_id === state.selectedRunId)) {
      return;
    }
    state.selectedRunId = filtered[0].run_id;
  }

  function renderSelectedRunCards(run) {
    const matchMissed = toMissedPct(run.pair_recall_pct);
    const extraGain = typeof run.extra_gain_vs_known_pct === 'number' ? run.extra_gain_vs_known_pct : null;
    const fpPct = typeof run.overall_false_positive_pct === 'number' ? run.overall_false_positive_pct : null;
    const ourCoverage = typeof run.our_match_coverage_pct === 'number' ? run.our_match_coverage_pct : null;
    const cards = [
      { label: 'Selected Input Records', value: fmtInt(run.records_input) },
      { label: 'Matched Pairs', value: fmtInt(run.matched_pairs) },
      { label: 'Our Match Coverage', value: fmtPct(ourCoverage) },
      { label: 'Match Correctness', value: fmtPct(run.pair_precision_pct) },
      { label: 'Match Missed', value: fmtPct(matchMissed) },
      { label: 'False Positive %', value: fmtPct(fpPct) },
      { label: 'Extra True Matches Found', value: fmtInt(run.extra_true_matches_found) },
      { label: 'Senzing Gain vs Our Matches', value: fmtPct(extraGain) },
      { label: 'Selected False Negative', value: fmtInt(run.false_negative) },
      { label: 'Selected Resolved Entities', value: fmtInt(run.resolved_entities) },
    ];

    byId('selectedRunCards').innerHTML = cards
      .map(
        (card) => `
          <div class="col-sm-6 col-lg-4 col-xl-3 fade-up">
            <div class="card metric-card">
              <div class="card-body">
                <div class="metric-label">${escapeHtml(card.label)}</div>
                <div class="metric-value">${escapeHtml(card.value)}</div>
              </div>
            </div>
          </div>
        `
      )
      .join('');
  }

  function renderSelector() {
    const runs = getSuccessfulRuns();
    const selector = byId('runSelector');
    selector.innerHTML = runs
      .map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(formatRunLabel(run))}</option>`)
      .join('');
    if (state.selectedRunId) {
      selector.value = state.selectedRunId;
    }
  }

  function destroyChart(name) {
    if (state[name]) {
      state[name].destroy();
      state[name] = null;
    }
  }

  function toDistribution(obj) {
    const entries = Object.entries(obj || {})
      .map(([k, v]) => [String(k), Number(v)])
      .filter(([, v]) => Number.isFinite(v))
      .sort((a, b) => Number(a[0]) - Number(b[0]));
    return {
      labels: entries.map(([k]) => k),
      values: entries.map(([, v]) => v),
    };
  }

  function renderSelectedCharts(run) {
    destroyChart('entitySizeChart');

    const entity = toDistribution(run.entity_size_distribution);
    state.entitySizeChart = new Chart(byId('entitySizeChart'), {
      type: 'bar',
      data: {
        labels: entity.labels,
        datasets: [
          {
            label: 'Entity count',
            data: entity.values,
            backgroundColor: '#ffffff',
            borderColor: '#ffffff',
            hoverBackgroundColor: '#ffffff',
            hoverBorderColor: '#ffffff',
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            ticks: { color: '#e6edf8' },
            grid: { color: 'rgba(230,237,248,0.14)' },
          },
          y: {
            ticks: { color: '#e6edf8' },
            grid: { color: 'rgba(230,237,248,0.14)' },
          },
        },
      },
    });
    renderTopMatchKeys(run);
  }

  function prettifyMatchKey(rawKey) {
    if (typeof rawKey !== 'string') {
      return '';
    }
    return rawKey.replaceAll('+', ', ');
  }

  function renderTopMatchKeys(run) {
    const container = byId('matchKeyList');
    if (!container) {
      return;
    }
    const topKeys = Array.isArray(run.top_match_keys) ? run.top_match_keys : [];
    if (!topKeys.length) {
      container.innerHTML = '<div class="match-key-empty">No match keys available for this run.</div>';
      return;
    }

    const counts = topKeys.map((item) => (typeof item[1] === 'number' ? item[1] : 0));
    const maxCount = Math.max(...counts, 1);
    const total = counts.reduce((acc, value) => acc + value, 0) || 1;

    container.innerHTML = topKeys
      .map((item, index) => {
        const rawLabel = typeof item[0] === 'string' ? item[0] : '';
        const count = typeof item[1] === 'number' ? item[1] : 0;
        const widthPct = (count / maxCount) * 100;
        const sharePct = (count / total) * 100;
        return `
          <div class="match-key-row">
            <div class="match-key-rank">#${index + 1}</div>
            <div class="match-key-center">
              <div class="match-key-label-line">
                <span class="match-key-label" title="${escapeHtml(rawLabel)}">${escapeHtml(prettifyMatchKey(rawLabel))}</span>
                <span class="match-key-share">${sharePct.toFixed(1)}%</span>
              </div>
              <div class="match-key-track">
                <div class="match-key-fill" style="width:${widthPct.toFixed(2)}%"></div>
              </div>
            </div>
            <div class="match-key-count">${fmtInt(count)}</div>
          </div>
        `;
      })
      .join('');
  }

  function renderCurrent() {
    const run = getRun(state.selectedRunId);
    if (!run) {
      byId('selectedRunCards').innerHTML =
        '<div class="col-12"><div class="alert alert-warning">No data available for selected run.</div></div>';
      return;
    }
    renderSelectedRunCards(run);
    renderSelectedCharts(run);
  }

  function bindEvents() {
    byId('runSelector').addEventListener('change', (event) => {
      state.selectedRunId = event.target.value;
      renderCurrent();
    });
  }

  function renderEmptyState() {
    byId('selectedRunCards').innerHTML =
      '<div class="col-12"><div class="alert alert-warning">Selected run details will appear here after the first successful run.</div></div>';
    byId('runSelector').innerHTML = '';
  }

  function boot() {
    if (!getSuccessfulRuns().length) {
      renderEmptyState();
      return;
    }
    state.selectedRunId = getSuccessfulRuns()[0].run_id;

    ensureSelectedRun();
    renderSelector();
    bindEvents();
    renderCurrent();
  }

  boot();
})();
