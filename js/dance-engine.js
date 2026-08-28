/**
 * AI Dance Engine & Audio Synthesizer
 */
class DanceEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.isPlaying = false;
    this.animId = null;
    this.startTime = 0;
    this.currentTime = 0;
    this.duration = 16;
    this.danceStyle = 'cyber_hiphop';
    this.userMedia = null;
    this.audioCtx = null;
    this.audioPlaying = false;
    this.isMuted = false;
    this.volume = 0.8;
    this.playbackRate = 1.0;
    this.particles = [];
    this.onTimeUpdate = null;

    this.styles = {
      cyber_hiphop: {
        id: 'cyber_hiphop',
        name: 'Cyber Hip-Hop',
        bpm: 128,
        vibe: '⚡ Electric / Popping',
        primaryColor: '#00f0ff',
        secondaryColor: '#7928ca',
        accentColor: '#38ef7d',
        synthScale: [130.81, 155.56, 174.61, 196.00, 233.08, 261.63],
        description: 'High-energy robotic popping, arm wave dynamics, and futuristic cyber glow trails.'
      },
      salsa_fiesta: {
        id: 'salsa_fiesta',
        name: 'Salsa Fiesta',
        bpm: 105,
        vibe: '🔥 Latin / Fluid Groove',
        primaryColor: '#ff007f',
        secondaryColor: '#ffaa00',
        accentColor: '#ff3366',
        synthScale: [146.83, 164.81, 196.00, 220.00, 261.63, 293.66],
        description: 'Rhythmic hip sway, syncopated cross-body footwork, and fluid passionate spins.'
      },
      kpop_idol: {
        id: 'kpop_idol',
        name: 'K-Pop Idol',
        bpm: 132,
        vibe: '✨ Pop / Point Choreo',
        primaryColor: '#e040fb',
        secondaryColor: '#00e5ff',
        accentColor: '#ff4081',
        synthScale: [164.81, 196.00, 220.00, 246.94, 293.66, 329.63],
        description: 'Ultra-crisp synchronized point choreography, heart poses, and radiant idol sparkles.'
      },
      breakdance_freeze: {
        id: 'breakdance_freeze',
        name: 'Breakdance Freeze',
        bpm: 115,
        vibe: '💥 Street / Power Moves',
        primaryColor: '#ff9100',
        secondaryColor: '#00e676',
        accentColor: '#ffd600',
        synthScale: [110.00, 130.81, 146.83, 164.81, 196.00, 220.00],
        description: 'Dynamic 6-step footwork, floor sweeps, windmill rotations, and explosive freeze locks.'
      }
    };

    this.initParticles();
  }

  initParticles() {
    this.particles = [];
    for (let i = 0; i < 60; i++) {
      this.particles.push({
        x: Math.random() * 800,
        y: Math.random() * 450,
        size: Math.random() * 3 + 1,
        vx: (Math.random() - 0.5) * 1.5,
        vy: (Math.random() - 0.5) * 1.5,
        life: Math.random() * 100,
        maxLife: 100
      });
    }
  }

  setDanceStyle(styleKey) {
    if (this.styles[styleKey]) {
      this.danceStyle = styleKey;
    }
  }

  setUserMedia(mediaObj) {
    this.userMedia = mediaObj;
  }

  initAudio() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  play() {
    this.initAudio();
    this.isPlaying = true;
    this.startTime = performance.now() - (this.currentTime * 1000) / this.playbackRate;
    this.startAudioLoop();
    this.renderLoop();
  }

  pause() {
    this.isPlaying = false;
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
    this.stopAudioLoop();
  }

  seek(timeInSeconds) {
    this.currentTime = Math.max(0, Math.min(timeInSeconds, this.duration));
    if (this.isPlaying) {
      this.startTime = performance.now() - (this.currentTime * 1000) / this.playbackRate;
    }
    this.renderFrame(this.currentTime);
    if (this.onTimeUpdate) this.onTimeUpdate(this.currentTime, this.duration);
  }

  setVolume(vol) {
    this.volume = Math.max(0, Math.min(1, vol));
  }

  setMuted(muted) {
    this.isMuted = muted;
  }

  setPlaybackRate(rate) {
    this.playbackRate = rate;
    if (this.isPlaying) {
      this.startTime = performance.now() - (this.currentTime * 1000) / this.playbackRate;
    }
  }

  renderLoop() {
    if (!this.isPlaying) return;

    const elapsed = ((performance.now() - this.startTime) / 1000) * this.playbackRate;
    this.currentTime = elapsed % this.duration;

    this.renderFrame(this.currentTime);

    if (this.onTimeUpdate) {
      this.onTimeUpdate(this.currentTime, this.duration);
    }

    this.animId = requestAnimationFrame(() => this.renderLoop());
  }

  renderFrame(t) {
    const canvas = this.canvas;
    const ctx = this.ctx;
    const w = canvas.width;
    const h = canvas.height;
    const style = this.styles[this.danceStyle];
    const bpm = style.bpm;
    const beatInterval = 60 / bpm;
    const currentBeat = t / beatInterval;
    const beatPhase = currentBeat % 1;

    // Background
    const bgGrad = ctx.createRadialGradient(w / 2, h / 2, 50, w / 2, h / 2, w * 0.7);
    bgGrad.addColorStop(0, '#13182c');
    bgGrad.addColorStop(0.6, '#090b14');
    bgGrad.addColorStop(1, '#040509');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    this.drawPerspectiveGrid(ctx, w, h, t, style);
    this.drawEqualizer(ctx, w, h, t, beatPhase, style);
    this.drawStageLighting(ctx, w, h, t, beatPhase, style);
    this.drawParticles(ctx, w, h, style);
    this.drawDancer(ctx, w, h, t, currentBeat, style);
    this.drawHudOverlay(ctx, w, h, t, style);
  }

  drawPerspectiveGrid(ctx, w, h, t, style) {
    const horizon = h * 0.65;
    ctx.save();
    ctx.strokeStyle = style.primaryColor;
    ctx.globalAlpha = 0.25;
    ctx.lineWidth = 1;

    const offset = (t * 60) % 30;
    for (let y = horizon; y < h; y += (y - horizon + 10) * 0.35) {
      const lineY = y + (offset * ((y - horizon) / (h - horizon)));
      if (lineY <= h) {
        ctx.beginPath();
        ctx.moveTo(0, lineY);
        ctx.lineTo(w, lineY);
        ctx.stroke();
      }
    }

    const centerX = w / 2;
    for (let x = -w * 0.5; x <= w * 1.5; x += 60) {
      ctx.beginPath();
      ctx.moveTo(centerX, horizon);
      ctx.lineTo(x, h);
      ctx.stroke();
    }

    ctx.globalAlpha = 0.6;
    ctx.strokeStyle = style.accentColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, horizon);
    ctx.lineTo(w, horizon);
    ctx.stroke();

    ctx.restore();
  }

  drawEqualizer(ctx, w, h, t, beatPhase, style) {
    ctx.save();
    const barCount = 14;
    const barW = 6;
    const gap = 4;
    const maxH = 120;

    for (let i = 0; i < barCount; i++) {
      const freq = Math.sin(t * 8 + i * 0.7) * 0.5 + 0.5;
      const beatBoost = (1 - beatPhase) * 0.4;
      const barH = Math.max(8, (freq + beatBoost) * maxH * (1 - i / barCount * 0.3));
      
      const grad = ctx.createLinearGradient(0, h * 0.7, 0, h * 0.7 - barH);
      grad.addColorStop(0, style.primaryColor);
      grad.addColorStop(1, style.secondaryColor);

      ctx.fillStyle = grad;
      ctx.globalAlpha = 0.7;
      ctx.fillRect(20 + i * (barW + gap), h * 0.68 - barH, barW, barH);
      ctx.fillRect(w - 20 - (barCount - i) * (barW + gap), h * 0.68 - barH, barW, barH);
    }
    ctx.restore();
  }

  drawStageLighting(ctx, w, h, t, beatPhase, style) {
    ctx.save();
    const beatImpact = Math.pow(1 - beatPhase, 3);

    const gradL = ctx.createRadialGradient(w * 0.2, 0, 10, w * 0.35, h * 0.7, 300);
    gradL.addColorStop(0, `${style.primaryColor}66`);
    gradL.addColorStop(1, 'transparent');
    ctx.fillStyle = gradL;
    ctx.beginPath();
    ctx.moveTo(w * 0.2, 0);
    ctx.lineTo(w * 0.05, h * 0.8);
    ctx.lineTo(w * 0.45, h * 0.8);
    ctx.closePath();
    ctx.fill();

    const gradR = ctx.createRadialGradient(w * 0.8, 0, 10, w * 0.65, h * 0.7, 300);
    gradR.addColorStop(0, `${style.secondaryColor}66`);
    gradR.addColorStop(1, 'transparent');
    ctx.fillStyle = gradR;
    ctx.beginPath();
    ctx.moveTo(w * 0.8, 0);
    ctx.lineTo(w * 0.55, h * 0.8);
    ctx.lineTo(w * 0.95, h * 0.8);
    ctx.closePath();
    ctx.fill();

    const centerGlow = ctx.createRadialGradient(w / 2, h * 0.68, 10, w / 2, h * 0.68, 180 + beatImpact * 60);
    centerGlow.addColorStop(0, `${style.accentColor}${Math.floor((0.3 + beatImpact * 0.4) * 255).toString(16).padStart(2, '0')}`);
    centerGlow.addColorStop(1, 'transparent');
    ctx.fillStyle = centerGlow;
    ctx.beginPath();
    ctx.ellipse(w / 2, h * 0.68, 180 + beatImpact * 40, 50 + beatImpact * 15, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  drawParticles(ctx, w, h, style) {
    ctx.save();
    for (const p of this.particles) {
      p.x += p.vx;
      p.y += p.vy;
      p.life += 0.5;
      if (p.life > p.maxLife || p.x < 0 || p.x > w || p.y < 0 || p.y > h) {
        p.x = Math.random() * w;
        p.y = Math.random() * h * 0.7;
        p.life = 0;
      }
      const alpha = (1 - p.life / p.maxLife) * 0.6;
      ctx.fillStyle = style.primaryColor;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  drawDancer(ctx, w, h, t, beat, style) {
    ctx.save();
    const cx = w / 2;
    const groundY = h * 0.68;
    const dancerH = 260;
    const baseHeadY = groundY - dancerH;

    let bodyX = cx;
    let bodyY = groundY - 140;
    let headX = cx;
    let headY = baseHeadY + 25;
    let lHandX = cx - 50, lHandY = bodyY - 10;
    let rHandX = cx + 50, rHandY = bodyY - 10;
    let lFootX = cx - 30, lFootY = groundY;
    let rFootX = cx + 30, rFootY = groundY;

    const b = beat;
    const sinB = Math.sin(b * Math.PI);

    if (this.danceStyle === 'cyber_hiphop') {
      const pop = Math.pow(Math.abs(Math.sin(b * Math.PI)), 8) * 12;
      bodyX = cx + Math.sin(b * 0.5) * 45;
      bodyY = groundY - 140 + pop + Math.abs(sinB) * 10;
      headX = bodyX + Math.sin(b) * 8;
      headY = bodyY - 80;

      lHandX = bodyX - 70 + Math.sin(b * 2) * 30;
      lHandY = bodyY - 40 - Math.cos(b * 2) * 50;
      rHandX = bodyX + 70 + Math.cos(b * 2) * 30;
      rHandY = bodyY - 40 - Math.sin(b * 2) * 50;
      
      lFootX = bodyX - 40 + Math.sin(b) * 20;
      rFootX = bodyX + 40 - Math.sin(b) * 20;

    } else if (this.danceStyle === 'salsa_fiesta') {
      const sway = Math.sin(b * Math.PI) * 35;
      bodyX = cx + sway;
      bodyY = groundY - 140 + Math.abs(Math.cos(b * Math.PI)) * 12;
      headX = bodyX - sway * 0.2;
      headY = bodyY - 85;

      lHandX = bodyX - 60 + Math.sin(b * 1.5) * 25;
      lHandY = bodyY - 60 + Math.cos(b * 1.5) * 35;
      rHandX = bodyX + 60 + Math.cos(b * 1.5) * 25;
      rHandY = bodyY - 60 - Math.sin(b * 1.5) * 35;

      lFootX = bodyX - 35 + Math.sin(b * Math.PI) * 30;
      rFootX = bodyX + 35 - Math.sin(b * Math.PI) * 30;

    } else if (this.danceStyle === 'kpop_idol') {
      const bounce = Math.abs(Math.sin(b * Math.PI * 2)) * 15;
      bodyX = cx + Math.sin(b * 0.5) * 25;
      bodyY = groundY - 140 + bounce;
      headX = bodyX;
      headY = bodyY - 85;

      const phase = Math.floor(b) % 4;
      if (phase === 0 || phase === 2) {
        lHandX = bodyX - 80;
        lHandY = bodyY - 80;
        rHandX = bodyX + 75;
        rHandY = bodyY - 20;
      } else {
        lHandX = bodyX - 25;
        lHandY = bodyY - 50;
        rHandX = bodyX + 25;
        rHandY = bodyY - 50;
      }

      lFootX = bodyX - 45 + Math.sin(b * Math.PI) * 15;
      rFootX = bodyX + 45 - Math.sin(b * Math.PI) * 15;

    } else if (this.danceStyle === 'breakdance_freeze') {
      const cycle = b % 8;
      if (cycle < 6) {
        const angle = b * Math.PI * 2;
        bodyX = cx + Math.cos(angle) * 30;
        bodyY = groundY - 70 + Math.sin(angle) * 15;
        headX = bodyX - Math.cos(angle) * 20;
        headY = bodyY + 30;

        lHandX = bodyX - 60;
        lHandY = groundY - 10;
        rHandX = bodyX + 60;
        rHandY = groundY - 10;

        lFootX = bodyX + Math.cos(angle + 1) * 90;
        lFootY = bodyY + Math.sin(angle + 1) * 70;
        rFootX = bodyX + Math.cos(angle + 3.14) * 90;
        rFootY = bodyY + Math.sin(angle + 3.14) * 70;
      } else {
        bodyX = cx;
        bodyY = groundY - 100;
        headX = cx - 15;
        headY = groundY - 60;

        lHandX = cx - 20;
        lHandY = groundY;
        rHandX = cx + 50;
        rHandY = groundY - 120;

        lFootX = cx + 80;
        lFootY = groundY - 160;
        rFootX = cx + 40;
        rFootY = groundY - 180;
      }
    }

    const lElbowX = (bodyX - 25 + lHandX) / 2 + Math.sin(t * 4) * 10;
    const lElbowY = (bodyY - 40 + lHandY) / 2;
    const rElbowX = (bodyX + 25 + rHandX) / 2 - Math.sin(t * 4) * 10;
    const rElbowY = (bodyY - 40 + rHandY) / 2;

    const lKneeX = (bodyX - 15 + lFootX) / 2 - 10;
    const lKneeY = (bodyY + 20 + lFootY) / 2;
    const rKneeX = (bodyX + 15 + rFootX) / 2 + 10;
    const rKneeY = (bodyY + 20 + rFootY) / 2;

    this.drawSkeleton(ctx, {
      head: { x: headX, y: headY },
      neck: { x: bodyX, y: bodyY - 50 },
      lShoulder: { x: bodyX - 30, y: bodyY - 45 },
      rShoulder: { x: bodyX + 30, y: bodyY - 45 },
      lElbow: { x: lElbowX, y: lElbowY },
      rElbow: { x: rElbowX, y: rElbowY },
      lHand: { x: lHandX, y: lHandY },
      rHand: { x: rHandX, y: rHandY },
      hip: { x: bodyX, y: bodyY + 20 },
      lHip: { x: bodyX - 20, y: bodyY + 20 },
      rHip: { x: bodyX + 20, y: bodyY + 20 },
      lKnee: { x: lKneeX, y: lKneeY },
      rKnee: { x: rKneeX, y: rKneeY },
      lFoot: { x: lFootX, y: lFootY },
      rFoot: { x: rFootX, y: rFootY }
    }, style);

    this.drawAvatarHead(ctx, headX, headY, style, t);
    ctx.restore();
  }

  drawSkeleton(ctx, joints, style) {
    ctx.save();
    ctx.shadowBlur = 15;
    ctx.shadowColor = style.primaryColor;
    ctx.strokeStyle = style.primaryColor;
    ctx.lineWidth = 5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    const connections = [
      ['neck', 'hip'],
      ['neck', 'lShoulder'],
      ['lShoulder', 'lElbow'],
      ['lElbow', 'lHand'],
      ['neck', 'rShoulder'],
      ['rShoulder', 'rElbow'],
      ['rElbow', 'rHand'],
      ['hip', 'lHip'],
      ['lHip', 'lKnee'],
      ['lKnee', 'lFoot'],
      ['hip', 'rHip'],
      ['rHip', 'rKnee'],
      ['rKnee', 'rFoot']
    ];

    for (const [j1, j2] of connections) {
      ctx.beginPath();
      ctx.moveTo(joints[j1].x, joints[j1].y);
      ctx.lineTo(joints[j2].x, joints[j2].y);
      ctx.stroke();
    }

    ctx.fillStyle = style.accentColor;
    ctx.shadowBlur = 10;
    ctx.shadowColor = style.accentColor;
    for (const key in joints) {
      if (key === 'head') continue;
      ctx.beginPath();
      ctx.arc(joints[key].x, joints[key].y, 5, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  drawAvatarHead(ctx, hx, hy, style, t) {
    ctx.save();
    const r = 26;

    if (this.userMedia && this.userMedia.element) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(hx, hy, r, 0, Math.PI * 2);
      ctx.clip();
      
      try {
        const el = this.userMedia.element;
        ctx.drawImage(el, hx - r, hy - r, r * 2, r * 2);
      } catch (e) {
        ctx.fillStyle = '#6366f1';
        ctx.fill();
      }
      ctx.restore();

      ctx.strokeStyle = style.primaryColor;
      ctx.lineWidth = 3;
      ctx.shadowBlur = 12;
      ctx.shadowColor = style.primaryColor;
      ctx.beginPath();
      ctx.arc(hx, hy, r + 2, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      const grad = ctx.createLinearGradient(hx - r, hy - r, hx + r, hy + r);
      grad.addColorStop(0, style.primaryColor);
      grad.addColorStop(1, style.secondaryColor);

      ctx.fillStyle = grad;
      ctx.shadowBlur = 16;
      ctx.shadowColor = style.primaryColor;
      ctx.beginPath();
      ctx.arc(hx, hy, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#0f172a';
      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(hx - 16, hy - 6, 32, 12, 4) : ctx.rect(hx - 16, hy - 6, 32, 12);
      ctx.fill();

      ctx.fillStyle = style.accentColor;
      ctx.shadowBlur = 8;
      ctx.shadowColor = style.accentColor;
      ctx.fillRect(hx - 12 + Math.sin(t * 6) * 4, hy - 2, 12, 4);
    }
    ctx.restore();
  }

  drawHudOverlay(ctx, w, h, t, style) {
    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 13px system-ui, -apple-system, sans-serif';
    ctx.globalAlpha = 0.85;
    ctx.fillText(`AI DANCE STUDIO • ${style.name.toUpperCase()}`, 24, 32);

    ctx.font = '400 11px monospace';
    ctx.fillStyle = style.primaryColor;
    ctx.fillText(`TEMPO: ${style.bpm} BPM | 4K 60FPS | NEURAL SYNC ON`, 24, 48);

    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(w - 75, 28, 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.font = '600 11px system-ui';
    ctx.fillText('LIVE AI', w - 64, 32);

    ctx.fillStyle = 'rgba(255, 255, 255, 0.015)';
    for (let y = 0; y < h; y += 4) {
      ctx.fillRect(0, y, w, 1);
    }
    ctx.restore();
  }

  startAudioLoop() {
    if (!this.audioCtx || this.audioPlaying) return;
    this.audioPlaying = true;

    const style = this.styles[this.danceStyle];
    const bpm = style.bpm;
    const intervalMs = (60 / bpm) * 1000;

    let step = 0;
    this.audioTimer = setInterval(() => {
      if (!this.isPlaying || this.isMuted) return;
      this.playSynthBeat(step, style);
      step = (step + 1) % 16;
    }, intervalMs / 2);
  }

  stopAudioLoop() {
    this.audioPlaying = false;
    if (this.audioTimer) {
      clearInterval(this.audioTimer);
      this.audioTimer = null;
    }
  }

  playSynthBeat(step, style) {
    if (!this.audioCtx || this.isMuted || this.volume <= 0) return;
    const ctx = this.audioCtx;
    const t = ctx.currentTime;
    const masterGain = ctx.createGain();
    masterGain.gain.setValueAtTime(this.volume * 0.4, t);
    masterGain.connect(ctx.destination);

    if (step % 4 === 0) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.setValueAtTime(150, t);
      osc.frequency.exponentialRampToValueAtTime(35, t + 0.12);
      gain.gain.setValueAtTime(1.0, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
      osc.connect(gain);
      gain.connect(masterGain);
      osc.start(t);
      osc.stop(t + 0.18);
    }

    if (step % 2 === 1) {
      const bufferSize = ctx.sampleRate * 0.04;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }
      const whiteNoise = ctx.createBufferSource();
      whiteNoise.buffer = buffer;
      const filter = ctx.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.value = 7000;
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.3, t);
      gain.gain.exponentialRampToValueAtTime(0.01, t + 0.04);
      whiteNoise.connect(filter);
      filter.connect(gain);
      gain.connect(masterGain);
      whiteNoise.start(t);
    }

    if (step % 2 === 0) {
      const scale = style.synthScale;
      const noteFreq = scale[step % scale.length];
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = this.danceStyle === 'cyber_hiphop' ? 'sawtooth' : 'triangle';
      osc.frequency.setValueAtTime(noteFreq, t);
      gain.gain.setValueAtTime(0.25, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.22);
      osc.connect(gain);
      gain.connect(masterGain);
      osc.start(t);
      osc.stop(t + 0.22);
    }
  }

  generateVideoBlob(durationSeconds = 6) {
    return new Promise((resolve, reject) => {
      try {
        const stream = this.canvas.captureStream(30);
        let options = { mimeType: 'video/webm;codecs=vp9' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
          options = { mimeType: 'video/webm' };
          if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options = {};
          }
        }

        const recorder = new MediaRecorder(stream, options);
        const chunks = [];

        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) chunks.push(e.data);
        };

        recorder.onstop = () => {
          const blob = new Blob(chunks, { type: options.mimeType || 'video/webm' });
          resolve(blob);
        };

        const prevPlaying = this.isPlaying;
        this.play();
        recorder.start();

        setTimeout(() => {
          recorder.stop();
          if (!prevPlaying) this.pause();
        }, durationSeconds * 1000);

      } catch (err) {
        reject(err);
      }
    });
  }
}