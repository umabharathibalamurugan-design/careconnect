document.addEventListener('DOMContentLoaded',()=>{
  navUser();
  setActiveNav();
  document.querySelectorAll('[data-logout]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();CC.logout()}));
  const toggle=document.getElementById('menuToggle'), side=document.getElementById('sidebar'), overlay=document.getElementById('sidebarOverlay');
  const close=()=>{side?.classList.remove('open');overlay?.classList.remove('show')};
  toggle?.addEventListener('click',()=>{side?.classList.toggle('open');overlay?.classList.toggle('show')});
  overlay?.addEventListener('click',close);
});
function setActiveNav(){
  const path=location.pathname;
  document.querySelectorAll('[data-nav]').forEach(a=>{
    const key=a.dataset.nav;
    const match=(key==='dashboard'&&path==='/dashboard/')||(key==='sos'&&path.startsWith('/sos'))||
      (key==='location'&&path.startsWith('/location'))||(key==='contacts'&&path.startsWith('/emergency-contacts'))||
      (key==='history'&&path.startsWith('/emergency-history'))||(key==='notifications'&&path.startsWith('/notifications'))||
      (key==='admin'&&path.startsWith('/admin-portal'));
    a.classList.toggle('active',match);
  });
  const headings={dashboard:'Dashboard',sos:'Emergency SOS',location:'Live GPS Tracking',contacts:'Emergency Contacts',history:'Incident Monitoring',notifications:'Notifications',admin:'Response Center'};
  const active=document.querySelector('[data-nav].active');const h=document.getElementById('pageHeading');
  if(active&&h)h.textContent=headings[active.dataset.nav]||'Community safety';
  const u=CC.user;
  const adminRoles=['society_admin','security','volunteer'];
  document.querySelectorAll('[data-admin-only]').forEach(e=>e.style.display=(u&&adminRoles.includes(u.role))?'flex':'none');
}
