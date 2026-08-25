async function fetchAlerts(){
  const d=await CC.json('/api/emergency-alerts/');
  return Array.isArray(d)?d:(d.results||[]);
}

async function loadResponderQueue(){
 const panel=document.getElementById('responderLivePanel'), list=document.getElementById('responderQueue'); if(!panel||!list)return;
 try{
   const items=(await fetchAlerts()).filter(x=>['open','acknowledged','active','escalated'].includes(String(x.status).toLowerCase()));
   list.innerHTML=items.length?items.slice(0,8).map(x=>{
     const phone=x.resident_phone||'';
     return `<div class="list-item responder-queue-item"><div class="row"><strong>🚨 #${esc(x.id)} · ${esc(x.alert_type)}</strong><span class="badge ${esc(x.status)}">${esc(x.status)}</span></div><div class="meta">${esc(x.resident_name||'Resident')} · ${fmt(x.created_at)}${x.priority?` · ${esc(x.priority)}`:''}</div><p class="muted">${esc(x.message||'Emergency alert')}</p><div class="actions"><a class="btn btn-light btn-sm" target="_blank" href="https://www.google.com/maps?q=${x.latitude},${x.longitude}">📍 Location</a>${phone?`<a class="btn btn-light btn-sm" href="tel:${esc(phone)}">📞 Call resident</a>`:''}<button class="btn btn-primary btn-sm" onclick="responderAction(${x.id},'accepted')">Accept</button><button class="btn btn-light btn-sm" onclick="responderAction(${x.id},'on_way')">On way</button><button class="btn btn-light btn-sm" onclick="responderAction(${x.id},'arrived')">Arrived</button><button class="btn btn-success btn-sm" onclick="responderAction(${x.id},'completed')">Resolve</button><a class="btn btn-light btn-sm" href="/emergency-history/?alert=${x.id}">Open chat</a></div></div>`;
   }).join(''):'<div class="empty">No active emergencies in your response queue.</div>';
 }catch(e){list.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
async function responderAction(id,action){try{await CC.json(`/api/response/alerts/${id}/respond/`,{method:'POST',body:JSON.stringify({action})});toast('Response status updated: '+action,'success');loadResponderQueue()}catch(e){toast(e.message,'error')}}

async function loadGuardianIncidents(){
 const panel=document.getElementById('guardianLivePanel'),list=document.getElementById('guardianIncidentList');if(!panel||!list)return;
 try{
  const items=(await fetchAlerts()).filter(x=>['open','acknowledged','active','escalated'].includes(String(x.status).toLowerCase()));
  list.innerHTML=items.length?items.slice(0,6).map(x=>`<div class="list-item"><div class="row"><strong>🚨 #${esc(x.id)} · ${esc(x.alert_type)}</strong><span class="badge ${esc(x.status)}">${esc(x.status)}</span></div><div class="meta">${esc(x.resident_name||'Resident')} · ${fmt(x.created_at)}</div><p class="muted">${esc(x.message||'Emergency alert')}</p><div class="actions"><a class="btn btn-primary btn-sm" href="/emergency-history/?alert=${x.id}">View response</a><a class="btn btn-light btn-sm" target="_blank" href="https://www.google.com/maps?q=${x.latitude},${x.longitude}">📍 Location</a>${x.resident_phone?`<a class="btn btn-light btn-sm" href="tel:${esc(x.resident_phone)}">📞 Call</a>`:''}</div></div>`).join(''):'<div class="empty">No active incidents for your linked resident.</div>';
 }catch(e){list.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}

function initResidentSOS(){
 const panel=document.getElementById('residentSosPanel'); if(!panel)return;
 panel.style.display='grid';
 const btn=document.getElementById('dashboardSOS'), cancel=document.getElementById('cancelDashboardSOS'), box=document.getElementById('sosCancelBox'), count=document.getElementById('sosCountdown'), status=document.getElementById('residentSosStatus');
 let coords=null,alertId=null,timer=null,seconds=15;
 const gps=()=>new Promise((resolve,reject)=>{if(!navigator.geolocation)return reject(new Error('GPS is not supported.'));navigator.geolocation.getCurrentPosition(p=>resolve(p.coords),e=>reject(new Error(e.message||'Unable to get GPS location.')),{enableHighAccuracy:true,timeout:10000,maximumAge:3000})});
 btn.onclick=async()=>{
   btn.disabled=true;status.className='sos-mini-status sending';status.textContent='Sending SOS and locating you…';
   try{
    coords=await gps();
    const d=await CC.json('/api/response/sos/',{method:'POST',body:JSON.stringify({alert_type:'SOS Emergency',message:'One-tap emergency SOS activated from the resident dashboard.',latitude:coords.latitude,longitude:coords.longitude,response_window_minutes:2})});
    alertId=d.alert_id;status.className='sos-mini-status success';const sm=d.smart_match;status.textContent=sm?`SOS #${d.alert_id} registered. ${sm.responder_name} is the recommended responder.`:`SOS #${d.alert_id} registered. ${d.notified_users||0} response-network users notified.`;toast('SOS sent — response team notified','success');
    box.style.display='flex';seconds=15;count.textContent=`Cancel available for ${seconds}s`;
    timer=setInterval(()=>{seconds--;count.textContent=seconds>0?`Cancel available for ${seconds}s`:'Cancellation window closed';if(seconds<=0){clearInterval(timer);box.style.display='none';}},1000);
   }catch(e){status.className='sos-mini-status error';status.textContent=e.message;btn.disabled=false}
 };
 cancel.onclick=async()=>{if(!alertId)return;try{await CC.json(`/api/response/alerts/${alertId}/cancel/`,{method:'POST',body:'{}'});toast('SOS cancelled','success');status.textContent='SOS cancelled. No response is required.';box.style.display='none';btn.disabled=false;alertId=null;clearInterval(timer)}catch(e){toast(e.message,'error')}};
}

function startCheckIn(minutes){
 CC.json('/api/response/safety-checkin/',{method:'POST',body:JSON.stringify({minutes})}).then(d=>{toast('Safety check-in started','success');window.__ccCheckinId=d.id;renderCheckIn(d);}).catch(e=>toast(e.message,'error'));
}
function renderCheckIn(d){
 const state=document.getElementById('checkinState'),status=document.getElementById('checkinStatus'),safe=document.getElementById('safeCheckInBtn'),cancel=document.getElementById('cancelCheckInBtn');if(!state||!status)return;
 const due=new Date(d.due_at).getTime();state.innerHTML='<i></i> Active';safe.style.display='inline-flex';cancel.style.display='inline-flex';
 const tick=()=>{const left=Math.max(0,due-Date.now());if(left<=0){clearInterval(window.__ccCheckinTimer);status.textContent='Safety check-in expired. Your configured guardian escalation may now begin.';state.innerHTML='<i></i> Missed';return}const mins=Math.floor(left/60000),secs=Math.floor(left/1000)%60;status.textContent=`Safety timer active · ${mins}m ${String(secs).padStart(2,'0')}s remaining · due ${new Date(d.due_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}`};clearInterval(window.__ccCheckinTimer);tick();window.__ccCheckinTimer=setInterval(tick,1000);
}
async function markSafe(){if(!window.__ccCheckinId)return;try{await CC.json(`/api/response/safety-checkin/${window.__ccCheckinId}/action/`,{method:'POST',body:JSON.stringify({action:'safe'})});toast('Safety confirmed','success');document.getElementById('checkinStatus').textContent='✓ You confirmed that you are safe.';document.getElementById('safeCheckInBtn').style.display='none';document.getElementById('cancelCheckInBtn').style.display='none';clearInterval(window.__ccCheckinTimer)}catch(e){toast(e.message,'error')}}
async function cancelCheckIn(){if(!window.__ccCheckinId)return;try{await CC.json(`/api/response/safety-checkin/${window.__ccCheckinId}/action/`,{method:'POST',body:JSON.stringify({action:'cancel'})});toast('Safety timer cancelled');document.getElementById('checkinStatus').textContent='Safety timer cancelled.';document.getElementById('safeCheckInBtn').style.display='none';document.getElementById('cancelCheckInBtn').style.display='none';clearInterval(window.__ccCheckinTimer)}catch(e){toast(e.message,'error')}}

function roleConfig(role){
 const common={
  resident:{label:'RESIDENT APP',title:'Your safety dashboard',summary:'Emergency access, safety check-ins, trusted contacts and live response updates.',features:[['🚨','Emergency SOS','Activate SOS with GPS, voice tools and two-way response.','/sos/','Open SOS','danger'],['⏱️','Safety Check-In','Set a safety timer and confirm you are safe.','/dashboard/','Start check-in','primary'],['📍','Live GPS','Share your location during an emergency.','/location/','Open GPS','light'],['♧','Emergency contacts','Keep trusted contacts ready for one-tap calling.','/emergency-contacts/','Manage contacts','light'],['🔔','Notifications','Open live alerts and response actions.','/notifications/','View notifications','light']]},
  guardian:{label:'GUARDIAN PORTAL',title:'Protect the person you care for',summary:'See active incidents, response status, shared location and direct contact actions.',features:[['🚨','Live emergencies','See the current incident and responder status.','/emergency-history/','Open incidents','danger'],['📍','Shared location','Follow location shared during an emergency.','/location/','View location','primary'],['📞','Call resident','Use the resident phone contact when available.','/emergency-contacts/','Open contacts','light'],['🔔','Response notifications','Act on alerts immediately.','/notifications/','View alerts','light']]},
  volunteer:{label:'VOLUNTEER RESPONSE DESK',title:'Respond to nearby emergencies',summary:'Accept, travel, arrive and close incidents while keeping the resident informed.',features:[['🚨','Response queue','Accept an emergency and update your response state.','/admin-portal/','Open response desk','danger'],['📍','Responder GPS','Share your live response position.','/location/','Share location','primary'],['💬','Incident chat','Communicate directly with the emergency team.','/emergency-history/','Open incidents','light'],['🔔','Assignments','See every response notification with action buttons.','/notifications/','View assignments','light']]},
  security:{label:'SECURITY RESPONSE DESK',title:'Coordinate immediate on-site safety',summary:'Handle society incidents, contact residents and escalate critical emergencies.',features:[['🚨','Security queue','Accept and manage active emergencies in your society.','/admin-portal/','Open security desk','danger'],['📞','Call resident','Contact the person who triggered the alert.','/emergency-history/','Open incidents','primary'],['📍','Live position','Share the security response location.','/location/','Open GPS','light'],['🚓','Escalation','Escalate critical incidents when configured.','/admin-portal/','Open escalation desk','light']]},
  society_admin:{label:'SOCIETY COMMAND CENTER',title:'Run emergency response for your society',summary:'Monitor residents, responders, incidents, hotspots and society-level escalation.',features:[['🏢','Command center','Manage active incidents and responder ownership.','/admin-portal/','Open command center','primary'],['👥','Responders','Review volunteer and security readiness.','/admin-portal/','Responder status','light'],['📍','Live incident map','Monitor emergency locations.','/location/','Open map','light'],['🔔','Notifications','Track every response event.','/notifications/','View alerts','light']]},
  admin:{label:'ADMIN OPERATIONS',title:'Platform emergency operations',summary:'Monitor platform-wide incidents, escalation, responder performance and audit activity.',features:[['🛡️','Operations center','Review incidents, ownership, escalation and performance.','/admin-portal/','Open operations','primary'],['📊','System intelligence','Review response trends and responder load.','/admin-portal/','Open intelligence','light'],['📍','Live map','Monitor emergency locations.','/location/','Open map','light'],['🔔','Notifications','Review system response events.','/notifications/','View alerts','light']]},
  superadmin:{label:'SUPER ADMIN',title:'CareConnect platform command',summary:'Global oversight for societies, configuration, audit visibility and emergency rules.',features:[['👑','Platform command','Manage global emergency operations and configuration.','/admin-portal/','Open platform center','primary'],['🏢','Societies','Review community-level operations.','/admin-portal/','Manage societies','light'],['📊','Analytics & audit','Review system-wide response intelligence.','/admin-portal/','Open analytics','light'],['🔔','Notifications','Monitor platform events.','/notifications/','View alerts','light']]}
 };
 return common[role]||common.resident;
}

document.addEventListener('DOMContentLoaded',async()=>{
 if(!CC.requireLogin())return;navUser();applyRoleUI();
 const u=CC.user||{},role=String(u.role||'resident').toLowerCase(),c=roleConfig(role);
 document.getElementById('roleEyebrow').textContent=c.label;document.getElementById('welcome').textContent=(u.first_name||u.username||'User')+' — '+c.title;document.getElementById('roleSummary').textContent=c.summary;document.getElementById('workspaceTitle').textContent=role==='resident'?'Safety shortcuts':role==='guardian'?'Guardian actions':role==='volunteer'||role==='security'?'Response actions':'Operations workspace';
 document.getElementById('heroActions').innerHTML=c.features.slice(0,2).map(x=>`<a class="btn btn-${x[5]}" href="${x[3]}">${x[4]}</a>`).join('');
 document.getElementById('featureGrid').innerHTML=c.features.map(x=>`<a class="feature-card" href="${x[3]}"><div class="feature-icon">${x[0]}</div><div><h3>${x[1]}</h3><p>${x[2]}</p></div><span class="feature-arrow">→</span></a>`).join('');
 const alerts=await fetchAlerts().catch(e=>{toast(e.message,'error');return[]});
 const active=alerts.filter(a=>['open','acknowledged','active','escalated'].includes(String(a.status).toLowerCase()));
 document.getElementById('total').textContent=alerts.length;document.getElementById('active').textContent=active.length;document.getElementById('critical').textContent=alerts.filter(a=>String(a.priority).toLowerCase()==='critical').length;document.getElementById('resolved').textContent=alerts.filter(a=>String(a.status).toLowerCase()==='resolved').length;renderIncidents(alerts.slice(0,8));
 if(role==='resident')initResidentSOS();
 if(role==='guardian'){document.getElementById('guardianLivePanel').style.display='block';loadGuardianIncidents();setInterval(loadGuardianIncidents,5000)}
 if(['volunteer','security','security_volunteer'].includes(role)){document.getElementById('responderLivePanel').style.display='block';document.getElementById('refreshResponderQueue')?.addEventListener('click',loadResponderQueue);loadResponderQueue();setInterval(loadResponderQueue,5000)}
 if(['resident'].includes(role)){document.getElementById('safetyCheckinPanel').style.display='block'}
 if(['admin','society_admin','superadmin'].includes(role)){document.getElementById('smartResponseSection').style.display='block'}
});
function renderIncidents(items){const el=document.getElementById('incidentList');if(!items.length){el.innerHTML='<div class="empty">No incidents yet.</div>';return}el.innerHTML=items.map(a=>`<a class="list-item incident-row" href="/emergency-history/?alert=${a.id}"><div class="incident-main"><div class="incident-title"><strong>#${esc(a.id)} · ${esc(a.alert_type)}</strong><span class="badge ${esc(String(a.status).toLowerCase())}">${esc(a.status)}</span></div><div class="meta">${esc(a.resident_name||a.resident_username||'Resident')} · ${fmt(a.created_at)}</div><p>${esc(a.message||'Emergency alert')}</p></div><span class="incident-arrow">→</span></a>`).join('')}
async function loadResponderAvailability(){
 const list=document.getElementById('availabilityList'),summary=document.getElementById('responseSummary');if(!list)return;
 try{const d=await CC.json('/api/response/responder-availability/');const items=d.responders||d.results||[];const total=items.length,available=items.filter(x=>x.available_for_emergency&&!x.busy).length,busy=items.filter(x=>x.busy).length;summary?.querySelectorAll('strong').forEach((e,i)=>e.textContent=[total,available,busy,Math.max(0,total-available-busy)][i]??'0');list.innerHTML=items.slice(0,8).map(x=>`<div class="list-item"><div class="row"><strong>${esc(x.name||x.username||'Responder')}</strong><span class="badge ${x.available_for_emergency&&!x.busy?'resolved':'medium'}">${x.available_for_emergency&&!x.busy?'Available':'Busy'}</span></div><div class="meta">${esc(x.role||'Responder')} · ${x.active_load||0} active</div></div>`).join('')||'<div class="empty">No responder data.</div>'}catch(e){list.innerHTML='<div class="empty">'+esc(e.message)+'</div>'}
}
document.getElementById('refreshResponders')?.addEventListener('click',loadResponderAvailability);

async function loadAIBriefing(){
  const box=document.getElementById('aiBriefingCard'); if(!box) return;
  try{ const d=await CC.json('/api/ai/briefing/'); box.textContent=d.briefing; }
  catch(e){ box.textContent='AI briefing is temporarily unavailable. Emergency controls and the rest of CareConnect remain available.'; }
}
document.addEventListener('DOMContentLoaded',()=>{loadAIBriefing();document.getElementById('refreshAIBriefing')?.addEventListener('click',loadAIBriefing);});
