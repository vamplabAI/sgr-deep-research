async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed: ' + res.status);
  return await res.json();
}

async function loadConfig() {
  try {
    const data = await fetchJSON('/api/config');
    const cfg = document.getElementById('cfgGateway');
    cfg.textContent = JSON.stringify(data.gateway_config, null, 2);
    // populate target select
    const sel = document.getElementById('targetSel');
    sel.innerHTML = '';
    const optGw = document.createElement('option');
    optGw.value = 'gateway'; optGw.textContent = 'gateway (airsroute_gateway/config.yaml)';
    sel.appendChild(optGw);
    (data.editable_configs || []).forEach((c) => {
      const o = document.createElement('option');
      o.value = c.name; o.textContent = `${c.name} (${c.path})`;
      sel.appendChild(o);
    });
  } catch (e) {}
}

async function loadTelemetry() {
  try {
    const data = await fetchJSON('/api/telemetry');
    const tbody = document.getElementById('telemetry');
    tbody.innerHTML = '';
    (data.items || []).forEach((it) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${it.ts || ''}</td>
        <td>${it.status || ''}</td>
        <td>${it.model || ''}</td>
        <td>${(it.messages_count ?? '').toString()}</td>
        <td title="${(it.summary||'').replace(/"/g, '&quot;')}">${(it.summary||'')}</td>
        <td>${(it.latency_ms ?? '').toString()}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {}
}

async function applyConfig() {
  const updatesRaw = document.getElementById('updates').value;
  const key = document.getElementById('adminkey').value.trim();
  const target = document.getElementById('targetSel').value;
  let updates;
  try { updates = JSON.parse(updatesRaw); } catch (_) { alert('Invalid JSON'); return; }
  const res = await fetch('/api/config', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { 'Authorization': 'Bearer ' + key } : {})
    },
    body: JSON.stringify({ target, updates })
  });
  if (!res.ok) { alert('Failed: ' + res.status); return; }
  await loadConfig();
  alert('Applied');
}

document.getElementById('saveCfg').addEventListener('click', applyConfig);

async function loadSelected() {
  const target = document.getElementById('targetSel').value;
  const data = await fetchJSON('/api/config?target=' + encodeURIComponent(target));
  const pre = document.getElementById('cfgSelected');
  pre.textContent = JSON.stringify(data.config, null, 2);
}
document.getElementById('loadTarget').addEventListener('click', loadSelected);

loadConfig();
loadTelemetry(); // initial load as fallback
setInterval(loadTelemetry, 15000); // low-frequency fallback

// Live SSE updates
try {
  const es = new EventSource('/api/telemetry/stream');
  es.addEventListener('telemetry', (ev) => {
    try {
      const it = JSON.parse(ev.data);
      const tbody = document.getElementById('telemetry');
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${it.ts || ''}</td>
        <td>${it.status || ''}</td>
        <td>${it.model || ''}</td>
        <td>${(it.messages_count ?? '').toString()}</td>
        <td title="${(it.summary||'').replace(/"/g, '&quot;')}">${(it.summary||'')}</td>
        <td>${(it.latency_ms ?? '').toString()}</td>
      `;
      tbody.prepend(tr);
      // trim to ~200 rows
      while (tbody.children.length > 200) tbody.removeChild(tbody.lastChild);
    } catch (e) {}
  });
  es.addEventListener('config', async () => {
    await loadConfig();
    await loadSelected();
  });
} catch (e) {}
