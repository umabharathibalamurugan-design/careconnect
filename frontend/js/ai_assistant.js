(function(){
  const $=id=>document.getElementById(id);
  let sessionId=null, activeAlert=null;

  function setOpen(open){
    const fab=$('aiAssistantToggle'), box=$('aiAssistant');
    if(!box) return;
    box.hidden=!open;
    if(fab) fab.setAttribute('aria-expanded', open ? 'true' : 'false');
    if(open){ briefing(); setTimeout(()=>$('aiInput')?.focus(),0); }
  }

  function add(text, who){
    const d=document.createElement('div');
    d.className='ai-msg '+who;
    d.textContent=text;
    $('aiMessages').appendChild(d);
    $('aiMessages').scrollTop=$('aiMessages').scrollHeight;
  }

  function actionButtons(actions){
    const box=$('aiActions');
    if(!box) return;
    box.innerHTML='';
    if(!actions||!actions.length){box.hidden=true;return;}
    actions.forEach(a=>{
      const b=document.createElement('a');
      b.className='ai-action '+(a.style||'primary');
      b.href=a.url;
      b.textContent=a.label;
      b.addEventListener('click',()=>setOpen(false));
      box.appendChild(b);
    });
    box.hidden=false;
  }

  async function briefing(){
    const briefingBox=$('aiBriefing');
    if(!briefingBox) return;
    try{
      const q=activeAlert?('?alert_id='+encodeURIComponent(activeAlert)):'';
      const d=await CC.json('/api/ai/briefing/'+q);
      briefingBox.textContent=d.briefing;
      const c=d.context||{};
      const line=$('aiContextLine');
      if(line) line.textContent=(c.role_label||'User')+' · '+(c.active_incidents||0)+' active incident(s) visible';
    }catch(e){
      briefingBox.textContent='AI context is temporarily unavailable. The rest of CareConnect remains available.';
    }
  }

  async function ask(q){
    add(q,'user');
    $('aiInput').disabled=true;
    try{
      const d=await CC.json('/api/ai/chat/',{method:'POST',body:JSON.stringify({message:q,session_id:sessionId,alert_id:activeAlert})});
      sessionId=d.session_id;
      add(d.reply,'bot');
      actionButtons(d.actions);
      if(d.context?.current_incident) activeAlert=d.context.current_incident.id;
    }catch(e){
      add('I could not reach the Copilot service. If this is an emergency, use the SOS control directly.','bot');
    }finally{
      $('aiInput').disabled=false;
      $('aiInput').focus();
      briefing();
    }
  }

  function init(){
    const fab=$('aiAssistantToggle'), box=$('aiAssistant'), close=$('aiClose'), form=$('aiForm');
    if(!fab||!box) return;

    // Start closed. The floating AI button remains visible.
    setOpen(false);

    fab.addEventListener('click',()=>setOpen(true));
    close?.addEventListener('click',()=>setOpen(false));

    // Clicking a normal navigation link should close the floating AI panel,
    // but must NOT hide or disable the AI button itself.
    document.querySelectorAll('[data-nav], [data-action="sos"], [data-action="emergency"], [data-action="response"]').forEach(el=>{
      el.addEventListener('click',()=>setOpen(false));
    });

    document.addEventListener('click',(event)=>{
      if(box.hidden) return;
      const target=event.target;
      if(target.closest('#aiAssistant') || target.closest('#aiAssistantToggle')) return;
      // Optional outside-click close: only the AI overlay closes.
      if(!target.closest('.ai-assistant-fab')) setOpen(false);
    });

    document.querySelectorAll('[data-ai]').forEach(b=>b.addEventListener('click',()=>ask(b.dataset.ai)));
    form?.addEventListener('submit',e=>{
      e.preventDefault();
      const q=$('aiInput').value.trim();
      if(q){$('aiInput').value='';ask(q);}
    });

    window.CareConnectAI={
      open:()=>setOpen(true),
      close:()=>setOpen(false),
      toggle:()=>setOpen(box.hidden),
      setIncident:(id)=>{activeAlert=id;briefing();}
    };
  }
  document.addEventListener('DOMContentLoaded',init);
})();
