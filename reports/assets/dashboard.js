// Composio Research Agent Dashboard Explorer
document.addEventListener('DOMContentLoaded', () => {
  const dataScript = document.getElementById('analytics-data');
  if (!dataScript) return;

  let payload;
  try {
    payload = JSON.parse(dataScript.textContent);
  } catch (err) {
    console.error('Failed to parse analytics data:', err);
    return;
  }

  const explorerData = payload.explorer || [];
  const searchInput = document.getElementById('explorer-search');
  const catFilter = document.getElementById('explorer-cat-filter');
  const verdictFilter = document.getElementById('explorer-verdict-filter');
  const tableBody = document.getElementById('explorer-table-body');
  const countDisplay = document.getElementById('explorer-count');

  function renderTable(items) {
    if (!tableBody) return;
    tableBody.innerHTML = '';

    if (items.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 32px; color: #94a3b8;">No applications match the active filters.</td></tr>';
      if (countDisplay) countDisplay.textContent = 'Showing 0 applications';
      return;
    }

    if (countDisplay) countDisplay.textContent = `Showing ${items.length} of ${explorerData.length} applications`;

    items.forEach(app => {
      const tr = document.createElement('tr');
      const vClass = `badge-${app.verdict}`;
      const modeBadge = app.live_verified
        ? '<span class="badge badge-live">LIVE VERIFIED</span>'
        : '<span class="badge badge-partial">PARTIAL LIVE</span>';

      const compBadge = app.has_composio
        ? '<span style="color:#34d399; font-weight:600;">✓ Discovered</span>'
        : '<span style="color:#94a3b8;">Not Found</span>';

      const mcpBadge = app.mcp_session_created
        ? '<span style="color:#38bdf8; font-weight:600;">✓ Created</span>'
        : (app.has_composio ? '<span style="color:#fbbf24;">Auth Req.</span>' : '<span style="color:#64748b;">N/A</span>');

      tr.innerHTML = `
        <td><strong>${app.name}</strong><br><small style="color:#64748b;">${app.category_display}</small></td>
        <td><span class="badge ${vClass}">${app.verdict.replace('_', ' ')}</span></td>
        <td>${app.auth_methods.join(', ') || 'unknown'}</td>
        <td>${app.api_types.join(', ') || 'unknown'} (${app.api_breadth})</td>
        <td>${compBadge}</td>
        <td>${mcpBadge}</td>
        <td>${modeBadge}</td>
      `;
      tableBody.appendChild(tr);
    });
  }

  function applyFilters() {
    const term = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const cat = catFilter ? catFilter.value : 'all';
    const verdict = verdictFilter ? verdictFilter.value : 'all';

    const filtered = explorerData.filter(app => {
      const matchName = !term || app.name.toLowerCase().includes(term) || (app.description && app.description.toLowerCase().includes(term));
      const matchCat = cat === 'all' || app.category === cat;
      const matchVerdict = verdict === 'all' || app.verdict === verdict;
      return matchName && matchCat && matchVerdict;
    });

    renderTable(filtered);
  }

  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (catFilter) catFilter.addEventListener('change', applyFilters);
  if (verdictFilter) verdictFilter.addEventListener('change', applyFilters);

  // Initial render
  renderTable(explorerData);
});
