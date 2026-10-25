// Address of the Flask backend (backend/app.py). Change it if the API runs elsewhere.
const API_URL = 'http://127.0.0.1:5000/predict';

let stream, recorder, chunks = [], lipData = [], faceMesh, camera;
let isRecording = false, isUploadMode = false, uploadedFile = null;

const vid = document.getElementById('previewVideo');
const img = document.getElementById('imgPreview');
const out = document.getElementById('output');
const overlay = document.getElementById('overlay');
const ctx = overlay ? overlay.getContext('2d') : null;

setTimeout(() => {
  const loading = document.getElementById('loading');
  const landing = document.getElementById('landing');
  if (loading) loading.style.display = 'none';
  if (landing) landing.style.display = 'flex';
}, 1000);

const uploadBtn = document.getElementById('uploadBtn');
if (uploadBtn) uploadBtn.onclick = () => document.getElementById('fileInput').click();
const backBtn = document.getElementById('backBtn');
if (backBtn) backBtn.onclick = () => goHome();
const fileInput = document.getElementById('fileInput');
if (fileInput) fileInput.onchange = e => { if (e.target.files[0]) showFile(e.target.files[0]); };
const dropZone = document.getElementById('dropZone');
if (dropZone) dropZone.onclick = () => document.getElementById('fileInput').click();

function showFile(file) {
  const landing = document.getElementById('landing');
  const app = document.getElementById('app');
  if (landing) landing.style.display = 'none';
  if (app) app.style.display = 'flex';
  uploadedFile = file;
  isUploadMode = true;
  lipData = [];
  const url = URL.createObjectURL(file);
  
  if (!file.type.startsWith('video')) {
    if (out) out.innerText = 'Please upload a valid video file (mp4, webm, avi or mov).';
    const btn = document.getElementById('analyzeUploadBtn');
    if (btn) btn.style.display = 'none';
    uploadedFile = null; 
    isUploadMode = false;
    return;
  }
  
  // Fix black screen: clear old stream
  if (vid.srcObject) {
    try { vid.srcObject.getTracks().forEach(t => t.stop()); } catch(e) {}
    vid.srcObject = null;
  }
  if (vid.src && vid.src.startsWith('blob:')) {
    try { URL.revokeObjectURL(vid.src); } catch(e) {}
  }
  
  vid.src = url; 
  vid.style.display = 'block'; 
  if (img) img.style.display = 'none';
  vid.loop = false; 
  vid.muted = true;
  vid.controls = true;
  vid.playsInline = true;
  
  const recStart = document.getElementById('recStart');
  const recStop = document.getElementById('recStop');
  const analyzeBtn = document.getElementById('analyzeUploadBtn');
  if (recStart) recStart.style.display = 'none';
  if (recStop) recStop.style.display = 'none';
  if (analyzeBtn) analyzeBtn.style.display = 'inline-block';
  if (out) out.innerText = 'Video uploaded successfully - Click Analyze to read lips';
  
  vid.onloadedmetadata = () => {
    if (overlay) {
      overlay.width = vid.videoWidth; 
      overlay.height = vid.videoHeight;
      overlay.style.width = '100%';
      overlay.style.height = '100%';
    }
    startLipTrackingForUpload();
  };
  
  vid.oncanplay = () => {
    vid.play().catch(() => {});
  };
}

async function startLive() {
  const landing = document.getElementById('landing');
  const app = document.getElementById('app');
  if (landing) landing.style.display = 'none';
  if (app) app.style.display = 'flex';
  isUploadMode = false; lipData = [];
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    vid.srcObject = stream; 
    vid.style.display = 'block'; 
    if (img) img.style.display = 'none';
    vid.controls = false;
    await vid.play();
    const recStart = document.getElementById('recStart');
    const analyzeBtn = document.getElementById('analyzeUploadBtn');
    if (recStart) recStart.style.display = 'inline-block';
    if (analyzeBtn) analyzeBtn.style.display = 'none';
    if (out) out.innerText = 'Lips are being detected - Please move your mouth';
    startLipTracking();
  } catch (e) { 
    if (out) out.innerText = 'Error: ' + e.message; 
  }
}
const liveBtn = document.getElementById('liveBtn');
if (liveBtn) liveBtn.onclick = startLive;

function startLipTracking() {
  faceMesh = new FaceMesh({ locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}` });
  faceMesh.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
  faceMesh.onResults(onFaceResults);
  camera = new Camera(vid, {
    onFrame: async () => { await faceMesh.send({ image: vid }); },
    width: 640, height: 480
  });
  camera.start();
}

function startLipTrackingForUpload() {
  faceMesh = new FaceMesh({ locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}` });
  faceMesh.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
  faceMesh.onResults(onFaceResults);
  
  async function processFrame() {
    if (vid.paused || vid.ended || !isUploadMode) return;
    await faceMesh.send({ image: vid });
    requestAnimationFrame(processFrame);
  }
  vid.onplay = () => { lipData = []; processFrame(); };
}

