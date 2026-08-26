let sosCoords=null,mediaRecorder=null,audioChunks=[],activeAlertId=null,soundStream=null,audioContext=null,analyser=null,soundTimer=null,voiceRecognition=null;

function getGPS(){
  return new Promise((resolve,reject)=>{
    if(!window.isSecureContext){
      reject(new Error(
        'GPS requires a secure HTTPS connection. Please open CareConnect using https://umabharathi.pythonanywhere.com/'
      ));
      return;
    }

    if(!navigator.geolocation){
      reject(new Error(
        'GPS is not available in this browser. Please use Chrome or Edge and enable Location permission.'
      ));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      position=>{
        resolve(position.coords);
      },
      error=>{
        let message='Unable to get your GPS location.';

        switch(error.code){
          case error.PERMISSION_DENIED:
            message='Location permission was denied. Please allow Location access for CareConnect in your browser settings.';
            break;

          case error.POSITION_UNAVAILABLE:
            message='Your current location is unavailable. Turn on GPS/Location services and try again.';
            break;

          case error.TIMEOUT:
            message='GPS location request timed out. Please try again in an open area.';
            break;
        }

        reject(new Error(message));
      },
      {
        enableHighAccuracy:true,
        timeout:20000,
        maximumAge:0
      }
    );
  });
}

async function captureGPS(){
  sosCoords=await getGPS();

  const gps=document.getElementById('gps');

  if(gps){
    gps.textContent=
      `${sosCoords.latitude.toFixed(6)}, ${sosCoords.longitude.toFixed(6)} · ±${Math.round(sosCoords.accuracy||0)}m`;
  }

  return sosCoords;
}

async function sendSOS(source='manual'){
  const btn=document.getElementById('activateSOS');
  const status=document.getElementById('sosStatus');

  if(!btn||!status)return;

  btn.disabled=true;
  status.className='notice';
  status.textContent='Getting your location…';

  try{
    if(!sosCoords){
      await captureGPS();
    }

    status.textContent='Sending emergency alert…';

    const d=await CC.json(
      '/api/response/sos/',
      {
        method:'POST',
        body:JSON.stringify({
          alert_type:document.getElementById('type')?.value||'Personal Safety',
          message:
            (document.getElementById('message')?.value||'Emergency SOS activated')+
            (source!=='manual'?` [Triggered by ${source}]`:''),
          latitude:sosCoords.latitude,
          longitude:sosCoords.longitude,
          response_window_minutes:2
        })
      }
    );

    activeAlertId=d.alert_id;

    status.className='notice success';

    status.textContent=
      `SOS #${d.alert_id} sent successfully. ${d.notified_users||0} responders notified.`;

    const mode=document.getElementById('emergencyModeStatus');

    if(mode){
      mode.hidden=false;
      document.body.classList.add('emergency-active');

      const incident=document.getElementById('emergencyId');
      const location=document.getElementById('emLocation');
      const alerts=document.getElementById('emAlerts');
      const guardian=document.getElementById('emGuardian');
      const security=document.getElementById('emSecurity');
      const responder=document.getElementById('emResponder');
      const police=document.getElementById('emPolice');

      if(incident)incident.textContent='Incident #'+d.alert_id+' · ACTIVE';
      if(location)location.textContent='Sharing';
      if(alerts)alerts.textContent=(d.notified_users||0)+' notified';
      if(guardian)guardian.textContent=(d.notified_users||0)?'Notified':'Pending';
      if(security)security.textContent=(d.notified_users||0)?'Notified':'Pending';
      if(responder)responder.textContent=d.smart_match?.responder_name||'Awaiting response';
      if(police)police.textContent='Standby';
    }

    toast('SOS sent — responders notified','success');

  }catch(e){
    status.className='notice error';
    status.textContent=e.message||'Unable to send SOS.';
    btn.disabled=false;
  }
}

