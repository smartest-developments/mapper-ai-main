(function () {
  const data = window.MVP_DASHBOARD_DATA || { runs: [], summary: {} };
  const ALL_RUNS_ID = '__all__';

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

  function asNumber(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
  }

  function ratioPct(num, den) {
    if (typeof num !== 'number' || typeof den !== 'number' || den <= 0) {
      return null;
    }
    return (num / den) * 100;
  }

  function sumField(runs, field) {
    return runs.reduce((acc, run) => acc + (asNumber(run?.[field]) ?? 0), 0);
  }

  function mergeDistribution(runs, field) {
    const merged = {};
    for (const run of runs) {
      const source = run?.[field];
      if (!source || typeof source !== 'object') {
        continue;
      }
      for (const [key, value] of Object.entries(source)) {
        const number = Number(value);
        if (!Number.isFinite(number)) {
          continue;
        }
        merged[key] = (merged[key] || 0) + number;
      }
    }
    return merged;
  }

  function mergeTopMatchKeys(runs, limit = 10) {
    const counts = {};
    for (const run of runs) {
      const topKeys = Array.isArray(run?.top_match_keys) ? run.top_match_keys : [];
      for (const item of topKeys) {
        const key = typeof item?.[0] === 'string' ? item[0] : '';
        const count = Number(item?.[1]);
        if (!key || !Number.isFinite(count)) {
          continue;
        }
        counts[key] = (counts[key] || 0) + count;
      }
    }
    return Object.entries(counts)
      .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0]))
      .slice(0, limit);
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
    if (runId === ALL_RUNS_ID) {
      return buildAggregateRun(getSuccessfulRuns());
    }
    return getAllRuns().find((run) => run.run_id === runId) || null;
  }

  function getQualityRuns(runs) {
    return runs.filter((run) => Boolean(run.quality_available));
  }

  function buildAggregateRun(runs) {
    const selectedRuns = Array.isArray(runs) ? runs : [];
    if (!selectedRuns.length) {
      return null;
    }

    const totalInput = sumField(selectedRuns, 'records_input');
    const totalOurResolved = sumField(selectedRuns, 'our_resolved_entities');
    const totalPairs = sumField(selectedRuns, 'matched_pairs');
    const totalResolved = sumField(selectedRuns, 'resolved_entities');
    const tp = sumField(selectedRuns, 'true_positive');
    const fp = sumField(selectedRuns, 'false_positive');
    const fn = sumField(selectedRuns, 'false_negative');
    const predictedPairs = sumField(selectedRuns, 'predicted_pairs_labeled');
    const ourTruePairs = sumField(selectedRuns, 'our_true_positive');
    const ourTotalTruePairs = sumField(selectedRuns, 'our_true_pairs_total');
    const ourFalsePositive = sumField(selectedRuns, 'our_false_positive');
    const ourFalseNegative = sumField(selectedRuns, 'our_false_negative');
    const extraPairs = sumField(selectedRuns, 'extra_true_matches_found');
    const knownPairs = sumField(selectedRuns, 'known_pairs_ipg');
    const precisionPct = ratioPct(tp, tp + fp);
    const coveragePct = ratioPct(ourTruePairs, ourTotalTruePairs);
    const falsePositivePct = ratioPct(fp, predictedPairs);
    const gainPct = ratioPct(extraPairs, knownPairs);

    return {
      run_id: ALL_RUNS_ID,
      run_status: 'success',
      source_input_name: `All successful runs (${selectedRuns.length})`,
      run_label: 'All outputs (aggregate)',
      records_input: totalInput,
      our_resolved_entities: totalOurResolved,
      matched_pairs: totalPairs,
      resolved_entities: totalResolved,
      true_positive: tp,
      false_positive: fp,
      false_negative: fn,
      predicted_pairs_labeled: predictedPairs,
      our_true_positive: ourTruePairs,
      our_true_pairs_total: ourTotalTruePairs,
      our_false_positive: ourFalsePositive,
      our_false_negative: ourFalseNegative,
      extra_true_matches_found: extraPairs,
      known_pairs_ipg: knownPairs,
      extra_gain_vs_known_pct: gainPct,
      pair_precision_pct: precisionPct,
      pair_recall_pct: coveragePct,
      our_match_coverage_pct: coveragePct,
      overall_false_positive_pct: falsePositivePct,
      entity_size_distribution: mergeDistribution(selectedRuns, 'entity_size_distribution'),
      top_match_keys: mergeTopMatchKeys(selectedRuns, 10),
    };
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

  function prettifySourceName(sourceName) {
    if (typeof sourceName !== 'string') {
      return '';
    }
    const base = sourceName.replace(/\.json$/i, '');
    const tokens = base
      .split('_')
      .map((token) => token.trim())
      .filter(Boolean);
    if (!tokens.length) {
      return sourceName;
    }

    // Keep a compact, user-friendly label (few words) from filename only.
    let start = 0;
    let labelPrefix = '';
    if (tokens[0].toLowerCase() === 'sample' && tokens[1]) {
      const num = tokens[1].padStart(2, '0');
      labelPrefix = `Sample ${num}`;
      start = 2;
    }
    const stopWords = new Set(['json', 'records', 'record']);
    const core = [];
    for (let i = start; i < tokens.length; i += 1) {
      const token = tokens[i];
      if (/^\d+$/.test(token)) {
        continue;
      }
      if (stopWords.has(token.toLowerCase())) {
        continue;
      }
      core.push(token);
      if (core.length >= 3) {
        break;
      }
    }

    const phrase = core
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
    if (labelPrefix && phrase) {
      return `${labelPrefix} ${phrase}`;
    }
    return labelPrefix || phrase || sourceName;
  }

  function formatRunLabel(run) {
    const date = parseRunDate(run);
    const sourceNameRaw =
      (typeof run?.source_input_name === 'string' && run.source_input_name.trim()) ||
      (typeof run?.run_label === 'string' && run.run_label.trim()) ||
      '';
    const sourceName = prettifySourceName(sourceNameRaw);
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
    if (state.selectedRunId === ALL_RUNS_ID) {
      return;
    }
    if (filtered.some((run) => run.run_id === state.selectedRunId)) {
      return;
    }
    state.selectedRunId = ALL_RUNS_ID;
  }

  function renderSelectedRunCards(run) {
    const recallPct = asNumber(run.pair_recall_pct);
    const precisionPct = asNumber(run.pair_precision_pct);
    const matchMissed = toMissedPct(recallPct);
    const predictedPairs = asNumber(run.predicted_pairs_labeled);
    const falsePositive = asNumber(run.false_positive);
    const fallbackFalsePositivePct = ratioPct(falsePositive, predictedPairs);
    const fpPct = asNumber(run.overall_false_positive_pct) ?? fallbackFalsePositivePct;
    const ourCoverage = asNumber(run.our_match_coverage_pct) ?? recallPct;
    const ourMatchMissed = toMissedPct(ourCoverage);
    const extraPairs = asNumber(run.extra_true_matches_found) ?? 0;
    const knownPairs = asNumber(run.known_pairs_ipg);
    const gainPct = asNumber(run.extra_gain_vs_known_pct) ?? ratioPct(extraPairs, knownPairs) ?? 0;
    const ourCards = [
      { label: 'Entities', value: fmtInt(run.our_resolved_entities) },
      { label: 'Matched Pairs', value: fmtInt(run.our_true_positive) },
      { label: 'Match Found', value: fmtPct(ourCoverage) },
      { label: 'Miss-Matched', value: fmtPct(ourMatchMissed) },
      { label: 'False Positive', value: fmtInt(run.our_false_positive) },
      { label: 'False Negative', value: fmtInt(run.our_false_negative) },
      { label: 'Input Records', value: fmtInt(run.records_input) },
    ];

    const theirCards = [
      { label: 'Entities', value: fmtInt(run.resolved_entities) },
      { label: 'Matched Pairs', value: fmtInt(run.matched_pairs) },
      { label: 'Match Found', value: fmtPct(precisionPct) },
      { label: 'Miss-Matched', value: fmtPct(matchMissed) },
      { label: 'False Positive', value: fmtInt(run.false_positive) },
      { label: 'False Negative', value: fmtInt(run.false_negative) },
      { label: 'False Positive %', value: fmtPct(fpPct) },
      { label: 'Extra Pairs', value: fmtInt(extraPairs) },
      { label: 'Match Gain', value: fmtPct(gainPct) },
    ];

    byId('ourMetricCards').innerHTML = ourCards
      .map(
        (card) => `
          <div class="col-12 col-sm-6 col-xl-4 fade-up">
            <div class="card metric-card metric-card-our">
              <div class="card-body">
                <div class="metric-label">${escapeHtml(card.label)}</div>
                <div class="metric-value">${escapeHtml(card.value)}</div>
              </div>
            </div>
          </div>
        `
      )
      .join('');

    byId('theirMetricCards').innerHTML = theirCards
      .map(
        (card) => `
          <div class="col-12 col-sm-6 col-xl-4 fade-up">
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
    const options = [
      `<option value="${ALL_RUNS_ID}">Select all output (aggregate)</option>`,
      ...runs.map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(formatRunLabel(run))}</option>`),
    ];
    selector.innerHTML = options.join('');
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
      byId('ourMetricCards').innerHTML =
        '<div class="col-12"><div class="alert alert-warning">No data available for selected run.</div></div>';
      byId('theirMetricCards').innerHTML =
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
    byId('ourMetricCards').innerHTML =
      '<div class="col-12"><div class="alert alert-warning">Selected run details will appear here after the first successful run.</div></div>';
    byId('theirMetricCards').innerHTML =
      '<div class="col-12"><div class="alert alert-warning">Selected run details will appear here after the first successful run.</div></div>';
    byId('runSelector').innerHTML = '';
  }

  function boot() {
    if (!getSuccessfulRuns().length) {
      renderEmptyState();
      return;
    }
    state.selectedRunId = ALL_RUNS_ID;

    ensureSelectedRun();
    renderSelector();
    bindEvents();
    renderCurrent();
  }

  boot();
})();
