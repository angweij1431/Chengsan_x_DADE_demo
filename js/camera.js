/**
 * Camera Recorder Controller
 */
class CameraController {
  constructor(options) {
    this.videoElement = options.videoElement;
    this.timerElement = options.timerElement;
    this.statusElement = options.statusElement;
    this.onStateChange = options.onStateChange || (() => {});
    this.onRecorded = options.onRecorded || (() => {});

    this.stream = null;
    this.mediaRecorder = null;
    this.recordedChunks = [];
    this.recordedBlob = null;
    this.recordedUrl = null;
    this.recordTimer = null;
    this.recordSeconds = 0;
    this.maxRecordSeconds = 15;
    this.state = 'uninitialized';
    this.isFacingUser = true;
  }

  async startCamera() {
    try {
      this.stopCamera();

      const constraints = {
        video: {
          facingMode: this.isFacingUser ? 'user' : 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: true
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.videoElement.srcObject = this.stream;
      this.videoElement.muted = true;
      this.videoElement.playsInline = true;
      await this.videoElement.play();

      this.setState('preview');
      return true;
    } catch (error) {
      console.warn('Camera access error:', error);
      this.setState('error', error.message || 'Camera permission denied or camera not found.');
      return false;
    }
  }

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoElement.srcObject) {
      this.videoElement.srcObject = null;
    }
  }

  toggleFlip() {
    this.isFacingUser = !this.isFacingUser;
    if (this.state === 'preview' || this.state === 'recording') {
      this.startCamera();
    }
  }

  startRecording() {
    if (!this.stream) return;

    this.recordedChunks = [];
    let options = { mimeType: 'video/webm;codecs=vp9' };
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
      options = { mimeType: 'video/webm' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = {};
      }
    }

    try {
      this.mediaRecorder = new MediaRecorder(this.stream, options);

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          this.recordedChunks.push(e.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        this.recordedBlob = new Blob(this.recordedChunks, { type: options.mimeType || 'video/webm' });
        if (this.recordedUrl) URL.revokeObjectURL(this.recordedUrl);
        this.recordedUrl = URL.createObjectURL(this.recordedBlob);

        this.videoElement.srcObject = null;
        this.videoElement.src = this.recordedUrl;
        this.videoElement.muted = false;
        this.videoElement.controls = false;
        this.videoElement.loop = true;
        this.videoElement.play();

        this.setState('recorded');
        this.onRecorded(this.recordedBlob, this.recordedUrl);
      };

      this.mediaRecorder.start(250);
      this.recordSeconds = 0;
      this.updateTimerDisplay();

      this.recordTimer = setInterval(() => {
        this.recordSeconds++;
        this.updateTimerDisplay();
        if (this.recordSeconds >= this.maxRecordSeconds) {
          this.stopRecording();
        }
      }, 1000);

      this.setState('recording');
    } catch (err) {
      console.error('Failed to start MediaRecorder:', err);
      this.setState('error', 'Unable to record video on this browser.');
    }
  }

  stopRecording() {
    if (this.recordTimer) {
      clearInterval(this.recordTimer);
      this.recordTimer = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
  }

  retake() {
    if (this.recordedUrl) {
      URL.revokeObjectURL(this.recordedUrl);
      this.recordedUrl = null;
      this.recordedBlob = null;
    }
    this.videoElement.src = '';
    this.startCamera();
  }

  updateTimerDisplay() {
    if (!this.timerElement) return;
    const mins = Math.floor(this.recordSeconds / 60).toString().padStart(2, '0');
    const secs = (this.recordSeconds % 60).toString().padStart(2, '0');
    this.timerElement.textContent = `${mins}:${secs}`;
  }

  setState(newState, errorMsg = '') {
    this.state = newState;
    this.onStateChange(newState, errorMsg);
  }
}