async function toggleRecording(){
  const b=document.getElementById('recordBtn');
  const t=document.getElementById('recordText');

  if(mediaRecorder&&mediaRecorder.state==='recording'){
    mediaRecorder.stop();
    return;
  }

  if(!window.isSecureContext){
    toast('Voice recording requires a secure HTTPS connection.','error');
    return;
  }

  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    toast(
      'This mobile browser does not support microphone recording. Try Chrome or Edge.',
      'error'
    );
    return;
  }

  try{
    const stream=await navigator.mediaDevices.getUserMedia({audio:true});

    audioChunks=[];
    mediaRecorder=new MediaRecorder(stream);

    mediaRecorder.ondataavailable=e=>{
      if(e.data.size){
        audioChunks.push(e.data);
      }
    };

    mediaRecorder.onstop=async()=>{
      stream.getTracks().forEach(x=>x.stop());

      if(t)t.textContent='Record voice';

      const blob=new Blob(
        audioChunks,
        {type:mediaRecorder.mimeType||'audio/webm'}
      );

      if(activeAlertId){
        const fd=new FormData();

        fd.append(
          'audio',
          blob,
          'incident-voice.webm'
        );

        try{
          await CC.json(
            `/api/response/alerts/${activeAlertId}/audio/`,
            {
              method:'POST',
              body:fd
            }
          );

          toast('Voice note sent to the incident','success');

        }catch(e){
          toast(
            'Recording completed, but could not send it.',
            'error'
          );
        }

      }else{
        toast(
          'Voice recorded. Activate SOS first to attach it to an incident.',
          'success'
        );
      }
    };

    mediaRecorder.start();

    if(t)t.textContent='Stop recording';

    toast('Recording…','success');

  }catch(e){

    let message='Microphone permission was denied.';

    if(e.name==='NotAllowedError'){
      message=
        'Microphone permission was denied. Allow microphone access for CareConnect.';
    }else if(e.name==='NotFoundError'){
      message='No microphone was found on this device.';
    }else if(e.name==='NotReadableError'){
      message=
        'The microphone is currently being used by another application.';
    }

    toast(message,'error');
  }
}

async function toggleSound(){
  const button=document.getElementById('soundBtn');
  const meter=document.getElementById('soundMeter');
  const status=document.getElementById('soundStatus');

  if(soundStream){
    stopSound();
    return;
  }

  if(!window.isSecureContext){
    if(status){
      status.textContent='Sound detection requires HTTPS.';
    }
    return;
  }

  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    if(status){
      status.textContent=
        'Sound detection is not supported in this mobile browser.';
    }
    return;
  }

  try{
    soundStream=await navigator.mediaDevices.getUserMedia({
      audio:true
    });

    const AudioCtx=window.AudioContext||window.webkitAudioContext;

    if(!AudioCtx){
      throw new Error('Audio detection is not supported in this browser.');
    }

    audioContext=new AudioCtx();

    const source=
      audioContext.createMediaStreamSource(soundStream);

    analyser=audioContext.createAnalyser();
    analyser.fftSize=512;

    source.connect(analyser);

    const data=
      new Uint8Array(analyser.frequencyBinCount);

    if(meter){
      meter.style.display='block';
    }

    if(button){
      button.innerHTML=
        '<span class="tool-icon">■</span>Stop detect';
    }

    if(status){
      status.textContent=
        'Listening for a sustained distress sound. Keep this page open.';
    }

    let peaks=0;

    const check=()=>{
      if(!analyser)return;

      analyser.getByteTimeDomainData(data);

      let sum=0;

      for(const v of data){
        const n=(v-128)/128;
        sum+=n*n;
      }

      const rms=Math.sqrt(sum/data.length);
      const level=Math.min(
        100,
        Math.round(rms*260)
      );

      if(meter?.firstElementChild){
        meter.firstElementChild.style.width=
          level+'%';
      }

      if(rms>.34){
        peaks++;

        if(peaks>=3){
          stopSound();
          sendSOS('sound detection');
          return;
        }
      }else{
        peaks=Math.max(0,peaks-1);
      }

      soundTimer=requestAnimationFrame(check);
    };

    check();

  }catch(e){
    if(status){
      status.textContent=
        e.message||'Microphone permission denied.';
    }
  }
}

function stopSound(){
  if(soundTimer){
    cancelAnimationFrame(soundTimer);
  }

  soundTimer=null;

  soundStream?.getTracks().forEach(
    x=>x.stop()
  );

  soundStream=null;

  audioContext?.close();

  audioContext=null;
  analyser=null;

  const button=document.getElementById('soundBtn');
  const status=document.getElementById('soundStatus');

  if(button){
    button.innerHTML=
      '<span class="tool-icon">◉</span>Sound detect';
  }

  if(status){
    status.textContent=
      'Sound detection stopped.';
  }
}

async function openNearbyPolice(){
  if(!sosCoords){
    try{
      await captureGPS();
    }catch(e){
      toast(
        e.message||
        'Location is needed to find nearby police stations.',
        'error'
      );
      return;
    }
  }

  const q=
    `police station near ${sosCoords.latitude},${sosCoords.longitude}`;

  window.open(
    'https://www.google.com/maps/search/?api=1&query='+
    encodeURIComponent(q),
    '_blank'
  );
}

