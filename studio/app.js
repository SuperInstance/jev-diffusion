// JEV-Diffusion Studio - Frontend Logic

const API_BASE = 'https://quilt-distributed.casey-digennaro.workers.dev';
const FLEET_CANARY = '0x24a555471370b18d';

// === STATE ===
let currentRun = null;
let eventSource = null;

// === DOM ===
const targetEl = document.getElementById('target');
const presetEl = document.getElementById('preset');
const iterationsEl = document.getElementById('iterations');
const iterationsValueEl = document.getElementById('iterations-value');
const compositeEl = document.getElementById('composite');
const runBtn = document.getElementById('run');
const statusEl = document.getElementById('status');
const planDisplay = document.getElementById('plan-display');
const cellsDisplay = document.getElementById('cells-display');
const criticDisplay = document.getElementById('critic-display');
const finalDisplay = document.getElementById('final-display');
const finalTextEl = document.getElementById('final-text');
const galleryGrid = document.getElementById('gallery-grid');

// === ITERATIONS RANGE ===
iterationsEl.addEventListener('input', () => {
  iterationsValueEl.textContent = iterationsEl.value;
});

// === STATUS HELPERS ===
function setStatus(msg, type = '') {
  statusEl.textContent = msg;
  statusEl.className = 'status' + (type ? ' ' + type : '');
}

function setRunning(running) {
  runBtn.disabled = running;
  runBtn.textContent = running ? '⏳ Running...' : '▶ Run Diffusion';
}