function onFaceResults(results) {
  if (!overlay) return;
  if (!overlay.width) { overlay.width = vid.videoWidth; overlay.height = vid.videoHeight; }
  if (!ctx) return;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if (results.multiFaceLandmarks && results.multiFaceLandmarks[0]) {
    const landmarks = results.multiFaceLandmarks[0];
    const lipsIndices = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 13, 14];
    ctx.fillStyle = '#2563eb';
    lipsIndices.forEach(i => {
      const p = landmarks[i];
      ctx.beginPath();
      ctx.arc(p.x * overlay.width, p.y * overlay.height, 2.5, 0, 2 * Math.PI);
      ctx.fill();
    });
    const upper = landmarks[13], lower = landmarks[14];
    const dist = Math.abs(upper.y - lower.y);
    lipData.push(dist);
    if (isUploadMode) {
      if (out) out.innerText = `Tracking lip movements - Frames: ${lipData.length} | Mouth Open: ${dist.toFixed(4)}`;
    } else if (!isRecording) {
      if (out) {
        out.style.color = '';
        out.innerText = dist > 0.025 ? 'Mouth is open' : 'Face detected successfully';
      }
    }
  }
}

function startRec() {
  if (!stream) { alert('Please turn on the live camera first.'); return; }
  chunks = []; lipData = []; isRecording = true;
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: 'video/webm' });
    const timer = document.getElementById('timer');
    finishWithPrediction(blob, 'clip.webm', timer ? timer.innerText : '0 sec');
  };
  recorder.start();
  const recStart = document.getElementById('recStart');
  const recStop = document.getElementById('recStop');
  if (recStart) recStart.style.display = 'none';
  if (recStop) recStop.style.display = 'inline-block';
  if (out) out.innerText = 'Recording lip movements - Audio is not required';
  let s = 0; 
  const timerEl = document.getElementById('timer');
  window.t = setInterval(() => { s++; if (timerEl) timerEl.innerText = s + ' sec'; }, 1000);
}

function stopRec() {
  if (!isRecording) return;
  isRecording = false;
  try { recorder.stop(); } catch(e) {}
  clearInterval(window.t);
  const recStop = document.getElementById('recStop');
  if (recStop) recStop.style.display = 'none';
  if (out) out.innerText = 'Processing video, please wait...';
}

function analyzeUploadedVideo() {
  if (!uploadedFile) { alert('Please upload a video first.'); return; }
  finishWithPrediction(uploadedFile, uploadedFile.name, Math.floor(vid.duration || 0) + ' sec');
}

async function finishWithPrediction(blob, filename, duration) {
  if (out) {
    out.style.color = '';
    out.innerText = 'Reading lip movements - This may take a few seconds';
  }
  const analyzeBtn = document.getElementById('analyzeUploadBtn');
  if (analyzeBtn) analyzeBtn.disabled = true;
  let text;
  try {
    const form = new FormData();
    form.append('video', blob, filename);
    const res = await fetch(API_URL, { method: 'POST', body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || ('Server error ' + res.status));
    text = (data.prediction || '').trim() || '(No words recognized)';
  } catch (e) {
    const msg = (e instanceof TypeError)
      ? 'Cannot reach the backend server. Please start it with "python app.py" in the backend folder.'
      : e.message;
    if (out) {
      out.style.color = '#ef4444';
      out.innerText = 'Error: ' + msg;
    }
    if (analyzeBtn) analyzeBtn.disabled = false;
    const recStart = document.getElementById('recStart');
    if (!isUploadMode && recStart) recStart.style.display = 'inline-block';
    return;
  }
  try {
    localStorage.setItem('liply_text', text);
    localStorage.setItem('liply_duration', duration);
  } catch (e) {}
  try { await saveVideo(blob); } catch (e) {}
  window.location.href = 'result.html';
}

function openVideoDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('liply', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('videos');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function saveVideo(blob) {
  const db = await openVideoDB();
  await new Promise((resolve, reject) => {
    const tx = db.transaction('videos', 'readwrite');
    tx.objectStore('videos').put(blob, 'last');
    tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
  });
  db.close();
}

const recStartBtn = document.getElementById('recStart');
if (recStartBtn) recStartBtn.onclick = startRec;
const recStopBtn = document.getElementById('recStop');
if (recStopBtn) recStopBtn.onclick = stopRec;
const analyzeUploadBtn = document.getElementById('analyzeUploadBtn');
if (analyzeUploadBtn) analyzeUploadBtn.onclick = analyzeUploadedVideo;

function goHome() {
  if (stream) { try { stream.getTracks().forEach(t => t.stop()); } catch(e) {} }
  if (camera) { try { camera.stop(); } catch(e) {} }
  isUploadMode = false;
  const landing = document.getElementById('landing');
  const app = document.getElementById('app');
  if (landing) landing.style.display = 'flex';
  if (app) app.style.display = 'none';
  try { vid.pause(); } catch(e) {}
  vid.srcObject = null;
  if (vid.src && vid.src.startsWith('blob:')) {
    try { URL.revokeObjectURL(vid.src); } catch(e) {}
  }
  vid.src = '';
  const analyzeBtn = document.getElementById('analyzeUploadBtn');
  if (analyzeBtn) {
    analyzeBtn.style.display = 'none';
    analyzeBtn.disabled = false;
  }
  if (out) {
    out.style.color = '';
    out.innerText = '';
  }
}
