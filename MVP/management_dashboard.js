(function () {
  const data = window.MVP_DASHBOARD_DATA || { runs: [], summary: {} };

  const state = {
    selectedRunId: data.runs && data.runs.length ? data.runs[0].run_id : null,
    trendChart: null,
    entitySizeChart: null,
    matchKeyChart: null,
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

  function escapeHtml(text) {
    return String(text)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function getRun(runId) {
    return (data.runs || []).find((run) => run.run_id === runId) || null;
  }

  function renderSummaryCards() {
    const container = byId('summaryCards');
    const summary = data.summary || {};
    const cards = [
      { label: 'Total Runs', value: fmtInt(summary.runs_total) },
      { label: 'Total Input Records', value: fmtInt(summary.records_input_total) },
      { label: 'Total Matched Pairs', value: fmtInt(summary.matched_pairs_total) },
      { label: 'Avg Pair Precision', value: fmtPct(summary.avg_pair_precision_pct) },
      { label: 'Avg Pair Recall', value: fmtPct(summary.avg_pair_recall_pct) },
      { label: 'Latest Run', value: summary.latest_run_id || 'n/a' },
    ];

    container.innerHTML = cards
      .map(
        (card) => `
          <div class="col-sm-6 col-lg-4 col-xl-2">
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

  function renderGeneratedAt() {
    byId('generatedAt').textContent = `Generated at: ${data.generated_at || 'n/a'}`;
  }

  function renderSelector() {
    const selector = byId('runSelector');
    selector.innerHTML = (data.runs || [])
      .map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</option>`)
      .join('');
    if (state.selectedRunId) {
      selector.value = state.selectedRunId;
    }
    selector.addEventListener('change', (event) => {
      state.selectedRunId = event.target.value;
      renderSelectedRun();
    });
  }

  function renderRunsTable() {
    const body = byId('runsTableBody');
    body.innerHTML = (data.runs || [])
      .map(
        (run) => `
          <tr>
            <td><button class="btn btn-sm btn-outline-primary" data-run-id="${escapeHtml(run.run_id)}">${escapeHtml(
          run.run_id
        )}</button></td>
            <td>${fmtInt(run.records_input)}</td>
            <td>${fmtInt(run.matched_pairs)}</td>
            <td>${fmtPct(run.pair_precision_pct)}</td>
            <td>${fmtPct(run.pair_recall_pct)}</td>
            <td>${fmtInt(run.true_positive)}</td>
            <td>${fmtInt(run.false_positive)}</td>
            <td>${fmtInt(run.false_negative)}</td>
            <td>
              <a href="../${escapeHtml(run.management_summary_path)}" target="_blank" rel="noopener">management_summary.md</a><br>
              <a href="../${escapeHtml(run.ground_truth_summary_path)}" target="_blank" rel="noopener">ground_truth_match_quality.md</a>
            </td>
          </tr>
        `
      )
      .join('');

    body.querySelectorAll('button[data-run-id]').forEach((button) => {
      button.addEventListener('click', () => {
        state.selectedRunId = button.getAttribute('data-run-id');
        byId('runSelector').value = state.selectedRunId;
        renderSelectedRun();
      });
    });
  }

  function renderTrendChart() {
    const labels = (data.runs || []).slice().reverse().map((run) => run.run_id);
    const precision = (data.runs || []).slice().reverse().map((run) => run.pair_precision_pct ?? null);
    const recall = (data.runs || []).slice().reverse().map((run) => run.pair_recall_pct ?? null);

    const ctx = byId('trendChart');
    state.trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Pair Precision %',
            data: precision,
            borderColor: '#0284c7',
            backgroundColor: 'rgba(2,132,199,0.15)',
            tension: 0.2,
          },
          {
            label: 'Pair Recall %',
            data: recall,
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22,163,74,0.15)',
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0,
            max: 100,
          },
        },
      },
    });
  }

  function toDistribution(distributionObj) {
    const entries = Object.entries(distributionObj || {})
      .map(([key, value]) => [String(key), Number(value)])
      .filter(([, value]) => Number.isFinite(value))
      .sort((a, b) => Number(a[0]) - Number(b[0]));
    return {
      labels: entries.map(([key]) => key),
      values: entries.map(([, value]) => value),
    };
  }

  function renderSelectedRun() {
    const run = getRun(state.selectedRunId);
    if (!run) {
      return;
    }

    byId('runMeta').innerHTML = [
      `Run ID: <strong>${escapeHtml(run.run_id)}</strong>`,
      `Generated at: <strong>${escapeHtml(run.generated_at || 'n/a')}</strong>`,
      `Execution mode: <strong>${escapeHtml(run.mapping_info?.execution_mode || 'n/a')}</strong>`,
    ].join('<br>');

    const warningHtml = (run.runtime_warnings || []).length
      ? `<ul class="warning-list">${run.runtime_warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join('')}</ul>`
      : '<span class="text-muted">No runtime warnings.</span>';

    byId('runDetails').innerHTML = `
      <div class="row">
        <div class="col-lg-4 mb-3">
          <div class="small text-muted">Input / Export</div>
          <div class="h4">${fmtInt(run.records_input)} / ${fmtInt(run.records_exported)}</div>
          <div class="small text-muted">Input records vs exported rows from Senzing</div>
        </div>
        <div class="col-lg-4 mb-3">
          <div class="small text-muted">Ground Truth Quality</div>
          <div class="h4">P ${fmtPct(run.pair_precision_pct)} | R ${fmtPct(run.pair_recall_pct)}</div>
          <div class="small text-muted">TP ${fmtInt(run.true_positive)} | FP ${fmtInt(run.false_positive)} | FN ${fmtInt(
      run.false_negative
    )}</div>
        </div>
        <div class="col-lg-4 mb-3">
          <div class="small text-muted">Entities / Matches</div>
          <div class="h4">${fmtInt(run.resolved_entities)} entities</div>
          <div class="small text-muted">${fmtInt(run.matched_records)} matched records | ${fmtInt(
      run.matched_pairs
    )} matched pairs</div>
        </div>
      </div>
      <div class="row mt-2">
        <div class="col-lg-8 mb-3">
          <div class="small text-muted mb-1">Artifacts</div>
          <span class="badge badge-soft me-1">${fmtInt((run.artifacts || []).length)} files</span>
          <a class="ms-2" href="../${escapeHtml(run.management_summary_path)}" target="_blank" rel="noopener">Open management summary</a>
          <span class="mx-1">|</span>
          <a href="../${escapeHtml(run.ground_truth_summary_path)}" target="_blank" rel="noopener">Open ground truth summary</a>
        </div>
        <div class="col-lg-4 mb-3">
          <div class="small text-muted mb-1">Runtime warnings</div>
          ${warningHtml}
        </div>
      </div>
    `;

    const entityData = toDistribution(run.entity_size_distribution || {});
    const keyLabels = (run.top_match_keys || []).map((entry) => entry[0]);
    const keyValues = (run.top_match_keys || []).map((entry) => entry[1]);

    if (state.entitySizeChart) {
      state.entitySizeChart.destroy();
    }
    state.entitySizeChart = new Chart(byId('entitySizeChart'), {
      type: 'bar',
      data: {
        labels: entityData.labels,
        datasets: [
          {
            label: 'Number of entities',
            data: entityData.values,
            backgroundColor: '#2563eb',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
      },
    });

    if (state.matchKeyChart) {
      state.matchKeyChart.destroy();
    }
    state.matchKeyChart = new Chart(byId('matchKeyChart'), {
      type: 'bar',
      data: {
        labels: keyLabels,
        datasets: [
          {
            label: 'Pairs',
            data: keyValues,
            backgroundColor: '#0ea5e9',
          },
        ],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
      },
    });
  }

  function renderEmptyState() {
    byId('summaryCards').innerHTML = '<div class="col-12"><div class="alert alert-warning">No run found in ./output.</div></div>';
    byId('runsTableBody').innerHTML = '';
    byId('runSelector').innerHTML = '';
    byId('runDetails').innerHTML = '<span class="text-muted">Run details will appear here after the first execution.</span>';
  }

  function boot() {
    renderGeneratedAt();
    if (!data.runs || !data.runs.length) {
      renderEmptyState();
      return;
    }
    renderSummaryCards();
    renderSelector();
    renderRunsTable();
    renderTrendChart();
    renderSelectedRun();
  }

  boot();
})();