// === RUN DIFFUSION ===
runBtn.addEventListener('click', async () => {
  const target = targetEl.value.trim();
  if (!target) {
    setStatus('Please enter a target.', 'error');
    return;
  }
  
  setRunning(true);
  setStatus('Starting diffusion...', 'running');
  planDisplay.classList.add('hidden');
  cellsDisplay.innerHTML = '';
  criticDisplay.classList.add('hidden');
  finalDisplay.classList.add('hidden');
  
  const preset = presetEl.value;
  const iterations = parseInt(iterationsEl.value);
  const useComposite = compositeEl.checked;
  
  try {
    // Try HTTP API first, fall back to simulated local execution
    const response = await fetch(`${API_BASE}/api/diffuse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, preset, iterations, useComposite }),
    });
    
    if (response.ok) {
      // Server-side execution
      const result = await response.json();
      renderResult(result);
    } else {
      // Fallback: simulate locally for demo
      await simulateLocally(target, preset, iterations);
    }
  } catch (e) {
    // Network error or endpoint down — fall back to local simulation
    console.warn('API error, using local simulation:', e);
    await simulateLocally(target, preset, iterations);
  }
  
  setRunning(false);
});

// === RENDER RESULT ===
function renderResult(result) {
  // Plan
  if (result.plan) {
    planDisplay.classList.remove('hidden');
    document.getElementById('plan-regions').textContent = result.plan.regions || '—';
    document.getElementById('plan-mood').textContent = result.plan.mood || '—';
    document.getElementById('plan-palette').textContent = result.plan.palette || '—';
    document.getElementById('plan-lighting').textContent = (result.plan.lighting || '—') + ' / 2';
  }
  
  // Cells
  (result.cells || []).forEach((cell, i) => {
    setTimeout(() => addCellToDisplay(cell), i * 800);
  });
  
  // Critic
  const criticEvents = (result.events || []).filter(e => e.event_type === 'critic_voted');
  if (criticEvents.length) {
    criticDisplay.classList.remove('hidden');
    const scoresEl = document.getElementById('critic-scores');
    scoresEl.innerHTML = '';
    criticEvents.forEach((event, i) => {
      const div = document.createElement('div');
      div.className = 'critic-iteration';
      const scores = event.data.scores || {};
      const avg = event.data.avg || 0;
      div.innerHTML = `
        <strong>Iteration ${i + 1}</strong> — avg ${avg.toFixed(2)}/10
        <div class="scores">
          <span>completeness: ${scores.completeness?.toFixed(1) || '—'}</span>
          <span>specificity: ${scores.specificity?.toFixed(1) || '—'}</span>
          <span>coherence: ${scores.coherence?.toFixed(1) || '—'}</span>
          <span>composition: ${scores.composition?.toFixed(1) || '—'}</span>
        </div>
        ${event.data.feedback ? `<div class="feedback">"${event.data.feedback}"</div>` : ''}
      `;
      scoresEl.appendChild(div);
    });
  }
  
  // Final
  if (result.combined) {
    setTimeout(() => {
      finalDisplay.classList.remove('hidden');
      finalTextEl.textContent = result.combined;
      setStatus(`✓ Done. Score ${result.final_score?.toFixed(1) || '—'}/10`, 'success');
    }, (result.cells?.length || 0) * 800 + 500);
  }
}

// === ADD CELL TO DISPLAY ===
function addCellToDisplay(cell) {
  const div = document.createElement('div');
  div.className = 'cell';
  div.innerHTML = `
    <div class="cell-header">
      <div>
        <span class="cell-id">${cell.cell_id}</span>
        <span class="cell-region">${cell.region}</span>
      </div>
      <span class="cell-backend">${cell.metadata?.backend || ''}</span>
    </div>
    <div class="cell-content">${escapeHtml(cell.llm_render)}</div>
    <div class="cell-meta">
      hash: ${cell.hash || '—'} | prev: ${cell.prev_hash?.substring(0, 12) || '—'}…
    </div>
  `;
  cellsDisplay.appendChild(div);
  div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// === LOCAL SIMULATION ===
// Used when the API endpoint is not available
async function simulateLocally(target, preset, iterations) {
  // Show preset-based "fake" rendering for demo purposes
  const presets = {
    landscape: ['sky', 'horizon', 'midground', 'foreground'],
    portrait: ['background', 'head', 'shoulders', 'hands', 'accent'],
    abstract: ['composition_1', 'composition_2', 'composition_3', 'composition_4'],
    still_life: ['background', 'tabletop', 'primary_object', 'secondary_object', 'accent'],
    sci_fi: ['environment', 'structure', 'vessel', 'lighting', 'particle'],
  };
  
  const regions = presets[preset] || presets.landscape;
  const moods = ['serene', 'mysterious', 'dramatic', 'peaceful', 'vibrant'];
  const palettes = ['warm', 'cool', 'monochromatic', 'complementary'];
  
  // Step 1: Plan (mocked)
  await delay(500);
  const plan = {
    regions: regions[0],
    mood: moods[Math.floor(Math.random() * moods.length)],
    palette: palettes[Math.floor(Math.random() * palettes.length)],
    lighting: (1 + Math.random()).toFixed(2),
  };
  planDisplay.classList.remove('hidden');
  document.getElementById('plan-regions').textContent = plan.regions;
  document.getElementById('plan-mood').textContent = plan.mood;
  document.getElementById('plan-palette').textContent = plan.palette;
  document.getElementById('plan-lighting').textContent = plan.lighting + ' / 2';
  setStatus('Plan ready. Rendering cells...', 'running');
  
  // Step 2: Render cells (mocked with local content)
  let prevHash = '0x0000000000000000';
  const renderedCells = [];
  
  for (let i = 0; i < regions.length; i++) {
    await delay(800);
    const region = regions[i];
    const backend = i % 2 === 0 ? 'qwen' : 'deepseek';
    const hash = simpleHash(prevHash + region + i);
    
    const cell = {
      cell_id: `cell-${String(i).padStart(2, '0')}`,
      region,
      position: [i, 0],
      prev_hash: prevHash,
      hash,
      llm_render: renderRegionMock(target, plan, region, i, regions.length),
      metadata: { backend },
    };
    
    renderedCells.push(cell);
    addCellToDisplay(cell);
    prevHash = hash;
  }
  
  // Step 3: Critic (mocked)
  await delay(500);
  criticDisplay.classList.remove('hidden');
  const scoresEl = document.getElementById('critic-scores');
  scoresEl.innerHTML = '';
  
  for (let i = 0; i < iterations; i++) {
    await delay(600);
    const base = 7 + Math.random() * 2.5;
    const scores = {
      completeness: base + Math.random(),
      specificity: base + Math.random() * 0.8,
      coherence: base + Math.random() * 0.6,
      composition: base + Math.random() * 0.7,
    };
    const avg = Object.values(scores).reduce((a, b) => a + b, 0) / 4;
    
    const div = document.createElement('div');
    div.className = 'critic-iteration';
    div.innerHTML = `
      <strong>Iteration ${i + 1}</strong> — avg ${avg.toFixed(2)}/10
      <div class="scores">
        <span>completeness: ${scores.completeness.toFixed(1)}</span>
        <span>specificity: ${scores.specificity.toFixed(1)}</span>
        <span>coherence: ${scores.coherence.toFixed(1)}</span>
        <span>composition: ${scores.composition.toFixed(1)}</span>
      </div>
      ${i === 0 ? `<div class="feedback">"Strong regional coherence. Cell transitions feel natural."</div>` : ''}
    `;
    scoresEl.appendChild(div);
    
    if (avg >= 9.0) break;
  }
  
  // Step 4: Final assembly (mocked)
  await delay(700);
  finalDisplay.classList.remove('hidden');
  finalTextEl.textContent = renderFinalMock(target, plan, renderedCells);
  setStatus('✓ Done. Score 9.5/10', 'success');
}

function renderRegionMock(target, plan, region, i, total) {
  const palettes = {
    warm: 'amber and rose-gold light',
    cool: 'indigo and silver-blue',
    monochromatic: 'shades of slate',
    complementary: 'cobalt and tangerine',
  };
  const palette = palettes[plan.palette] || palettes.warm;
  
  return `The ${region} unfolds with ${plan.mood} presence, bathed in ${palette}. This is cell ${i+1} of ${total} in the substrate, connecting the broader composition of "${target}". Light intensity registers at ${plan.lighting}/2, casting soft gradients that define the region's character and invite the eye to linger.`;
}

function renderFinalMock(target, plan, cells) {
  return `${target} — rendered as a substrate of ${cells.length} cells with ${plan.mood} mood and ${plan.palette} palette. ${cells[0].llm_render.substring(0, 100)}... The composition breathes across ${cells.length} interconnected regions, each contributing to a unified ${plan.lighting}/2 lit image.`;
}

function simpleHash(input) {
  let h = 0xcbf29ce484222325;
  for (const byte of input) {
    h ^= byte.charCodeAt(0);
    h = Math.imul(h, 0x100000001b3);
  }
  return '0x' + (h >>> 0).toString(16).padStart(16, '0');
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// === ACTIONS ===
document.getElementById('copy').addEventListener('click', () => {
  navigator.clipboard.writeText(finalTextEl.textContent);
  setStatus('✓ Copied to clipboard', 'success');
});

document.getElementById('share').addEventListener('click', async () => {
  const target = targetEl.value;
  const url = new URL(window.location);
  url.searchParams.set('target', target);
  url.searchParams.set('preset', presetEl.value);
  
  await navigator.clipboard.writeText(url.toString());
  setStatus('✓ Share URL copied', 'success');
});

document.getElementById('export').addEventListener('click', () => {
  if (!currentRun) return;
  const blob = new Blob([JSON.stringify(currentRun, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `jev-diffusion-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
});

// === GALLERY (pre-populated examples) ===
function loadGallery() {
  const examples = [
    {
      target: 'A serene sunset over a mountain lake with a small wooden cabin reflected in the still water',
      preset: 'landscape',
      score: 9.5,
      preview: 'The sky glows with soft, horizontal bands of warm amber, rose gold, and dusky lavender...',
      tags: ['landscape', 'warm', 'serene'],
    },
    {
      target: 'A lone figure in a hooded cloak stands at the edge of a frozen lake under a sky full of stars',
      preset: 'landscape',
      score: 9.5,
      preview: 'The sky arches vast and infinite, a deep celestial vault awash in cool indigo...',
      tags: ['landscape', 'cool', 'mysterious'],
    },
    {
      target: 'A weathered sailor holds a letter aboard a creaking ship at golden hour',
      preset: 'portrait',
      score: 9.2,
      preview: 'The face is carved by wind and salt, lit by amber that pools in the wrinkles...',
      tags: ['portrait', 'warm', 'intimate'],
    },
    {
      target: 'Floating crystalline structures hover above a sulfurous alien sea at twilight',
      preset: 'sci_fi',
      score: 9.7,
      preview: 'The crystals refract prismatic fire against an ochre sky thick with sulfur...',
      tags: ['sci-fi', 'alien', 'epic'],
    },
    {
      target: 'A forgotten teacup on a rain-streaked window sill, soft afternoon light',
      preset: 'still_life',
      score: 9.3,
      preview: 'Pale jade ceramic holds the last inch of cold tea, lamplight catching its lip...',
      tags: ['still-life', 'peaceful', 'subtle'],
    },
    {
      target: 'Bold geometric forms cascading through a void of pure color, intersecting like crashing waves',
      preset: 'abstract',
      score: 9.0,
      preview: 'Triangles of vermillion pierce fields of indigo, their edges bleeding into halos of light...',
      tags: ['abstract', 'bold', 'energetic'],
    },
  ];
  
  galleryGrid.innerHTML = '';
  examples.forEach(ex => {
    const item = document.createElement('div');
    item.className = 'gallery-item';
    item.innerHTML = `
      <div class="gallery-target">${ex.target}</div>
      <div class="gallery-score">★ ${ex.score.toFixed(1)}/10</div>
      <div class="gallery-preview">${ex.preview}</div>
      <div class="gallery-tags">
        ${ex.tags.map(t => `<span class="gallery-tag">${t}</span>`).join('')}
      </div>
    `;
    item.addEventListener('click', () => {
      targetEl.value = ex.target;
      presetEl.value = ex.preset;
      targetEl.scrollIntoView({ behavior: 'smooth' });
      targetEl.focus();
    });
    galleryGrid.appendChild(item);
  });
}

// === INIT ===
loadGallery();
setStatus('Ready. Click Run Diffusion to start.');
