// Address of the Flask backend (backend/app.py). Change it if the API runs elsewhere.
const API_URL='http://127.0.0.1:5000/predict';

let stream, recorder, chunks=[], lipData=[], faceMesh, camera;
let isRecording=false, isUploadMode=false, uploadedFile=null;

const vid=document.getElementById('previewVideo');
const img=document.getElementById('imgPreview');
const out=document.getElementById('output');
const overlay=document.getElementById('overlay');
const ctx=overlay.getContext('2d');

setTimeout(()=>{
  document.getElementById('loading').style.display='none';
  document.getElementById('landing').style.display='flex';
},1000);

document.getElementById('uploadBtn').onclick=()=>document.getElementById('fileInput').click();
document.getElementById('backBtn').onclick=()=>goHome();
document.getElementById('fileInput').onchange=e=>{ if(e.target.files[0]) showFile(e.target.files[0]); };
document.getElementById('dropZone').onclick=()=>document.getElementById('fileInput').click();

function showFile(file){
  document.getElementById('landing').style.display='none';
  document.getElementById('app').style.display='flex';
  uploadedFile=file;
  isUploadMode=true;
  lipData=[];
  const url=URL.createObjectURL(file);
  if(!file.type.startsWith('video')){
    out.innerText='Please upload a video file (mp4, webm, avi or mov).';
    document.getElementById('analyzeUploadBtn').style.display='none';
    uploadedFile=null; isUploadMode=false;
  } else {
    vid.srcObject=null;
    vid.src=url; vid.style.display='block'; img.style.display='none';
    vid.loop=false; vid.muted=true;
    document.getElementById('recStart').style.display='none';
    document.getElementById('recStop').style.display='none';
    document.getElementById('analyzeUploadBtn').style.display='inline-block';
    out.innerText='📁 Video Uploaded - Ab Analyze Button Dabao Lips Ke Liye';
    vid.onloadedmetadata=()=>{
      overlay.width=vid.videoWidth; overlay.height=vid.videoHeight;
      startLipTrackingForUpload();
      vid.play().catch(()=>{});   // play only after the onplay handler exists
    };
  }
}

async function startLive(){
  document.getElementById('landing').style.display='none';
  document.getElementById('app').style.display='flex';
  isUploadMode=false; lipData=[];
  try{
    stream=await navigator.mediaDevices.getUserMedia({video:true, audio:false});
    vid.srcObject=stream; vid.style.display='block'; img.style.display='none';
    await vid.play();
    document.getElementById('recStart').style.display='inline-block';
    document.getElementById('analyzeUploadBtn').style.display='none';
    out.innerText='👄 Lips Detect Ho Rahe Hain... Muh hilao';
    startLipTracking();
  }catch(e){ out.innerText='❌ '+e.message; }
}
document.getElementById('liveBtn').onclick=startLive;

function startLipTracking(){
  faceMesh=new FaceMesh({locateFile:(file)=>`https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`});
  faceMesh.setOptions({maxNumFaces:1, refineLandmarks:true, minDetectionConfidence:0.5, minTrackingConfidence:0.5});
  faceMesh.onResults(onFaceResults);
  camera=new Camera(vid,{
    onFrame:async()=>{ await faceMesh.send({image:vid}); },
    width:640, height:480
  });
  camera.start();
}

function startLipTrackingForUpload(){
  faceMesh=new FaceMesh({locateFile:(file)=>`https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`});
  faceMesh.setOptions({maxNumFaces:1, refineLandmarks:true, minDetectionConfidence:0.5, minTrackingConfidence:0.5});
  faceMesh.onResults(onFaceResults);
  // uploaded video ke har frame ko process karo
  async function processFrame(){
    if(vid.paused || vid.ended || !isUploadMode) return;
    await faceMesh.send({image:vid});
    requestAnimationFrame(processFrame);
  }
  vid.onplay=()=>{ lipData=[]; processFrame(); };
}

