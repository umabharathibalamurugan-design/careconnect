let sosCoords=null,mediaRecorder=null,audioChunks=[],activeAlertId=null,soundStream=null,audioContext=null,analyser=null,soundTimer=null,voiceRecognition=null;
function getGPS(){return new Promise((resolve,reject)=>{if(!navigator.geolocation)return reject(new Error('GPS is not supported by this browser.'));navigator.geolocation.getCurrentPosition(p=>resolve(p.coords),e=>reject(new Error(e.message||'Unable to get GPS location.')),{enableHighAccuracy:true,timeout:10000,maximumAge:3000})})}
async function captureGPS(){sosCoords=await getGPS();document.getElementById('gps').textContent=`${sosCoords.latitude.toFixed(6)}, ${sosCoords.longitude.toFixed(6)} · ±${Math.round(sosCoords.accuracy||0)}m`;return sosCoords}
async function sendSOS(source='manual'){const btn=document.getElementById('activateSOS'),status=document.getElementById('sosStatus');btn.disabled=true;status.className='notice';status.textContent='Sending emergency alert…';try{if(!sosCoords)await captureGPS();const d=await CC.json('/api/response/sos/',{method:'POST',body:JSON.stringify({alert_type:document.getElementById('type').value,message:(document.getElementById('message').value||'Emergency SOS activated')+(source!=='manual'?` [Triggered by ${source}]`:''),latitude:sosCoords.latitude,longitude:sosCoords.longitude,response_window_minutes:2})});activeAlertId=d.alert_id;
status.className='notice success';
status.textContent=`SOS #${d.alert_id} sent successfully. ${d.notified_users||0} responders notified.`;
const mode=document.getElementById('emergencyModeStatus'); if(mode){mode.hidden=false;document.body.classList.add('emergency-active');document.getElementById('emergencyId').textContent='Incident #'+d.alert_id+' · ACTIVE';document.getElementById('emLocation').textContent='Sharing';document.getElementById('emAlerts').textContent=(d.notified_users||0)+' notified';document.getElementById('emGuardian').textContent=(d.notified_users||0)?'Notified':'Pending';document.getElementById('emSecurity').textContent=(d.notified_users||0)?'Notified':'Pending';document.getElementById('emResponder').textContent=d.smart_match?.responder_name||'Awaiting response';document.getElementById('emPolice').textContent='Standby';}
toast('SOS sent — responders notified');}catch(e){status.className='notice error';status.textContent=e.message;btn.disabled=false}}
async function toggleRecording(){const b=document.getElementById('recordBtn'),t=document.getElementById('recordText');if(mediaRecorder&&mediaRecorder.state==='recording'){mediaRecorder.stop();return}if(!navigator.mediaDevices?.getUserMedia){toast('Voice recording is not supported in this browser');return}try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});audioChunks=[];mediaRecorder=new MediaRecorder(stream);mediaRecorder.ondataavailable=e=>{if(e.data.size)audioChunks.push(e.data)};mediaRecorder.onstop=async()=>{stream.getTracks().forEach(x=>x.stop());t.textContent='Record voice';const blob=new Blob(audioChunks,{type:mediaRecorder.mimeType||'audio/webm'});if(activeAlertId){const fd=new FormData();fd.append('audio',blob,'incident-voice.webm');try{await CC.json(`/api/response/alerts/${activeAlertId}/audio/`,{method:'POST',body:fd});toast('Voice note sent to the incident')}catch(e){toast('Recording saved, but could not send it')}}else{toast('Voice recorded. Activate SOS first to attach it to an incident.')}};mediaRecorder.start();t.textContent='Stop recording';toast('Recording…')}catch(e){toast(e.message||'Microphone permission denied')}}
async function toggleSound(){const button=document.getElementById('soundBtn'),meter=document.getElementById('soundMeter'),status=document.getElementById('soundStatus');if(soundStream){stopSound();return}try{soundStream=await navigator.mediaDevices.getUserMedia({audio:true});audioContext=new (window.AudioContext||window.webkitAudioContext)();const source=audioContext.createMediaStreamSource(soundStream);analyser=audioContext.createAnalyser();analyser.fftSize=512;source.connect(analyser);const data=new Uint8Array(analyser.frequencyBinCount);meter.style.display='block';button.innerHTML='<span class="tool-icon">■</span>Stop detect';status.textContent='Listening for a sustained distress sound. Keep this page open.';let peaks=0;const check=()=>{if(!analyser)return;analyser.getByteTimeDomainData(data);let sum=0;for(const v of data){const n=(v-128)/128;sum+=n*n}const rms=Math.sqrt(sum/data.length);const level=Math.min(100,Math.round(rms*260));meter.firstElementChild.style.width=level+'%';if(rms>.34){peaks++;if(peaks>=3){stopSound();sendSOS('sound detection');return}}else peaks=Math.max(0,peaks-1);soundTimer=requestAnimationFrame(check)};check()}catch(e){status.textContent=e.message||'Microphone permission denied'}}
function stopSound(){if(soundTimer)cancelAnimationFrame(soundTimer);soundTimer=null;soundStream?.getTracks().forEach(x=>x.stop());soundStream=null;audioContext?.close();audioContext=null;analyser=null;document.getElementById('soundBtn').innerHTML='<span class="tool-icon">◉</span>Sound detect';document.getElementById('soundStatus').textContent='Sound detection stopped.'}
async function openNearbyPolice(){
  if(!sosCoords){try{await captureGPS()}catch(e){toast('Location is needed to find nearby police stations','error');return}}
  const q=`police station near ${sosCoords.latitude},${sosCoords.longitude}`;
  window.open('https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(q),'_blank');
}
async function refreshEmergencyState(){
  if(!activeAlertId)return;
  try{
    const [responses,updates]=await Promise.all([CC.json(`/api/response/alerts/${activeAlertId}/responses/`),CC.json(`/api/response/alerts/${activeAlertId}/updates/`)]);
    const rs=Array.isArray(responses)?responses:(responses.results||[]);
    const us=Array.isArray(updates)?updates:(updates.results||[]);
    const accepted=rs.find(x=>['accepted','on_way','arrived','completed'].includes(String(x.status)));
    const onWay=rs.find(x=>['on_way','arrived','completed'].includes(String(x.status)));
    const arrived=rs.find(x=>['arrived','completed'].includes(String(x.status)));
    const responder=document.getElementById('emResponder');
    if(responder)responder.textContent=arrived?'Arrived':onWay?'Responding':accepted?'Accepted':'Searching';
    const tl=document.getElementById('responseTimeline');
    if(tl){const status=arrived?'arrived':onWay?'on_way':accepted?'accepted':'notified';const idx={notified:1,accepted:2,on_way:3,arrived:4}[status]||1;tl.querySelectorAll('span').forEach((x,i)=>{x.classList.toggle('done',i<=idx);x.classList.toggle('current',i===idx)})}
    const last=us[us.length-1];
    if(last&&document.getElementById('emChatLast'))document.getElementById('emChatLast').textContent=`Latest update: ${last.detail||last.message||last.event||'Response updated'}`;
    if(document.getElementById('emPolice'))document.getElementById('emPolice').textContent=String(document.getElementById('emPolice').textContent||'Standby');
  }catch(e){}
}
async function sendEmergencyChat(){const input=document.getElementById('emChatInput');const msg=input?.value.trim();if(!activeAlertId||!msg)return;try{await CC.json(`/api/response/alerts/${activeAlertId}/chat/`,{method:'POST',body:JSON.stringify({message:msg})});input.value='';toast('Message sent to the response team','success');refreshEmergencyState()}catch(e){toast(e.message,'error')}}
async function escalateEmergency(){if(!activeAlertId)return;try{await CC.json(`/api/response/alerts/${activeAlertId}/escalate/`,{method:'POST',body:JSON.stringify({reason:'Resident requested emergency escalation'})});document.getElementById('emPolice').textContent='Escalated';toast('Emergency escalation recorded','success');refreshEmergencyState()}catch(e){toast(e.message,'error')}}

async function callPrimaryEmergencyContact(){
  try{
    const d=await CC.json('/api/');const items=Array.isArray(d)?d:(d.results||[]);const c=items.find(x=>x.is_primary&&x.phone_number)||items.find(x=>x.phone_number);
    if(c?.phone_number){location.href='tel:'+c.phone_number;toast('Calling '+c.name,'success');return}
    if(CC.user?.phone_number){location.href='tel:'+CC.user.phone_number;return}
    toast('Add a verified emergency contact first','error');
  }catch(e){toast(e.message,'error')}
}
function toggleVoiceRecognition(){
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;const btn=document.getElementById('voiceToTextBtn'),status=document.getElementById('voiceToTextStatus'),box=document.getElementById('message');
 if(!SR){toast('Voice-to-text is not supported in this browser. Try Chrome or Edge.','error');return}
 if(voiceRecognition){voiceRecognition.stop();return}
 voiceRecognition=new SR();voiceRecognition.lang=(document.documentElement.lang||'en-IN');voiceRecognition.interimResults=true;voiceRecognition.continuous=false;
 voiceRecognition.onstart=()=>{btn.textContent='⏹ Stop listening';status.textContent='Listening… speak your emergency message';};
 voiceRecognition.onresult=e=>{let text='';for(let i=e.resultIndex;i<e.results.length;i++)text+=e.results[i][0].transcript+' ';box.value=(box.value?box.value+' ':'')+text.trim();};
 voiceRecognition.onerror=e=>{status.textContent='Voice input: '+(e.error||'not available');toast('Voice input could not be completed','error');};
 voiceRecognition.onend=()=>{voiceRecognition=null;btn.textContent='🎙️ Speak message';status.textContent='Voice-to-text ready';};
 voiceRecognition.start();
}
let sosPressTimer=null;
function setupLongPressSOS(){const b=document.getElementById('activateSOS');if(!b)return;const start=()=>{clearTimeout(sosPressTimer);sosPressTimer=setTimeout(()=>sendSOS('long press'),900)};const cancel=()=>clearTimeout(sosPressTimer);b.addEventListener('pointerdown',start);['pointerup','pointerleave','pointercancel'].forEach(e=>b.addEventListener(e,cancel));}
document.addEventListener('DOMContentLoaded',()=>{if(!CC.requireLogin())return;document.getElementById('activateSOS').onclick=()=>sendSOS('manual');setupLongPressSOS();document.getElementById('callBtn').onclick=callPrimaryEmergencyContact;document.getElementById('recordBtn').onclick=toggleRecording;document.getElementById('soundBtn').onclick=toggleSound;document.getElementById('voiceToTextBtn')?.addEventListener('click',toggleVoiceRecognition);
document.getElementById('emCall')?.addEventListener('click',()=>document.getElementById('callBtn').click());
document.getElementById('emLocationBtn')?.addEventListener('click',()=>{if(sosCoords)window.open(`https://www.google.com/maps?q=${sosCoords.latitude},${sosCoords.longitude}`,'_blank')});
document.getElementById('emPoliceBtn')?.addEventListener('click',openNearbyPolice);
document.getElementById('nearbyPoliceBtn')?.addEventListener('click',openNearbyPolice);
document.getElementById('emEscalateBtn')?.addEventListener('click',escalateEmergency);
document.getElementById('emChatSend')?.addEventListener('click',sendEmergencyChat);
document.getElementById('emChatInput')?.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();sendEmergencyChat()}});
document.getElementById('emSafe')?.addEventListener('click',async()=>{if(!activeAlertId)return;try{await CC.json(`/api/response/alerts/${activeAlertId}/respond/`,{method:'POST',body:JSON.stringify({action:'completed',closure_note:'Resident confirmed they are safe.'})});toast('Safety confirmed and incident closed','success');document.getElementById('emergencyModeStatus').hidden=true;document.body.classList.remove('emergency-active');activeAlertId=null;document.getElementById('sosStatus').className='notice success';document.getElementById('sosStatus').textContent='Incident closed — you confirmed you are safe.';}catch(e){toast(e.message,'error')}});
setInterval(refreshEmergencyState,4000);});
