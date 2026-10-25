// result.js - Fixed version for LIP-READ

const videoEl = document.getElementById('resultVideo');
const predEl = document.getElementById('predictionText');
const durEl = document.getElementById('durationText');
const videoStatusEl = document.getElementById('videoStatus');
const copyBtn = document.getElementById('copyBtn');
const speakBtn = document.getElementById('speakBtn');
const translateBtn = document.getElementById('translateBtn');
const backHomeBtn = document.getElementById('backHomeBtn');
const translatedEl = document.getElementById('translatedText');

// Load text from localStorage
function loadResult() {
  let text = '';
  let duration = '';
  try {
    text = localStorage.getItem('liply_text') || '';
    duration = localStorage.getItem('liply_duration') || '';
  } catch(e) {}

  if (!text) {
    predEl.textContent = 'No prediction found. Please upload a video again from the home page.';
    predEl.style.color = '#ef4444';
    if (durEl) durEl.textContent = 'Duration: -';
    return;
  }

  predEl.textContent = text;
  predEl.style.color = '#111';
  if (durEl) durEl.textContent = duration ? `Duration: ${duration}` : 'Duration: -';
}

async function loadVideoFromDB() {
  if (!videoEl) return;
  try {
    const req = indexedDB.open('liply', 1);
    req.onsuccess = () => {
      const db = req.result;
      const tx = db.transaction('videos', 'readonly');
      const store = tx.objectStore('videos');
      const getReq = store.get('last');
      getReq.onsuccess = () => {
        const blob = getReq.result;
        if (blob) {
          const url = URL.createObjectURL(blob);
          videoEl.src = url;
          videoEl.onloadeddata = () => {
            if (videoStatusEl) videoStatusEl.textContent = `Video loaded: ${blob.type || 'video'} | ${(blob.size/1024/1024).toFixed(2)} MB`;
          };
          videoEl.onerror = () => {
            if (videoStatusEl) videoStatusEl.textContent = 'Video format not supported by browser for preview, but prediction is valid.';
          };
        } else {
          if (videoStatusEl) videoStatusEl.textContent = 'No video found in storage. Prediction is still available.';
        }
        db.close();
      };
      getReq.onerror = () => {
        if (videoStatusEl) videoStatusEl.textContent = 'Could not load video from storage.';
        db.close();
      };
    };
    req.onerror = () => {
      if (videoStatusEl) videoStatusEl.textContent = 'Could not open video storage.';
    };
  } catch(e) {
    if (videoStatusEl) videoStatusEl.textContent = 'Video replay not available.';
  }
}

if (copyBtn) {
  copyBtn.onclick = async () => {
    const txt = predEl.textContent || '';
    try {
      await navigator.clipboard.writeText(txt);
      const old = copyBtn.textContent;
      copyBtn.textContent = 'Copied!';
      setTimeout(()=> copyBtn.textContent = old, 1500);
    } catch(e) {
      alert('Copy failed: ' + txt);
    }
  };
}

if (speakBtn) {
  speakBtn.onclick = () => {
    const txt = predEl.textContent || '';
    if (!txt) return;
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(txt);
      utter.lang = 'en-US';
      window.speechSynthesis.speak(utter);
    } else {
      alert('Speech synthesis not supported in this browser.');
    }
  };
}

if (translateBtn) {
  translateBtn.onclick = async () => {
    const txt = predEl.textContent || '';
    if (!txt) return;
    const original = translateBtn.textContent;
    translateBtn.textContent = 'Translating...';
    translateBtn.disabled = true;
    try {
      // Using MyMemory free API (no key needed)
      const res = await fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(txt)}&langpair=en|hi`);
      const data = await res.json();
      let translated = data?.responseData?.translatedText || '';
      if (!translated || translated.toLowerCase().includes('mymemory')) {
        throw new Error('Translation failed');
      }
      if (translatedEl) {
        translatedEl.textContent = 'Hindi: ' + translated;
        translatedEl.style.display = 'block';
      }
      // Speak Hindi if possible
      if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(translated);
        utter.lang = 'hi-IN';
        window.speechSynthesis.speak(utter);
      }
    } catch(e) {
      if (translatedEl) {
        translatedEl.textContent = 'Translation failed. Please check internet connection.';
        translatedEl.style.display = 'block';
      }
    } finally {
      translateBtn.textContent = original;
      translateBtn.disabled = false;
    }
  };
}

if (backHomeBtn) {
  backHomeBtn.onclick = () => {
    window.location.href = 'index.html';
  };
}

// Init
loadResult();
loadVideoFromDB();