async function refreshEmergencyState(){
  if(!activeAlertId)return;

  try{
    const [responses,updates]=await Promise.all([
      CC.json(
        `/api/response/alerts/${activeAlertId}/responses/`
      ),
      CC.json(
        `/api/response/alerts/${activeAlertId}/updates/`
      )
    ]);

    const rs=
      Array.isArray(responses)
        ?responses
        :(responses.results||[]);

    const us=
      Array.isArray(updates)
        ?updates
        :(updates.results||[]);

    const accepted=
      rs.find(x=>[
        'accepted',
        'on_way',
        'arrived',
        'completed'
      ].includes(String(x.status)));

    const onWay=
      rs.find(x=>[
        'on_way',
        'arrived',
        'completed'
      ].includes(String(x.status)));

    const arrived=
      rs.find(x=>[
        'arrived',
        'completed'
      ].includes(String(x.status)));

    const responder=
      document.getElementById('emResponder');

    if(responder){
      responder.textContent=
        arrived
          ?'Arrived'
          :onWay
            ?'Responding'
            :accepted
              ?'Accepted'
              :'Searching';
    }

    const tl=
      document.getElementById('responseTimeline');

    if(tl){
      const state=
        arrived
          ?'arrived'
          :onWay
            ?'on_way'
            :accepted
              ?'accepted'
              :'notified';

      const idx={
        notified:1,
        accepted:2,
        on_way:3,
        arrived:4
      }[state]||1;

      tl.querySelectorAll('span').forEach(
        (x,i)=>{
          x.classList.toggle('done',i<=idx);
          x.classList.toggle('current',i===idx);
        }
      );
    }

    const last=us[us.length-1];

    const chatLast=
      document.getElementById('emChatLast');

    if(last&&chatLast){
      chatLast.textContent=
        `Latest update: ${
          last.detail||
          last.message||
          last.event||
          'Response updated'
        }`;
    }

  }catch(e){
    // Keep emergency UI alive even if status refresh fails.
  }
}

async function sendEmergencyChat(){
  const input=
    document.getElementById('emChatInput');

  const msg=input?.value.trim();

  if(!activeAlertId||!msg)return;

  try{
    await CC.json(
      `/api/response/alerts/${activeAlertId}/chat/`,
      {
        method:'POST',
        body:JSON.stringify({
          message:msg
        })
      }
    );

    input.value='';

    toast(
      'Message sent to the response team',
      'success'
    );

    refreshEmergencyState();

  }catch(e){
    toast(e.message,'error');
  }
}

async function escalateEmergency(){
  if(!activeAlertId)return;

  try{
    await CC.json(
      `/api/response/alerts/${activeAlertId}/escalate/`,
      {
        method:'POST',
        body:JSON.stringify({
          reason:'Resident requested emergency escalation'
        })
      }
    );

    const police=
      document.getElementById('emPolice');

    if(police){
      police.textContent='Escalated';
    }

    toast(
      'Emergency escalation recorded',
      'success'
    );

    refreshEmergencyState();

  }catch(e){
    toast(e.message,'error');
  }
}

async function callPrimaryEmergencyContact(){
  try{
    const d=await CC.json('/api/');

    const items=
      Array.isArray(d)
        ?d
        :(d.results||[]);

    const c=
      items.find(
        x=>x.is_primary&&x.phone_number
      )||
      items.find(
        x=>x.phone_number
      );

    if(c?.phone_number){
      location.href='tel:'+c.phone_number;

      toast(
        'Calling '+c.name,
        'success'
      );

      return;
    }

    if(CC.user?.phone_number){
      location.href=
        'tel:'+CC.user.phone_number;
      return;
    }

    toast(
      'Add a verified emergency contact first',
      'error'
    );

  }catch(e){
    toast(e.message,'error');
  }
}

