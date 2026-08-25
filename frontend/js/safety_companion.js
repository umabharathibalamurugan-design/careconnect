(() => {
  const panel = document.getElementById('safetyCompanionPanel');
  const user = CC.user || {};
  if (!panel || String(user.role || '').toLowerCase() !== 'resident') return;
  panel.style.display = 'block';

  let profile = null;
  let silentPresses = [];
  let wellnessId = null;

  const api = (url, opts={}) => CC.json(url, opts);
  const jsonBody = body => ({method:'POST', body:JSON.stringify(body)});

  async function loadProfile(){
    try {
      profile = await api('/api/safety-companion/profile/');
      document.getElementById('scFallState').textContent = profile.fall_detection_enabled ? 'ON' : 'OFF';
      document.getElementById('scInactivityState').textContent = profile.inactivity_detection_enabled ? 'ON' : 'OFF';
      document.getElementById('scVoiceState').textContent = profile.voice_distress_enabled ? 'On-device active' : 'Off until enabled';
      document.getElementById('scVoiceToggle').textContent = profile.voice_distress_enabled ? 'Disable' : 'Enable';
      document.getElementById('scWellnessState').textContent = profile.wellness_enabled ? 'ON' : 'OFF';
      document.getElementById('scArmedStatus').innerHTML = profile.silent_sos_enabled ? '<i></i> Companion active' : '<i></i> Silent SOS off';
    } catch(e) {}
  }

  async function sendSilentSOS(source='triple_key'){
    if (!profile?.silent_sos_enabled) return;
    let pos = null;
    try {
      pos = await new Promise((resolve,reject) => {
        if (!navigator.geolocation) return reject(new Error('GPS unavailable'));
        navigator.geolocation.getCurrentPosition(p=>resolve(p.coords),reject,{enableHighAccuracy:true,timeout:8000,maximumAge:5000});
      });
    } catch(e) { return; }
    // Deliberately no toast, DOM status update, sound or confirmation.
    try {
      await api('/api/safety-companion/silent-sos/', jsonBody({
        latitude: pos.latitude, longitude: pos.longitude,
        trigger_id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
        client_timestamp: new Date().toISOString(),
        source
      }));
    } catch(e) {}
  }

  // Browser-safe demonstration: rapid Shift x3. Native Android/iOS implementations
  // in mobile/ handle hardware events where the browser cannot.
  window.addEventListener('keydown', e => {
    if (e.key !== 'Shift' || e.repeat || ['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)) return;
    const now = performance.now();
    silentPresses = silentPresses.filter(t => now - t <= (profile?.triple_press_window_ms || 900));
    silentPresses.push(now);
    if (silentPresses.length >= 3) {
      silentPresses = [];
      void sendSilentSOS('rapid_triple_shift');
    }
  });

  document.getElementById('scTestSilent')?.addEventListener('click', () => void sendSilentSOS('manual_test'));

  function startRingtone(){
    let ctx, timer;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      let on = false;
      timer = setInterval(() => {
        if (!ctx) return;
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = on ? 880 : 660; g.gain.value = 0.035;
        o.connect(g); g.connect(ctx.destination); o.start();
        setTimeout(()=>{try{o.stop()}catch(e){}}, 180);
        on = !on;
      }, 420);
    } catch(e) {}
    return () => { clearInterval(timer); try{ctx?.close()}catch(e){} };
  }

  document.getElementById('scFakeCall')?.addEventListener('click', () => {
    const overlay = document.createElement('div');
    overlay.className = 'sc-call-overlay';
    overlay.innerHTML = `<div class="sc-call-card">
      <div class="sc-call-avatar">M</div><div class="small">Incoming call</div><h2>Mom</h2><p>Mobile · CareConnect local decoy</p>
      <div class="sc-call-actions"><button class="sc-call-action decline" aria-label="Decline">✕</button><button class="sc-call-action accept" aria-label="Accept">✓</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const stop = startRingtone();
    const close = () => { stop(); overlay.remove(); };
    overlay.querySelector('.decline').onclick = close;
    overlay.querySelector('.accept').onclick = () => { stop(); overlay.querySelector('.sc-call-card').innerHTML = '<div class="sc-call-avatar">M</div><div class="small">Call connected</div><h2>Mom</h2><p>Decoy call active</p><button class="sc-primary-btn" style="margin-top:28px">End call</button>'; overlay.querySelector('.sc-primary-btn').onclick = close; };
  });

  document.getElementById('scVoiceToggle')?.addEventListener('click', async () => {
    const enabled = !profile?.voice_distress_enabled;
    try {
      profile = await api('/api/safety-companion/profile/', {method:'PATCH',body:JSON.stringify({voice_distress_enabled:enabled})});
      await loadProfile();
    } catch(e) { toast(e.message,'error'); }
  });

  async function gps(){
    return new Promise((resolve,reject)=>{
      if(!navigator.geolocation) return reject(new Error('GPS is not supported.'));
      navigator.geolocation.getCurrentPosition(p=>resolve(p.coords),e=>reject(new Error(e.message || 'Unable to get GPS.')),{enableHighAccuracy:true,timeout:10000,maximumAge:5000});
    });
  }

  document.getElementById('scRouteBtn')?.addEventListener('click', async () => {
    const out = document.getElementById('scRouteResult');
    const lat = Number(document.getElementById('scDestLat').value), lng = Number(document.getElementById('scDestLng').value);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) { out.textContent='Enter a destination latitude and longitude.'; return; }
    out.textContent='Finding a safer path from your current GPS…';
    try {
      const p = await gps();
      const d = await api('/api/safety-companion/safe-route/', jsonBody({
        start:{lat:p.latitude,lng:p.longitude}, end:{lat,lng},
        safety_weight:Number(document.getElementById('scRouteWeight').value)
      }));
      document.getElementById('scRouteScore').textContent = `${d.average_safety_score}/100`;
      out.innerHTML = `<strong>${d.distance_m} m weighted route</strong> · average safety ${d.average_safety_score}/100 · ${d.segments.length} rated segments. <a target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&origin=${p.latitude},${p.longitude}&destination=${lat},${lng}">Open destination</a>`;
    } catch(e) { out.textContent = e.message; document.getElementById('scRouteScore').textContent='—'; }
  });

  document.getElementById('scReportSegment')?.addEventListener('click', async () => {
    try {
      const p = await gps();
      const lat = Number(document.getElementById('scDestLat').value), lng = Number(document.getElementById('scDestLng').value);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) throw new Error('Enter the segment endpoint in the destination fields first.');
      const distance = Math.max(1, Math.round(haversine(p.latitude,p.longitude,lat,lng)));
      await api('/api/safety-companion/route-segments/', jsonBody({
        start_lat:p.latitude,start_lng:p.longitude,end_lat:lat,end_lng:lng,
        distance_m:distance,safety_score:Number(document.getElementById('scSegmentScore').value)
      }));
      toast('Safety rating shared with your community','success');
    } catch(e) { toast(e.message,'error'); }
  });

  function haversine(a,b,c,d){
    const R=6371000, to=x=>x*Math.PI/180, x=to(c-a), y=to(d-b);
    const aa=Math.sin(x/2)**2+Math.cos(to(a))*Math.cos(to(c))*Math.sin(y/2)**2;
    return R*2*Math.atan2(Math.sqrt(aa),Math.sqrt(1-aa));
  }

  async function refreshWellness(){
    try {
      const rows = await api('/api/safety-companion/wellness/');
      const active = rows.find(x=>['scheduled','prompted'].includes(x.status));
      if(active){
        wellnessId = active.id;
        document.getElementById('scWellnessMessage').textContent = active.status==='prompted' ? 'Your wellness check is waiting for a response.' : `Scheduled for ${fmt(active.scheduled_for)}.`;
        document.getElementById('scWellnessSafe').disabled = active.status !== 'prompted';
      } else {
        wellnessId = null;
        document.getElementById('scWellnessMessage').textContent = rows[0] ? `Last check: ${rows[0].status}.` : 'No active check-in.';
        document.getElementById('scWellnessSafe').disabled = true;
      }
    } catch(e) {}
  }

  document.getElementById('scWellnessSchedule')?.addEventListener('click', async () => {
    try {
      if (!profile?.wellness_enabled) await api('/api/safety-companion/profile/',{method:'PATCH',body:JSON.stringify({wellness_enabled:true})});
      const [h,m] = document.getElementById('scWellnessTime').value.split(':').map(Number);
      const d = new Date(); d.setDate(d.getDate()+1); d.setHours(h||9,m||0,0,0);
      const timeout = Number(document.getElementById('scWellnessTimeout').value);
      const row = await api('/api/safety-companion/wellness/',jsonBody({scheduled_for:d.toISOString(),timeout_minutes:timeout}));
      wellnessId = row.id;
      document.getElementById('scWellnessMessage').textContent = `Scheduled for ${fmt(row.scheduled_for)}.`;
      document.getElementById('scWellnessState').textContent='ON';
      toast('Wellness check scheduled','success');
    } catch(e) { toast(e.message,'error'); }
  });

  document.getElementById('scWellnessSafe')?.addEventListener('click', async () => {
    if(!wellnessId)return;
    try { await api(`/api/safety-companion/wellness/${wellnessId}/action/`,jsonBody({action:'safe'})); toast('Marked safe','success'); refreshWellness(); }
    catch(e){toast(e.message,'error')}
  });

  loadProfile().then(refreshWellness);
})();
