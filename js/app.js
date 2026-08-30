/**
 * AI Dance Studio - Main Application Controller
 */
document.addEventListener('DOMContentLoaded', () => {
  const state = {
    currentPage: 1,
    uploadedMedia: null,
    cameraVideoBlob: null,
    cameraVideoUrl: null,
    selectedDance: 'cyber_hiphop',
    generatedVideoId: 'dance_' + Math.random().toString(36).substring(2, 9),
    generatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  };

  const elements = {
    steppers: document.querySelectorAll('.step-indicator'),
    pages: {
      1: document.getElementById('page-1'),
      2: document.getElementById('page-2'),
      3: document.getElementById('page-3'),
      4: document.getElementById('page-4'),
      5: document.getElementById('page-5')
    },

    fileInput: document.getElementById('media-file-input'),
    dropzone: document.getElementById('upload-dropzone'),
    previewCard: document.getElementById('upload-preview-card'),
    previewThumb: document.getElementById('preview-thumbnail'),
    previewFilename: document.getElementById('preview-filename'),
    previewMeta: document.getElementById('preview-meta'),
    removeUploadBtn: document.getElementById('remove-upload-btn'),
    page1ContinueBtn: document.getElementById('page-1-continue-btn'),
    quickDemoBtn: document.getElementById('quick-demo-btn'),
    presetButtons: document.querySelectorAll('.preset-btn'),

    cameraVideo: document.getElementById('camera-preview-video'),
    cameraTimer: document.getElementById('camera-rec-timer'),
    recBadge: document.getElementById('camera-rec-badge'),
    cameraPlaceholder: document.getElementById('camera-placeholder'),
    startRecBtn: document.getElementById('start-record-btn'),
    stopRecBtn: document.getElementById('stop-record-btn'),
    retakeBtn: document.getElementById('retake-record-btn'),
    useVideoBtn: document.getElementById('use-record-btn'),
    flipCamBtn: document.getElementById('flip-camera-btn'),
    startCamBtn: document.getElementById('start-camera-stream-btn'),
    danceCards: document.querySelectorAll('.dance-card'),
    generateDanceBtn: document.getElementById('generate-dance-btn'),
    page2BackBtn: document.getElementById('page-2-back-btn'),
    useUploadedNotice: document.getElementById('use-uploaded-notice'),

    progressBar: document.getElementById('progress-bar-fill'),
    progressPercent: document.getElementById('progress-percent'),
    statusSteps: document.querySelectorAll('.status-step-item'),
    skipProcessingBtn: document.getElementById('skip-processing-btn'),

    danceCanvas: document.getElementById('dance-canvas'),
    videoFrame: document.getElementById('video-showcase-frame'),
    videoStyleTag: document.getElementById('video-style-tag'),
    centerPlayBtn: document.getElementById('video-center-play-btn'),
    playPauseBtn: document.getElementById('btn-play-pause'),
    scrubberTrack: document.getElementById('scrubber-track'),
    scrubberFill: document.getElementById('scrubber-fill'),
    timeDisplay: document.getElementById('time-display'),
    muteBtn: document.getElementById('btn-mute'),
    volumeSlider: document.getElementById('volume-slider'),
    speedSelect: document.getElementById('speed-select'),
    fullscreenBtn: document.getElementById('btn-fullscreen'),
    downloadVideoBtn: document.getElementById('download-video-btn'),
    createAnotherBtn: document.getElementById('create-another-btn'),
    shareBtn: document.getElementById('share-video-btn'),
    page4BackBtn: document.getElementById('page-4-back-btn'),

    qrCanvas: document.getElementById('qr-canvas'),
    shareMiniThumb: document.getElementById('share-mini-thumb'),
    shareMiniTitle: document.getElementById('share-mini-title'),
    shareMiniMeta: document.getElementById('share-mini-meta'),
    shareLinkInput: document.getElementById('share-link-input'),
    copyLinkBtn: document.getElementById('copy-link-btn'),
    downloadQrBtn: document.getElementById('download-qr-btn'),
    backToVideoBtn: document.getElementById('back-to-video-btn'),
    socialButtons: document.querySelectorAll('.social-btn'),
    toastContainer: document.getElementById('toast-container')
  };

  let cameraController = null;
  let danceEngine = null;

  if (elements.danceCanvas) {
    elements.danceCanvas.width = 960;
    elements.danceCanvas.height = 540;
    danceEngine = new DanceEngine(elements.danceCanvas);
  }

  cameraController = new CameraController({
    videoElement: elements.cameraVideo,
    timerElement: elements.cameraTimer,
    statusElement: elements.recBadge,
    onStateChange: handleCameraStateChange,
    onRecorded: (blob, url) => {
      state.cameraVideoBlob = blob;
      state.cameraVideoUrl = url;
      showToast('Video recorded successfully! Ready to generate dance.');
      updatePage2GenerateButton();
    }
  });

  // PAGE NAVIGATION ROUTER
  function navigateTo(pageNumber) {
    if (pageNumber < 1 || pageNumber > 5) return;

    if (state.currentPage === 4 && danceEngine) {
      danceEngine.pause();
      elements.videoFrame.classList.remove('playing');
    }

    if (state.currentPage === 2 && cameraController) {
      cameraController.stopCamera();
    }

    state.currentPage = pageNumber;

    for (const p in elements.pages) {
      if (elements.pages[p]) {
        elements.pages[p].classList.remove('active');
      }
    }
    elements.pages[pageNumber].classList.add('active');

    elements.steppers.forEach((stepper, idx) => {
      const stepIdx = idx + 1;
      stepper.classList.remove('active', 'completed');
      if (stepIdx === pageNumber) {
        stepper.classList.add('active');
      } else if (stepIdx < pageNumber) {
        stepper.classList.add('completed');
      }
    });

    if (pageNumber === 2) {
      ensureDefaultMedia();
      onEnterPage2();
    } else if (pageNumber === 3) {
      ensureDefaultMedia();
      startAiProcessing();
    } else if (pageNumber === 4) {
      ensureDefaultMedia();
      onEnterPage4();
    } else if (pageNumber === 5) {
      ensureDefaultMedia();
      onEnterPage5();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function ensureDefaultMedia() {
    if (!state.uploadedMedia && !state.cameraVideoBlob) {
      const avatarSvg = createPresetAvatar('guy');
      const blob = new Blob([avatarSvg], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.src = url;
      state.uploadedMedia = {
        type: 'image',
        file: null,
        url: url,
        element: img,
        name: 'Demo Dancer Preset.svg',
        size: 'Demo Asset'
      };
    }
  }

  // Clickable Stepper Navigation
  elements.steppers.forEach(stepper => {
    stepper.addEventListener('click', () => {
      const stepNum = parseInt(stepper.dataset.step, 10);
      if (stepNum) {
        ensureDefaultMedia();
        navigateTo(stepNum);
      }
    });
  });

  // PAGE 1: UPLOAD LOGIC
  ['dragenter', 'dragover'].forEach(eventName => {
    elements.dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      elements.dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    elements.dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      elements.dropzone.classList.remove('dragover');
    });
  });

  elements.dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length > 0) processUploadedFile(files[0]);
  });

  elements.dropzone.addEventListener('click', (e) => {
    if (e.target !== elements.fileInput) elements.fileInput.click();
  });

  elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processUploadedFile(e.target.files[0]);
    }
  });

  function processUploadedFile(file) {
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');

    if (!isImage && !isVideo) {
      showToast('Please upload a valid image (JPG, PNG) or video (MP4, WebM).');
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const mediaObj = {
      type: isImage ? 'image' : 'video',
      file: file,
      url: objectUrl,
      name: file.name,
      size: (file.size / (1024 * 1024)).toFixed(2) + ' MB'
    };

    if (isImage) {
      const img = new Image();
      img.src = objectUrl;
      img.onload = () => {
        mediaObj.element = img;
        setUploadedMedia(mediaObj);
      };
    } else {
      const vid = document.createElement('video');
      vid.src = objectUrl;
      vid.muted = true;
      vid.playsInline = true;
      vid.onloadedmetadata = () => {
        if (vid.duration > 8) {
          showToast('⏱️ Notice: Video exceeds 8s limit. Automatically trimming to the first 8 seconds!', 6000);
          mediaObj.trimmed = true;
        }
        mediaObj.element = vid;
        setUploadedMedia(mediaObj);
      };
      vid.onerror = () => {
        mediaObj.element = vid;
        setUploadedMedia(mediaObj);
      };
    }
  }

  function setUploadedMedia(mediaObj) {
    if (state.uploadedMedia && state.uploadedMedia.url) {
      URL.revokeObjectURL(state.uploadedMedia.url);
    }
    state.uploadedMedia = mediaObj;

    elements.previewFilename.textContent = mediaObj.name;
    elements.previewMeta.innerHTML = `<span>${mediaObj.type.toUpperCase()}</span> • <span>${mediaObj.size}</span>`;
    elements.previewThumb.src = mediaObj.url;

    elements.dropzone.style.display = 'none';
    elements.previewCard.classList.add('show');
    showToast('Media uploaded successfully!');
  }

  elements.removeUploadBtn.addEventListener('click', () => {
    if (state.uploadedMedia && state.uploadedMedia.url) {
      URL.revokeObjectURL(state.uploadedMedia.url);
    }
    state.uploadedMedia = null;
    elements.fileInput.value = '';
    elements.previewCard.classList.remove('show');
    elements.dropzone.style.display = 'block';
    elements.presetButtons.forEach(b => b.classList.remove('active'));
  });

  elements.presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      elements.presetButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const presetKey = btn.dataset.preset;
      const avatarSvg = createPresetAvatar(presetKey);
      const blob = new Blob([avatarSvg], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);

      const img = new Image();
      img.src = url;
      img.onload = () => {
        setUploadedMedia({
          type: 'image',
          file: null,
          url: url,
          element: img,
          name: `${btn.textContent.trim()} Preset.svg`,
          size: 'Demo Asset'
        });
      };
    });
  });

  function createPresetAvatar(preset) {
    let color1 = '#00f0ff', color2 = '#7928ca';
    if (preset === 'girl') { color1 = '#ff007f'; color2 = '#ffaa00'; }
    if (preset === 'dancer') { color1 = '#ff9100'; color2 = '#00e676'; }
    if (preset === 'robot') { color1 = '#38ef7d'; color2 = '#11998e'; }

    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${color1}" />
          <stop offset="100%" stop-color="${color2}" />
        </linearGradient>
      </defs>
      <rect width="120" height="120" fill="#0b0f19" />
      <circle cx="60" cy="46" r="28" fill="url(#g)" />
      <path d="M24 110 C24 85 40 76 60 76 C80 76 96 85 96 110 Z" fill="url(#g)" opacity="0.85" />
      <circle cx="50" cy="42" r="4" fill="#ffffff" />
      <circle cx="70" cy="42" r="4" fill="#ffffff" />
      <rect x="44" y="54" width="32" height="5" rx="2.5" fill="#ffffff" />
    </svg>`;
  }

  elements.page1ContinueBtn.addEventListener('click', () => {
    ensureDefaultMedia();
    navigateTo(2);
  });

  if (elements.quickDemoBtn) {
    elements.quickDemoBtn.addEventListener('click', () => {
      ensureDefaultMedia();
      navigateTo(2);
    });
  }

  if (elements.page2BackBtn) {
    elements.page2BackBtn.addEventListener('click', () => {
      navigateTo(1);
    });
  }

  if (elements.page4BackBtn) {
    elements.page4BackBtn.addEventListener('click', () => {
      navigateTo(2);
    });
  }

  // PAGE 2: CAMERA & DANCE SELECTION
  function onEnterPage2() {
    if (state.uploadedMedia) {
      elements.useUploadedNotice.style.display = 'block';
      elements.useUploadedNotice.innerHTML = `✨ <strong>Ready:</strong> Using your uploaded media (<em>${state.uploadedMedia.name}</em>) or you can record a live camera clip below.`;
    } else {
      elements.useUploadedNotice.style.display = 'none';
    }
    updatePage2GenerateButton();
  }

  function handleCameraStateChange(newState, errorMsg) {
    if (newState === 'preview') {
      elements.cameraPlaceholder.style.display = 'none';
      elements.startRecBtn.style.display = 'inline-flex';
      elements.stopRecBtn.style.display = 'none';
      elements.retakeBtn.style.display = 'none';
      elements.useVideoBtn.style.display = 'none';
      elements.recBadge.classList.remove('recording');
    } else if (newState === 'recording') {
      elements.startRecBtn.style.display = 'none';
      elements.stopRecBtn.style.display = 'inline-flex';
      elements.retakeBtn.style.display = 'none';
      elements.useVideoBtn.style.display = 'none';
      elements.recBadge.classList.add('recording');
    } else if (newState === 'recorded') {
      elements.startRecBtn.style.display = 'none';
      elements.stopRecBtn.style.display = 'none';
      elements.retakeBtn.style.display = 'inline-flex';
      elements.useVideoBtn.style.display = 'inline-flex';
      elements.recBadge.classList.remove('recording');
    } else if (newState === 'error') {
      elements.cameraPlaceholder.style.display = 'flex';
      elements.cameraPlaceholder.innerHTML = `
        <div style="font-size: 2rem;">📷</div>
        <p><strong>Camera not available or access denied.</strong></p>
        <p style="font-size: 0.8rem; color: #94a3b8;">${errorMsg || 'You can continue using your uploaded media from Page 1.'}</p>
      `;
    }
  }

  elements.startCamBtn.addEventListener('click', () => {
    cameraController.startCamera();
  });

  elements.startRecBtn.addEventListener('click', () => {
    cameraController.startRecording();
  });

  elements.stopRecBtn.addEventListener('click', () => {
    cameraController.stopRecording();
  });

  elements.retakeBtn.addEventListener('click', () => {
    cameraController.retake();
  });

  elements.useVideoBtn.addEventListener('click', () => {
    showToast('Video selected for dance generation!');
    updatePage2GenerateButton();
  });

  elements.flipCamBtn.addEventListener('click', () => {
    cameraController.toggleFlip();
  });

  elements.danceCards.forEach(card => {
    card.addEventListener('click', () => {
      elements.danceCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      state.selectedDance = card.dataset.style;
      updatePage2GenerateButton();
    });
  });

  function updatePage2GenerateButton() {
    // Keep generate button active for smooth experience
    elements.generateDanceBtn.removeAttribute('disabled');
  }

  elements.generateDanceBtn.addEventListener('click', () => {
    ensureDefaultMedia();
    navigateTo(3);
  });

  // PAGE 3: AI PROCESSING ANIMATION
  let processingInterval = null;

  function startAiProcessing() {
    if (processingInterval) {
      clearInterval(processingInterval);
      processingInterval = null;
    }

    let progress = 0;
    elements.progressBar.style.width = '0%';
    elements.progressPercent.textContent = '0%';

    const stepMilestones = [
      { step: 0, targetPct: 20, desc: 'Analysing your media & composition' },
      { step: 1, targetPct: 45, desc: 'Tracking 33-point skeletal landmarks' },
      { step: 2, targetPct: 70, desc: `Synthesizing ${danceEngine.styles[state.selectedDance].name} moves` },
      { step: 3, targetPct: 90, desc: 'Rendering neural lighting & beat sync' },
      { step: 4, targetPct: 100, desc: 'Encoding final HD dance video' }
    ];

    elements.statusSteps.forEach(s => s.classList.remove('active', 'completed'));
    if (elements.statusSteps[0]) elements.statusSteps[0].classList.add('active');

    // Dispatch API call to Flask backend service
    fetch('/api/process-dance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dance_style: state.selectedDance,
        source_media: state.uploadedMedia ? state.uploadedMedia.name : 'preset_guy',
        user_media: state.cameraVideoUrl ? 'live_camera_clip' : 'uploaded_avatar'
      })
    }).then(res => res.json()).then(data => {
      if (data && data.status === 'success') {
        state.backendResponse = data;
        state.generatedVideoId = data.video_id;
        console.log('[Backend Integration] Generated video ID:', data.video_id, data.download_url);
      }
    }).catch(err => {
      console.warn('[Backend Notice] Running in offline demo mode:', err);
    });

    processingInterval = setInterval(() => {
      progress += 1;
      elements.progressBar.style.width = `${progress}%`;
      elements.progressPercent.textContent = `${progress}%`;

      stepMilestones.forEach((m, idx) => {
        if (progress >= m.targetPct) {
          if (elements.statusSteps[idx]) {
            elements.statusSteps[idx].classList.remove('active');
            elements.statusSteps[idx].classList.add('completed');
          }
          if (elements.statusSteps[idx + 1] && progress < 100) {
            elements.statusSteps[idx + 1].classList.add('active');
          }
        }
      });

      if (progress >= 100) {
        clearInterval(processingInterval);
        processingInterval = null;
        setTimeout(() => {
          navigateTo(4);
        }, 500);
      }
    }, 40);
  }

  if (elements.skipProcessingBtn) {
    elements.skipProcessingBtn.addEventListener('click', () => {
      if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
      }
      navigateTo(4);
    });
  }

  // PAGE 4: GENERATED VIDEO SHOWCASE
  function onEnterPage4() {
    const style = danceEngine.styles[state.selectedDance];
    elements.videoStyleTag.textContent = `${style.name.toUpperCase()} • ${style.bpm} BPM`;

    if (state.cameraVideoUrl) {
      const vid = document.createElement('video');
      vid.src = state.cameraVideoUrl;
      vid.loop = true;
      vid.muted = true;
      vid.play();
      danceEngine.setUserMedia({ type: 'video', element: vid });
    } else if (state.uploadedMedia) {
      danceEngine.setUserMedia(state.uploadedMedia);
    }

    danceEngine.setDanceStyle(state.selectedDance);

    danceEngine.onTimeUpdate = (cur, dur) => {
      const pct = (cur / dur) * 100;
      elements.scrubberFill.style.width = `${pct}%`;
      const curM = Math.floor(cur / 60).toString().padStart(2, '0');
      const curS = Math.floor(cur % 60).toString().padStart(2, '0');
      const durM = Math.floor(dur / 60).toString().padStart(2, '0');
      const durS = Math.floor(dur % 60).toString().padStart(2, '0');
      elements.timeDisplay.textContent = `${curM}:${curS} / ${durM}:${durS}`;
    };

    danceEngine.play();
    elements.videoFrame.classList.add('playing');
    elements.playPauseBtn.textContent = '⏸';
    elements.centerPlayBtn.style.display = 'none';
  }

  function togglePlayPause() {
    if (danceEngine.isPlaying) {
      danceEngine.pause();
      elements.videoFrame.classList.remove('playing');
      elements.playPauseBtn.textContent = '▶';
      elements.centerPlayBtn.style.display = 'grid';
    } else {
      danceEngine.play();
      elements.videoFrame.classList.add('playing');
      elements.playPauseBtn.textContent = '⏸';
      elements.centerPlayBtn.style.display = 'none';
    }
  }

  elements.playPauseBtn.addEventListener('click', togglePlayPause);
  elements.centerPlayBtn.addEventListener('click', togglePlayPause);
  elements.videoFrame.addEventListener('click', (e) => {
    if (e.target === elements.danceCanvas) togglePlayPause();
  });

  elements.scrubberTrack.addEventListener('click', (e) => {
    const rect = elements.scrubberTrack.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    danceEngine.seek(pos * danceEngine.duration);
  });

  elements.muteBtn.addEventListener('click', () => {
    danceEngine.isMuted = !danceEngine.isMuted;
    elements.muteBtn.textContent = danceEngine.isMuted ? '🔇' : '🔊';
  });

  elements.volumeSlider.addEventListener('input', (e) => {
    const vol = parseFloat(e.target.value);
    danceEngine.setVolume(vol);
    danceEngine.setMuted(vol === 0);
    elements.muteBtn.textContent = vol === 0 ? '🔇' : '🔊';
  });

  elements.speedSelect.addEventListener('change', (e) => {
    danceEngine.setPlaybackRate(parseFloat(e.target.value));
  });

  elements.fullscreenBtn.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      elements.videoFrame.requestFullscreen().catch(err => console.warn(err));
    } else {
      document.exitFullscreen();
    }
  });

  elements.downloadVideoBtn.addEventListener('click', async () => {
    showToast('Preparing your high quality video download...');
    try {
      const blob = await danceEngine.generateVideoBlob(6);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `AI_Dance_${danceEngine.styles[state.selectedDance].name.replace(/\s+/g, '_')}.webm`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('🎉 Video downloaded successfully!');
    } catch (err) {
      console.warn('Video download error:', err);
      const imgUrl = elements.danceCanvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = imgUrl;
      a.download = `AI_Dance_Frame_${state.selectedDance}.png`;
      a.click();
      showToast('Downloaded HD Dance Snapshot!');
    }
  });

  elements.createAnotherBtn.addEventListener('click', () => {
    navigateTo(1);
  });

  elements.shareBtn.addEventListener('click', () => {
    navigateTo(5);
  });

  // PAGE 5: QR CODE & MOBILE SHARING
  function onEnterPage5() {
    const style = danceEngine.styles[state.selectedDance];
    let shareUrl = `${window.location.origin}/download/${state.generatedVideoId}`;

    if (state.backendResponse && state.backendResponse.qr_target_url) {
      shareUrl = state.backendResponse.qr_target_url;
    }

    QRCodeGenerator.renderToCanvas(elements.qrCanvas, shareUrl, 220);

    elements.shareMiniTitle.textContent = `${style.name} AI Video`;
    elements.shareMiniMeta.textContent = `Generated today • ${style.bpm} BPM • 1080p`;
    elements.shareLinkInput.value = shareUrl;

    const snapshot = elements.danceCanvas.toDataURL('image/jpeg', 0.85);
    elements.shareMiniThumb.src = snapshot;
  }

  elements.copyLinkBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(elements.shareLinkInput.value).then(() => {
      showToast('📋 Link copied to clipboard!');
    }).catch(() => {
      elements.shareLinkInput.select();
      document.execCommand('copy');
      showToast('📋 Link copied to clipboard!');
    });
  });

  elements.downloadQrBtn.addEventListener('click', () => {
    const qrData = elements.qrCanvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = qrData;
    a.download = `AI_Dance_QR_${state.selectedDance}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast('💾 QR Code downloaded!');
  });

  elements.backToVideoBtn.addEventListener('click', () => {
    navigateTo(4);
  });

  elements.socialButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const platform = btn.dataset.platform;
      const text = `Check out my AI-generated ${danceEngine.styles[state.selectedDance].name} dance video!`;
      const url = encodeURIComponent(elements.shareLinkInput.value);

      if (platform === 'whatsapp') {
        window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(text + ' ' + url)}`, '_blank');
      } else if (platform === 'twitter') {
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${url}`, '_blank');
      } else {
        navigator.clipboard.writeText(elements.shareLinkInput.value);
        showToast(`Copied link for ${platform.toUpperCase()}!`);
      }
    });
  });

  function showToast(message) {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>✨</span><span>${message}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3000);
  }
});