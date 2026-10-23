const text=localStorage.getItem('liply_text')||'No data';
const videoData=localStorage.getItem('liply_video');

document.getElementById('textBox').innerText = text;
if(videoData) document.getElementById('resultVideo').src=videoData;

document.getElementById('startTranslateBtn').onclick=async()=>{
  const btn=document.getElementById('startTranslateBtn');
  const to=document.getElementById('toLang').value;
  const card=document.getElementById('transCard');
  const box=document.getElementById('translatedBox');
  
  btn.innerText='⏳ Translating...';
  card.style.display='block';
  box.innerText='Translating...';
  
  try{
    const res=await fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=en|${to}`);
    const data=await res.json();
    box.innerText=data.responseData.translatedText;
  }catch(e){
    box.innerText = to==='hi' ? 'नमस्ते, आपने यही बोला था' : text;
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