function toggleVoiceRecognition(){
  const SR=
    window.SpeechRecognition||
    window.webkitSpeechRecognition;

  const btn=
    document.getElementById('voiceToTextBtn');

  const status=
    document.getElementById('voiceToTextStatus');

  const box=
    document.getElementById('message');

  if(!SR){
    toast(
      'Voice-to-text is not supported in this browser. Try Chrome.',
      'error'
    );
    return;
  }

  if(voiceRecognition){
    voiceRecognition.stop();
    return;
  }

  voiceRecognition=new SR();

  voiceRecognition.lang=
    document.documentElement.lang||
    'en-IN';

  voiceRecognition.interimResults=true;
  voiceRecognition.continuous=false;

  voiceRecognition.onstart=()=>{
    if(btn)btn.textContent='⏹ Stop listening';

    if(status){
      status.textContent=
        'Listening… speak your emergency message';
    }
  };

  voiceRecognition.onresult=e=>{
    let text='';

    for(
      let i=e.resultIndex;
      i<e.results.length;
      i++
    ){
      text+=
        e.results[i][0].transcript+' ';
    }

    if(box){
      box.value=
        (box.value?box.value+' ':'')+
        text.trim();
    }
  };

  voiceRecognition.onerror=e=>{
    if(status){
      status.textContent=
        'Voice input: '+(e.error||'not available');
    }

    toast(
      'Voice input could not be completed',
      'error'
    );
  };

  voiceRecognition.onend=()=>{
    voiceRecognition=null;

    if(btn){
      btn.textContent='🎙️ Speak message';
    }

    if(status){
      status.textContent=
        'Voice-to-text ready';
    }
  };

  try{
    voiceRecognition.start();
  }catch(e){
    voiceRecognition=null;

    toast(
      'Voice input could not be started.',
      'error'
    );
  }
}

let sosPressTimer=null;

function setupLongPressSOS(){
  const b=
    document.getElementById('activateSOS');

  if(!b)return;

  const start=()=>{
    clearTimeout(sosPressTimer);

    sosPressTimer=
      setTimeout(
        ()=>{
          sendSOS('long press');
        },
        900
      );
  };

  const cancel=()=>{
    clearTimeout(sosPressTimer);
  };

  b.addEventListener(
    'pointerdown',
    start
  );

  [
    'pointerup',
    'pointerleave',
    'pointercancel'
  ].forEach(
    e=>b.addEventListener(e,cancel)
  );
}

document.addEventListener(
  'DOMContentLoaded',
  ()=>{
    if(!CC.requireLogin())return;

    const activateSOS=
      document.getElementById('activateSOS');

    if(activateSOS){
      activateSOS.onclick=
        ()=>sendSOS('manual');

      setupLongPressSOS();
    }

    document.getElementById('callBtn')?.addEventListener(
      'click',
      callPrimaryEmergencyContact
    );

    document.getElementById('recordBtn')?.addEventListener(
      'click',
      toggleRecording
    );

    document.getElementById('soundBtn')?.addEventListener(
      'click',
      toggleSound
    );

    document.getElementById('voiceToTextBtn')?.addEventListener(
      'click',
      toggleVoiceRecognition
    );

    document.getElementById('emCall')?.addEventListener(
      'click',
      ()=>{
        document.getElementById('callBtn')?.click();
      }
    );

    document.getElementById('emLocationBtn')?.addEventListener(
      'click',
      ()=>{
        if(sosCoords){
          window.open(
            `https://www.google.com/maps?q=${sosCoords.latitude},${sosCoords.longitude}`,
            '_blank'
          );
        }
      }
    );

    document.getElementById('emPoliceBtn')?.addEventListener(
      'click',
      openNearbyPolice
    );

    document.getElementById('nearbyPoliceBtn')?.addEventListener(
      'click',
      openNearbyPolice
    );

    document.getElementById('emEscalateBtn')?.addEventListener(
      'click',
      escalateEmergency
    );

    document.getElementById('emChatSend')?.addEventListener(
      'click',
      sendEmergencyChat
    );

    document.getElementById('emChatInput')?.addEventListener(
      'keydown',
      e=>{
        if(e.key==='Enter'){
          e.preventDefault();
          sendEmergencyChat();
        }
      }
    );

    document.getElementById('emSafe')?.addEventListener(
      'click',
      async()=>{
        if(!activeAlertId)return;

        try{
          await CC.json(
            `/api/response/alerts/${activeAlertId}/respond/`,
            {
              method:'POST',
              body:JSON.stringify({
                action:'completed',
                closure_note:
                  'Resident confirmed they are safe.'
              })
            }
          );

          toast(
            'Safety confirmed and incident closed',
            'success'
          );

          const mode=
            document.getElementById('emergencyModeStatus');

          if(mode){
            mode.hidden=true;
          }

          document.body.classList.remove(
            'emergency-active'
          );

          activeAlertId=null;

          const sosStatus=
            document.getElementById('sosStatus');

          if(sosStatus){
            sosStatus.className=
              'notice success';

            sosStatus.textContent=
              'Incident closed — you confirmed you are safe.';
          }

          const activate=
            document.getElementById('activateSOS');

          if(activate){
            activate.disabled=false;
          }

        }catch(e){
          toast(
            e.message,
            'error'
          );
        }
      }
    );

    setInterval(
      refreshEmergencyState,
      4000
    );
  }
);