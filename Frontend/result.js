let text='No data';
try{ text=localStorage.getItem('liply_text')||'No data'; }catch(e){}

document.getElementById('textBox').innerText = text;

// load the analysed clip (saved by index.html in IndexedDB) so it can be replayed here
(function loadVideo(){
  const player=document.getElementById('resultVideo');
  const note=document.getElementById('videoNote');
  const replay=document.getElementById('replayBtn');

  function show(blob){
    if(!blob){ note.innerText='No clip saved for replay.'; return; }
    player.src=URL.createObjectURL(blob);
    replay.style.display='inline-block';
    player.onerror=()=>{ note.innerText='⚠️ This browser cannot play this video format.'; };
  }
  replay.onclick=()=>{ player.currentTime=0; player.play().catch(()=>{}); };

  try{
    const req=indexedDB.open('liply',2);
    req.onupgradeneeded=()=>{
      const d=req.result;
      if(!d.objectStoreNames.contains('videos')) d.createObjectStore('videos');
      if(!d.objectStoreNames.contains('clips')) d.createObjectStore('clips',{keyPath:'id',autoIncrement:true});
    };
    req.onerror=()=>show(null);
    req.onsuccess=()=>{
      const db=req.result;
      const get=db.transaction('videos','readonly').objectStore('videos').get('last');
      get.onsuccess=()=>{
        if(get.result){ show(get.result); db.close(); return; }
        // fallback: newest clip in My Clips
        const all=db.transaction('clips','readonly').objectStore('clips').getAll();
        all.onsuccess=()=>{
          const list=(all.result||[]).sort((x,y)=>y.date-x.date);
          show(list.length ? list[0].blob : null);
          db.close();
        };
      };
    };
  }catch(e){ show(null); }
})();

document.getElementById('startTranslateBtn').onclick=async()=>{
  const btn=document.getElementById('startTranslateBtn');
  const to=document.getElementById('toLang').value;
  const card=document.getElementById('transCard');
  const box=document.getElementById('translatedBox');
  
  btn.innerText='⏳ Translating...';
  card.style.display='block';
  box.innerText='Translating...';
  
  if(to==='en'){ box.innerText=text; btn.innerText='✅ Translation Done'; return; }  // already English
  try{
    const res=await fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=en|${to}`);
    const data=await res.json();
    box.innerText=data.responseData.translatedText;
  }catch(e){
    box.innerText='Translation is unavailable right now. Check your internet connection.';
  }
  btn.innerText='✅ Translation Done';
};

function speakText(){
  const t=document.getElementById('transCard').style.display==='block' ? document.getElementById('translatedBox').innerText : document.getElementById('textBox').innerText;
  speechSynthesis.speak(new SpeechSynthesisUtterance(t));
}

function copyText(){
  const t=document.getElementById('transCard').style.display==='block' ? document.getElementById('translatedBox').innerText : document.getElementById('textBox').innerText;
  navigator.clipboard.writeText(t);
  alert('Copied!');
}