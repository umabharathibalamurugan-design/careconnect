const CC={
  get access(){return localStorage.getItem('access_token')||''},
  get user(){try{return JSON.parse(localStorage.getItem('cc_user')||'null')}catch(e){return null}},
  save(data){if(data.access)localStorage.setItem('access_token',data.access);if(data.refresh)localStorage.setItem('refresh_token',data.refresh);if(data.user)localStorage.setItem('cc_user',JSON.stringify(data.user))},
  clear(){['access_token','refresh_token','cc_user'].forEach(k=>localStorage.removeItem(k))},
  async request(url,options={}){const opts={...options,headers:{...(options.headers||{})}}; if(opts.body && !(opts.body instanceof FormData)) opts.headers['Content-Type']='application/json';if(this.access)opts.headers.Authorization='Bearer '+this.access;let r=await fetch(url,opts);if(r.status===401&&localStorage.getItem('refresh_token')){const rr=await fetch('/api/auth/token/refresh/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refresh:localStorage.getItem('refresh_token')})});if(rr.ok){const d=await rr.json();localStorage.setItem('access_token',d.access);opts.headers.Authorization='Bearer '+d.access;r=await fetch(url,opts)}}if(r.status===401){this.clear()}return r},
  async json(url,options={}){
    try{
      const r=await this.request(url,options);let d={};try{d=await r.json()}catch(e){}
      if(!r.ok)throw new Error(d.detail||d.non_field_errors?.[0]||Object.values(d).flat?.()[0]||('Request failed: '+r.status));
      return d;
    }catch(err){
      if(!navigator.onLine && String(options.method||'GET').toUpperCase()==='POST' && url==='/api/response/sos/') {
        await CC.offlineQueue(url, options);
        const e=new Error('Network unavailable. SOS saved on this device and will be sent automatically when the connection returns.');
        e.offlineQueued=true; throw e;
      }
      throw err;
    }
  },
  async offlineQueue(url, options){
    const db=await openOfflineDB();
    const tx=db.transaction('requests','readwrite');
    tx.objectStore('requests').add({url,method:options.method||'POST',body:options.body||null,headers:{'Content-Type':'application/json'},createdAt:Date.now()});
    return new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)});
  },
  logout(){this.clear();location.href='/login/'},
  requireLogin(){if(!this.access){location.href='/login/';return false}return true}
};
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[c]))}
function toast(msg,type='default'){const t=document.getElementById('toast');if(t){t.textContent=msg;t.className='toast '+(type==='success'?'toast-success':type==='error'?'toast-error':'');t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2800)}}
function fmt(v){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?v:d.toLocaleString()}
function roleLabel(r){return String(r||'resident').replace('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}
function navUser(){const u=CC.user;const name=u?(u.first_name||u.username):'Guest';document.querySelectorAll('[data-user-name]').forEach(e=>e.textContent=name);document.querySelectorAll('[data-user-role]').forEach(e=>e.textContent=u?roleLabel(u.role):'Guest');document.querySelectorAll('[data-user-initial]').forEach(e=>e.textContent=(name||'G').trim().charAt(0).toUpperCase()||'G');}
document.addEventListener('DOMContentLoaded',navUser);


function openOfflineDB(){return new Promise((resolve,reject)=>{const r=indexedDB.open('careconnect-offline',1);r.onupgradeneeded=()=>{if(!r.result.objectStoreNames.contains('requests'))r.result.createObjectStore('requests',{keyPath:'id',autoIncrement:true})};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
async function flushOfflineQueue(){
  if(!navigator.onLine)return;
  try{const db=await openOfflineDB();const tx=db.transaction('requests','readwrite');const store=tx.objectStore('requests');const rows=await new Promise((resolve,reject)=>{const q=store.getAll();q.onsuccess=()=>resolve(q.result||[]);q.onerror=()=>reject(q.error)});
    for(const item of rows){try{const r=await fetch(item.url,{method:item.method,headers:{...item.headers,Authorization:CC.access?'Bearer '+CC.access:''},body:item.body});if(r.ok)store.delete(item.id)}catch(e){break}}
  }catch(e){}
}
window.addEventListener('online',()=>{flushOfflineQueue();toast('Connection restored — queued emergency actions are syncing.','success')});
window.addEventListener('offline',()=>toast('You are offline. Emergency SOS will be queued on this device.','error'));
document.addEventListener('DOMContentLoaded',()=>{if('serviceWorker' in navigator){navigator.serviceWorker.register('/service-worker.js').catch(()=>{})};flushOfflineQueue()});
