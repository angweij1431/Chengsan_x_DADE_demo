/**
 * Booth kiosk controller.
 *
 * Three stations share one screen. Each declares which upload slots it needs,
 * which preset list to show, and which endpoint to post to, so the flow
 * (upload -> preset -> generate -> QR) is written once.
 */

const STATIONS = {
  dance: {
    title: 'Make me dance',
    sub: 'Upload a photo, pick a style. Got your own dance clip? Add it on the right.',
    endpoint: '/api/dance',
    presetKey: 'dance_templates',
    presetField: 'template_id',
    presetLabel: 'Choose a dance',
    primaryLabel: 'Your photo',
    secondary: {
      field: 'dance_video',
      accept: 'video/*',
      label: 'Your own dance clip',
      hint: 'Optional · limited goes',
      required: false
    },
    showRequest: false,
    working: 'Choreographing your dance…',
    workingSub: 'Video takes longer than photos — up to a minute or two.'
  },
  edit: {
    title: 'Edit my photo',
    sub: 'Upload your photo and a reference, then tell us what to change.',
    endpoint: '/api/edit',
    presetKey: 'edit_presets',
    presetField: 'preset_id',
    presetLabel: 'What should we do?',
    primaryLabel: 'Your photo',
    secondary: {
      field: 'reference',
      accept: 'image/*',
      label: 'Reference photo',
      hint: 'The look you want',
      required: true
    },
    showRequest: true,
    working: 'Editing your photo…',
    workingSub: 'This usually takes 10–30 seconds.'
  },
  scene: {
    title: 'Put me somewhere',
    sub: 'Upload a photo of a place, and a photo of yourself.',
    endpoint: '/api/scene',
    presetKey: 'scene_presets',
    presetField: 'preset_id',
    presetLabel: 'How should it look?',
    primaryLabel: 'Your photo',
    secondary: {
      field: 'environment',
      accept: 'image/*',
      label: 'The place',
      hint: 'Where you want to be',
      required: true
    },
    showRequest: true,
    working: 'Building your scene…',
    workingSub: 'This usually takes 10–30 seconds.'
  }
};

const ACTION_FOR_QUOTA = {
  edit: 'edit_image',
  scene: 'scene_image',
  dance: 'dance_template'
};

const el = (id) => document.getElementById(id);

const state = {
  station: null,
  config: null,
  preset: null,
  primaryFile: null,
  secondaryFile: null
};

// --------------------------------------------------------------------------
// navigation
// --------------------------------------------------------------------------

function show(view) {
  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  el(`view-${view}`).classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('[data-goto]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.goto;
    if (target === 'station') {
      resetStation();
      show('station');
    } else {
      show(target);
    }
  });
});

el('home-link').addEventListener('click', () => show('home'));

document.querySelectorAll('.station-card').forEach((card) => {
  card.addEventListener('click', () => openStation(card.dataset.station));
});

// --------------------------------------------------------------------------
// station setup
// --------------------------------------------------------------------------

function openStation(key) {
  state.station = key;
  const station = STATIONS[key];

  el('station-title').textContent = station.title;
  el('station-sub').textContent = station.sub;
  el('slot-primary-label').textContent = station.primaryLabel;
  el('slot-secondary-label').textContent = station.secondary.label;
  el('slot-secondary-hint').textContent = station.secondary.hint;
  el('slot-secondary').querySelector('input').accept = station.secondary.accept;

  el('preset-label').textContent = station.presetLabel;
  el('request-block').hidden = !station.showRequest;

  renderPresets(station);
  resetStation();
  show('station');
}

function renderPresets(station) {
  const row = el('preset-row');
  row.innerHTML = '';
  const presets = (state.config && state.config[station.presetKey]) || [];

  presets.forEach((preset, index) => {
    const chip = document.createElement('button');
    chip.className = 'preset-chip' + (index === 0 ? ' selected' : '');
    chip.innerHTML = `<span>${preset.emoji || '✨'}</span><span>${preset.name}</span>`;
    chip.addEventListener('click', () => {
      row.querySelectorAll('.preset-chip').forEach((c) => c.classList.remove('selected'));
      chip.classList.add('selected');
      state.preset = preset.id;
    });
    row.appendChild(chip);
  });

  state.preset = presets.length ? presets[0].id : null;
  el('preset-block').hidden = presets.length === 0;
}

