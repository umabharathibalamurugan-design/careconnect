let notificationTimer = null;
let notificationSocket = null;

function connectNotificationSocket(){
  if(!window.WebSocket || !CC.access) return;
  const proto=location.protocol==='https:'?'wss':'ws';
  try{
    notificationSocket=new WebSocket(`${proto}://${location.host}/ws/notifications/?token=${encodeURIComponent(CC.access)}`);
    notificationSocket.onopen=()=>document.getElementById('notificationLive')?.classList.add('socket-live');
    notificationSocket.onmessage=event=>{
      try{const data=JSON.parse(event.data);if(data.type==='notification'){toast('🔔 '+data.title,'success');loadNotifications();updateNotificationBadge((Number(document.getElementById('unreadCount')?.textContent)||0)+1);}}catch(e){}
    };
    notificationSocket.onclose=()=>setTimeout(connectNotificationSocket,5000);
  }catch(e){}
}

document.addEventListener('DOMContentLoaded', async () => {
  if (!CC.requireLogin()) return;
  await loadNotifications();
  connectNotificationSocket();
  notificationTimer = setInterval(loadNotifications, 10000);
});

async function loadNotifications() {
  const el = document.getElementById('notifications');
  if (!el) return;
  try {
    const d = await CC.json('/api/notifications/');
    const items = Array.isArray(d) ? d : (d.results || []);
    const unread = items.filter(n => !n.is_read).length;
    const delivered = items.filter(n => (n.delivery_status || []).some(x => x.channel === 'in_app' && x.status === 'delivered')).length;
    document.getElementById('unreadCount').textContent = unread;
    document.getElementById('registeredCount').textContent = items.length;
    document.getElementById('deliveredCount').textContent = delivered;
    updateNotificationBadge(unread);

    el.innerHTML = items.length ? items.map(renderNotification).join('') : '<div class="empty notification-empty"><div class="empty-icon">✓</div><strong>No notifications yet</strong><p>Your emergency and response events will appear here automatically.</p></div>';
  } catch (e) {
    el.innerHTML = '<div class="empty">' + esc(e.message) + '</div>';
  }
}

function renderNotification(n) {
  const role = String(CC.user?.role || '').toLowerCase();
  const icon = n.notification_type === 'emergency' ? '🚨' : n.notification_type === 'volunteer' ? '🤝' : n.notification_type === 'tracking' ? '📍' : '🔔';
  const deliveries = n.delivery_status || [];
  const deliveryHtml = deliveries.map(x => `<span class="delivery-chip ${esc(x.status)}">${esc(x.channel.replace('_',' '))}: ${esc(x.status)}</span>`).join('');
  const incidentId = n.alert_id;
  let actions = '';
  if (incidentId) {
    actions += `<a class="btn btn-light btn-sm" href="/emergency-history/?alert=${incidentId}" onclick="readNotification(${n.id})">Open incident</a>`;
    if (['volunteer','security','security_volunteer'].includes(role)) actions += `<button class="btn btn-primary btn-sm" onclick="notificationRespond(${incidentId},${n.id})">Respond now</button>`;
    if (['admin','society_admin','superadmin','security_admin','security','security_volunteer'].includes(role)) actions += `<button class="btn btn-light btn-sm" onclick="notificationEscalate(${incidentId},${n.id})">Escalate</button>`;
  }
  if (!n.is_read) actions += `<button class="btn btn-light btn-sm notification-read" onclick="readNotification(${n.id})">Mark as read</button>`;
  return `<article class="notification-item ${n.is_read ? 'read' : 'unread'}" data-alert-id="${incidentId || ''}">
    <div class="notification-icon">${icon}</div>
    <div class="notification-body">
      <div class="notification-top"><strong>${esc(n.title)}</strong>${n.is_read ? '<span class="badge">Read</span>' : '<span class="badge active">New</span>'}</div>
      <p>${esc(n.message)}</p>
      <div class="notification-meta"><span>${fmt(n.created_at)}</span><span class="delivery-label">Delivery</span>${deliveryHtml}</div>
      <div class="actions notification-actions">${actions}</div>
    </div>
  </article>`;
}

async function notificationRespond(id, notificationId) {
  try {
    await CC.json(`/api/response/alerts/${id}/respond/`, {method:'POST', body:JSON.stringify({action:'accepted'})});
    if(notificationId) await CC.json('/api/notifications/' + notificationId + '/read/', {method:'PATCH', body:'{}'});
    toast('Emergency accepted — the resident has been notified', 'success');
    setTimeout(()=>location.href='/emergency-history/?alert='+id, 350);
  } catch(e) { toast(e.message, 'error'); }
}

async function notificationEscalate(id, notificationId) {
  try {
    await CC.json(`/api/response/alerts/${id}/escalate/`, {method:'POST', body:'{}'});
    if(notificationId) await CC.json('/api/notifications/' + notificationId + '/read/', {method:'PATCH', body:'{}'});
    toast('Emergency escalated', 'success');
    loadNotifications();
  } catch(e) { toast(e.message, 'error'); }
}

function updateNotificationBadge(count) {
  const badge = document.getElementById('notificationBadge');
  if (!badge) return;
  badge.textContent = count > 99 ? '99+' : count;
  badge.hidden = count === 0;
}