function onFaceResults(results){
  if(!overlay.width) { overlay.width=vid.videoWidth; overlay.height=vid.videoHeight; }
  ctx.clearRect(0,0,overlay.width,overlay.height);
  if(results.multiFaceLandmarks && results.multiFaceLandmarks[0]){
    const landmarks=results.multiFaceLandmarks[0];
    const lipsIndices=[61,146,91,181,84,17,314,405,321,375,291,13,14];
    ctx.fillStyle='#2563eb';
    lipsIndices.forEach(i=>{
      const p=landmarks[i];
      ctx.beginPath();
      ctx.arc(p.x*overlay.width, p.y*overlay.height, 2.5, 0, 2*Math.PI);
      ctx.fill();
    });
    const upper=landmarks[13], lower=landmarks[14];
    const dist=Math.abs(upper.y-lower.y);
    lipData.push(dist);
    if(isUploadMode){
      out.innerText=`🔍 Upload Video Lips Tracking... Frames: ${lipData.length} | Open: ${dist.toFixed(4)}`;
    } else if(!isRecording){
      out.style.color='';
      out.innerText=dist>0.025 ? '👄 Mouth open' : '👄 Face detected';
    }
  }
}

function startRec(){
  if(!stream){ alert('Turn on the live camera first.'); return; }
  chunks=[]; lipData=[]; isRecording=true;
  recorder=new MediaRecorder(stream);
  recorder.ondataavailable=e=>{ if(e.data.size>0) chunks.push(e.data); };
  recorder.onstop=()=>{
    const blob=new Blob(chunks,{type:'video/webm'});
    finishWithPrediction(blob, 'clip.webm', document.getElementById('timer').innerText);
  };
  recorder.start();
  document.getElementById('recStart').style.display='none';
  document.getElementById('recStop').style.display='inline-block';
  out.innerText='🔴 Lips Recording... bina awaz ke bhi chalega';
  let s=0; window.t=setInterval(()=>{ s++; document.getElementById('timer').innerText=s+' sec'; },1000);
}

function stopRec(){
  if(!isRecording) return;
  isRecording=false;
  recorder.stop();
  clearInterval(window.t);
  document.getElementById('recStop').style.display='none';
  out.innerText='Processing...';
}

function analyzeUploadedVideo(){
  if(!uploadedFile){ alert('Please upload a video first.'); return; }
  finishWithPrediction(uploadedFile, uploadedFile.name, Math.floor(vid.duration||0)+' sec');
}

// Sends the clip to the Flask backend, saves the real answer, then opens the result page.
async function finishWithPrediction(blob, filename, duration){
  out.style.color='';
  out.innerText='⏳ Reading lips... this can take a few seconds';
  document.getElementById('analyzeUploadBtn').disabled=true;
  let text;
  try{
    const form=new FormData();
    form.append('video', blob, filename);
    const res=await fetch(API_URL,{method:'POST',body:form});
    const data=await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.error || ('Server error '+res.status));
    text=(data.prediction||'').trim() || '(no words recognised)';
  }catch(e){
    const msg = (e instanceof TypeError)
      ? 'Cannot reach the backend. Start it with "python app.py" in the backend folder.'
      : e.message;
    out.style.color='#ef4444';
    out.innerText='❌ '+msg;
    document.getElementById('analyzeUploadBtn').disabled=false;
    if(!isUploadMode) document.getElementById('recStart').style.display='inline-block';
    return;
  }
  try{
    localStorage.setItem('liply_text', text);
    localStorage.setItem('liply_duration', duration);
  }catch(e){}
  // The video goes into IndexedDB (room for large files); the result page works even if this fails.
  try{ await saveVideo(blob); }catch(e){}
  window.location.href='result.html';
}

// ---- tiny IndexedDB helper: keeps the last clip so result.html can replay it ----
function openVideoDB(){
  return new Promise((resolve,reject)=>{
    const req=indexedDB.open('liply',1);
    req.onupgradeneeded=()=>req.result.createObjectStore('videos');
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error);
  });
}
async function saveVideo(blob){
  const db=await openVideoDB();
  await new Promise((resolve,reject)=>{
    const tx=db.transaction('videos','readwrite');
    tx.objectStore('videos').put(blob,'last');
    tx.oncomplete=resolve; tx.onerror=()=>reject(tx.error);
  });
  db.close();
}

document.getElementById('recStart').onclick=startRec;
document.getElementById('recStop').onclick=stopRec;
document.getElementById('analyzeUploadBtn').onclick=analyzeUploadedVideo;

function goHome(){
  if(stream) stream.getTracks().forEach(t=>t.stop());
  if(camera) camera.stop();
  isUploadMode=false;
  document.getElementById('landing').style.display='flex';
  document.getElementById('app').style.display='none';
  vid.pause(); vid.srcObject=null;
  document.getElementById('analyzeUploadBtn').style.display='none';
  document.getElementById('analyzeUploadBtn').disabled=false;
  out.style.color='';
}