function resetStation() {
  state.primaryFile = null;
  state.secondaryFile = null;
  el('request-input').value = '';
  el('error-box').hidden = true;

  ['slot-primary', 'slot-secondary'].forEach((id) => {
    const slot = el(id);
    slot.classList.remove('filled');
    slot.querySelector('input').value = '';
    slot.querySelectorAll('.slot-preview').forEach((p) => {
      p.classList.remove('shown');
      p.removeAttribute('src');
    });
  });

  updateQuotaNote();
  updateGenerateButton();
}

// --------------------------------------------------------------------------
// uploads
// --------------------------------------------------------------------------

function wireSlot(slotId, onPick) {
  const slot = el(slotId);
  const input = slot.querySelector('input');

  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    const isVideo = file.type.startsWith('video/');
    const img = slot.querySelector('img.slot-preview');
    const video = slot.querySelector('video.slot-preview');

    if (isVideo && video) {
      video.src = url;
      video.classList.add('shown');
      video.play().catch(() => {});
      if (img) img.classList.remove('shown');
    } else if (img) {
      img.src = url;
      img.classList.add('shown');
      if (video) video.classList.remove('shown');
    }

    slot.classList.add('filled');
    slot.querySelector('.slot-hint').textContent = '✓ ' + file.name.slice(0, 28);
    onPick(file);
    updateGenerateButton();
    updateQuotaNote();
  });
}

wireSlot('slot-primary', (file) => { state.primaryFile = file; });
wireSlot('slot-secondary', (file) => { state.secondaryFile = file; });

function updateGenerateButton() {
  const station = STATIONS[state.station];
  if (!station) return;
  const ready = state.primaryFile && (!station.secondary.required || state.secondaryFile);
  el('generate-btn').disabled = !ready;
}

function updateQuotaNote() {
  const station = STATIONS[state.station];
  if (!station || !state.config) return;

  let action = ACTION_FOR_QUOTA[state.station];
  if (state.station === 'dance' && state.secondaryFile) action = 'dance_custom';

  const quota = state.config.limits[action];
  if (!quota) { el('quota-note').textContent = ''; return; }

  const label = action === 'dance_custom' ? 'custom dance clips' : 'goes';
  el('quota-note').textContent =
    `${quota.session_remaining} of ${quota.session_limit} ${label} left for you today.`;
}

// --------------------------------------------------------------------------
// generate
// --------------------------------------------------------------------------

el('generate-btn').addEventListener('click', async () => {
  const station = STATIONS[state.station];
  el('error-box').hidden = true;

  const form = new FormData();
  form.append('photo', state.primaryFile);
  if (state.secondaryFile) form.append(station.secondary.field, state.secondaryFile);
  if (state.preset) form.append(station.presetField, state.preset);
  if (station.showRequest) form.append('request', el('request-input').value);

  el('working-title').textContent = station.working;
  el('working-sub').textContent = station.workingSub;
  show('working');

  try {
    const response = await fetch(station.endpoint, { method: 'POST', body: form });
    const data = await response.json();

    if (!response.ok || data.status !== 'success') {
      throw new Error(data.message || `Request failed (${response.status}).`);
    }

    await refreshConfig();
    showResult(data);
  } catch (err) {
    el('error-box').textContent = err.message;
    el('error-box').hidden = false;
    show('station');
  }
});

function showResult(data) {
  const media = el('result-media');
  media.innerHTML = '';

  if (data.is_video) {
    const video = document.createElement('video');
    video.src = data.view_url;
    video.controls = true;
    video.autoplay = true;
    video.loop = true;
    video.playsInline = true;
    media.appendChild(video);
  } else {
    const img = document.createElement('img');
    img.src = data.view_url;
    img.alt = 'Your generated result';
    media.appendChild(img);
  }

  el('qr-img').src = data.qr_code_base64;
  el('download-btn').href = data.download_url;
  el('download-btn').setAttribute('download', data.filename);
  el('result-note').textContent = data.note || 'Scan the QR code to get it on your phone.';

  show('result');
}

// --------------------------------------------------------------------------
// boot
// --------------------------------------------------------------------------

async function refreshConfig() {
  const response = await fetch('/api/config');
  state.config = await response.json();
  return state.config;
}

async function boot() {
  const chip = el('provider-chip');
  try {
    const config = await refreshConfig();
    const provider = config.dance_provider;
    chip.textContent = `dance: ${provider}`;
    if (provider === 'mock') {
      chip.classList.add('warn');
      chip.title = 'Dance videos are demo renders. Set DANCE_PROVIDER in .env for real ones.';
    }
  } catch (err) {
    chip.textContent = 'server offline';
    chip.classList.add('bad');
  }
}

boot();
