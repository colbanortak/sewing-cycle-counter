"""Modern Dashboard HTML - COLBAN Performans Takip Sistemi"""

DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>COLBAN Performans Takip</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>

:root{--bg:#0f1117;--bg2:#1a1d2e;--bg3:#242840;--sidebar:#13152a;--text:#e2e8f0;--text2:#94a3b8;
--primary:#6366f1;--primary2:#818cf8;--green:#22c55e;--yellow:#eab308;--red:#ef4444;--gray:#64748b;
--border:#2d3154;--card:#1e2235;--radius:12px;--shadow:0 4px 24px rgba(0,0,0,.3)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);display:flex;min-height:100vh;overflow-x:hidden}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--bg2)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.sidebar{width:260px;background:var(--sidebar);border-right:1px solid var(--border);display:flex;flex-direction:column;position:fixed;top:0;left:0;height:100vh;z-index:100;transition:transform .3s}
.sidebar .logo{padding:24px 20px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border)}
.sidebar .logo svg{width:36px;height:36px;flex-shrink:0}
.sidebar .logo-text{font-size:15px;font-weight:700;color:var(--primary2)}
.sidebar .logo-sub{font-size:10px;color:var(--text2);text-transform:uppercase;letter-spacing:1.5px}
.sidebar nav{flex:1;padding:16px 12px;display:flex;flex-direction:column;gap:4px}
.sidebar nav a{display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:var(--radius);color:var(--text2);text-decoration:none;font-size:14px;font-weight:500;transition:all .2s;cursor:pointer}
.sidebar nav a:hover{background:rgba(99,102,241,.1);color:var(--text)}
.sidebar nav a.active{background:rgba(99,102,241,.15);color:var(--primary2);border-left:3px solid var(--primary)}
.sidebar nav a svg{width:20px;height:20px;flex-shrink:0}
.sidebar nav a .badge{margin-left:auto;background:var(--primary);color:#fff;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600}
.sidebar .clock-box{padding:16px 20px;border-top:1px solid var(--border);text-align:center}
.sidebar .clock-box .time{font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:var(--primary2)}
.sidebar .clock-box .date{font-size:12px;color:var(--text2);margin-top:4px}
.main{margin-left:260px;flex:1;min-height:100vh}
.top-header{position:sticky;top:0;background:rgba(15,17,23,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:16px 32px;display:flex;align-items:center;justify-content:space-between;z-index:50}
.top-header h1{font-size:20px;font-weight:700}
.top-header .hdr-clock{font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--text2)}
.hamburger{display:none;background:none;border:none;color:var(--text);cursor:pointer;padding:8px}
.hamburger svg{width:24px;height:24px}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:90}
.content{padding:32px}
.page{display:none}.page.active{display:block}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px;margin-bottom:32px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat-card:nth-child(1)::before{background:linear-gradient(90deg,#6366f1,#818cf8)}
.stat-card:nth-child(2)::before{background:linear-gradient(90deg,#22c55e,#4ade80)}
.stat-card:nth-child(3)::before{background:linear-gradient(90deg,#f59e0b,#fbbf24)}
.stat-card:nth-child(4)::before{background:linear-gradient(90deg,#ec4899,#f472b6)}
.stat-card .label{font-size:13px;color:var(--text2);margin-bottom:8px}
.stat-card .value{font-size:28px;font-weight:800;font-family:'JetBrains Mono',monospace}
.stat-card .sub{font-size:12px;color:var(--text2);margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
thead th{background:var(--bg3);padding:14px 16px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);font-weight:600}
tbody td{padding:12px 16px;border-top:1px solid var(--border);font-size:14px}
tbody tr:hover{background:rgba(99,102,241,.05)}
.badge{display:inline-block;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;text-transform:uppercase}
.badge-green{background:rgba(34,197,94,.15);color:#4ade80}
.badge-yellow{background:rgba(234,179,8,.15);color:#facc15}
.badge-red{background:rgba(239,68,68,.15);color:#f87171}
.badge-gray{background:rgba(100,116,139,.15);color:#94a3b8}
.badge-blue{background:rgba(99,102,241,.15);color:#818cf8}
.form-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:28px;margin-bottom:28px}
.form-card h3{font-size:16px;margin-bottom:20px;color:var(--primary2)}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.form-group{display:flex;flex-direction:column;gap:6px}
.form-group label{font-size:13px;color:var(--text2);font-weight:500}
.form-group input,.form-group select{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:14px;font-family:'Inter',sans-serif;outline:none;transition:border .2s}
.form-group input:focus,.form-group select:focus{border-color:var(--primary)}
.form-group input[type=file]{padding:8px}
.btn{padding:10px 24px;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif}
.btn-primary{background:var(--primary);color:#fff}.btn-primary:hover{background:#5558e6}
.btn-danger{background:var(--red);color:#fff}.btn-danger:hover{background:#dc2626}
.btn-sm{padding:6px 14px;font-size:12px}
.btn-success{background:var(--green);color:#fff}.btn-success:hover{background:#16a34a}
.machine-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-top:24px}
.machine-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px;position:relative}
.machine-card .mc-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.machine-card .mc-id{font-weight:700;font-size:16px}
.machine-card .mc-dot{width:10px;height:10px;border-radius:50%}
.machine-card .mc-dot.on{background:var(--green);box-shadow:0 0 8px rgba(34,197,94,.5)}
.machine-card .mc-dot.off{background:var(--gray)}
.machine-card .mc-info{font-size:13px;color:var(--text2);margin-bottom:4px}
.machine-card .mc-cycles{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:var(--primary2);margin-top:8px}
.report-section{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:24px}
.report-section h3{font-size:15px;margin-bottom:16px;color:var(--primary2)}
.bar-chart{display:flex;align-items:flex-end;gap:12px;height:200px;padding-top:16px}
.bar-col{display:flex;flex-direction:column;align-items:center;flex:1;gap:6px}
.bar-col .bar{width:100%;max-width:60px;background:linear-gradient(180deg,var(--primary),var(--primary2));border-radius:6px 6px 0 0;min-height:4px;transition:height .5s}
.bar-col .bar-label{font-size:11px;color:var(--text2);text-align:center;word-break:break-all}
.bar-col .bar-val{font-size:12px;font-weight:700;font-family:'JetBrains Mono',monospace}
.progress-row{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.progress-row .pr-name{width:120px;font-size:13px;color:var(--text2);flex-shrink:0}
.progress-row .pr-bar{flex:1;height:20px;background:var(--bg2);border-radius:6px;overflow:hidden}
.progress-row .pr-fill{height:100%;background:linear-gradient(90deg,var(--primary),var(--primary2));border-radius:6px;transition:width .5s}
.progress-row .pr-val{width:60px;text-align:right;font-size:13px;font-family:'JetBrains Mono',monospace}
.toast-container{position:fixed;top:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{padding:14px 20px;border-radius:var(--radius);font-size:14px;font-weight:500;animation:slideIn .3s;box-shadow:var(--shadow)}
.toast-success{background:#065f46;color:#6ee7b7;border:1px solid #059669}
.toast-error{background:#7f1d1d;color:#fca5a5;border:1px solid #dc2626}
@keyframes slideIn{from{transform:translateX(100px);opacity:0}to{transform:translateX(0);opacity:1}}
@media(max-width:768px){
.sidebar{transform:translateX(-100%)}
.sidebar.open{transform:translateX(0)}
.overlay.show{display:block}
.main{margin-left:0}
.hamburger{display:block}
.content{padding:16px}
.stats-grid{grid-template-columns:1fr 1fr}
}

</style>
</head>
<body>
<div class="overlay" id="overlay" onclick="closeSidebar()"></div>
<aside class="sidebar" id="sidebar">
  <div class="logo"><svg viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="16" stroke="#6366f1" stroke-width="2"/><path d="M12 18c0-3.3 2.7-6 6-6s6 2.7 6 6-2.7 6-6 6" stroke="#818cf8" stroke-width="2" stroke-linecap="round"/><circle cx="18" cy="18" r="2" fill="#6366f1"/></svg><div><div class="logo-text">COLBAN AI</div><div class="logo-sub">Performans Takip</div></div></div>
  <nav><a class="nav-link active" data-page="overview" onclick="showPage('overview')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span>Genel Bakis</span></a><a class="nav-link" data-page="training" onclick="showPage('training')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg><span>Urun Egitimi</span></a><a class="nav-link" data-page="machines" onclick="showPage('machines')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h.01M12 12h.01M18 12h.01"/></svg><span>Makineler</span></a><a class="nav-link" data-page="live" onclick="showPage('live')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg><span>Canli Sayim</span><span class="badge" id="live-badge" style="display:none">0</span></a><a class="nav-link" data-page="reports" onclick="showPage('reports')"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg><span>Raporlar</span></a></nav>
  <div class="clock-box"><div class="time" id="sidebar-clock">--:--:--</div><div class="date" id="sidebar-date">---</div></div>
</aside>
<div class="main">
<header class="top-header">
<div style="display:flex;align-items:center;gap:12px">
<button class="hamburger" onclick="toggleSidebar()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg></button>
<h1 id="page-title">Genel Bakis</h1>
</div>
<span class="hdr-clock" id="header-clock">--:--:--</span>
</header>
<div class="content">
<div class="page active" id="page-overview">
  <div class="stats-grid">
    <div class="stat-card"><div class="label">Toplam Uretim (Bugun)</div><div class="value" id="st-total">--</div><div class="sub">dikis dongusu</div></div>
    <div class="stat-card"><div class="label">Aktif Makine</div><div class="value" id="st-active">--</div><div class="sub">calisiyor</div></div>
    <div class="stat-card"><div class="label">Egitilmis Urun</div><div class="value" id="st-products">--</div><div class="sub">profil hazir</div></div>
    <div class="stat-card"><div class="label">Ort. Hiz</div><div class="value" id="st-speed">--</div><div class="sub">dongu/dk</div></div>
  </div>
  <h3 style="margin-bottom:16px;font-size:16px">Son Oturumlar</h3>
  <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Urun</th><th>Makine</th><th>Operator</th><th>Dongu</th><th>Hiz</th><th>Durum</th><th>Baslangic</th></tr></thead>
  <tbody id="sessions-tbody"><tr><td colspan="8" style="text-align:center;color:var(--text2)">Yukleniyor...</td></tr></tbody></table></div>
</div>
<div class="page" id="page-training">
  <div class="form-card">
    <h3>Yeni Urun Egitimi</h3>
    <form id="train-form" onsubmit="return trainProduct(event)">
      <div class="form-grid">
        <div class="form-group"><label>Urun Adi</label><input type="text" id="t-name" placeholder="ornek: gomlek" required></div>
        <div class="form-group"><label>Dongu Sayisi</label><input type="number" id="t-cycles" value="50" min="10" max="500" required></div>
        <div class="form-group"><label>Video Suresi (dk)</label><input type="number" id="t-duration" value="5" min="1" max="60"></div>
        <div class="form-group"><label>Notlar</label><input type="text" id="t-notes" placeholder="istege bagli"></div>
      </div>
      <div class="form-group" style="margin-top:16px"><label>Referans Video</label><input type="file" id="t-video" accept="video/*" required></div>
      <button type="submit" class="btn btn-primary" style="margin-top:16px">Egitimi Baslat</button>
    </form>
  </div>
  <h3 style="margin-bottom:16px;font-size:16px">Egitilmis Urunler</h3>
  <div style="overflow-x:auto"><table><thead><tr><th>Urun</th><th>Dongu</th><th>Ort. Sure</th><th>Durum</th><th>Egitim Tarihi</th><th>Islem</th></tr></thead>
  <tbody id="products-tbody"><tr><td colspan="6" style="text-align:center;color:var(--text2)">Yukleniyor...</td></tr></tbody></table></div>
</div>
<div class="page" id="page-machines">
  <div class="form-card">
    <h3>Yeni Makine Ekle</h3>
    <form id="machine-form" onsubmit="return addMachine(event)">
      <div class="form-grid">
        <div class="form-group"><label>Makine ID</label><input type="text" id="m-id" placeholder="M01" required></div>
        <div class="form-group"><label>Makine Adi</label><input type="text" id="m-name" placeholder="Duz Dikis 1" required></div>
        <div class="form-group"><label>Kamera Kaynagi</label><input type="text" id="m-camera" placeholder="0 veya rtsp://..." required></div>
        <div class="form-group"><label>Operator</label><input type="text" id="m-operator" placeholder="istege bagli"></div>
      </div>
      <button type="submit" class="btn btn-primary" style="margin-top:16px">Makine Ekle</button>
    </form>
  </div>
  <h3 style="margin-bottom:16px;font-size:16px">Kayitli Makineler</h3>
  <div style="overflow-x:auto"><table><thead><tr><th>ID</th><th>Ad</th><th>Kamera</th><th>Operator</th><th>Urun</th><th>Durum</th></tr></thead>
  <tbody id="machines-tbody"><tr><td colspan="6" style="text-align:center;color:var(--text2)">Yukleniyor...</td></tr></tbody></table></div>
</div>
<div class="page" id="page-live">
  <div class="form-card">
    <h3>Canli Sayim Baslat</h3>
    <form id="live-form" onsubmit="return startLive(event)">
      <div class="form-grid">
        <div class="form-group"><label>Makine</label><select id="l-machine" required><option value="">Secin...</option></select></div>
        <div class="form-group"><label>Urun Profili</label><select id="l-product" required><option value="">Secin...</option></select></div>
        <div class="form-group"><label>Operator</label><input type="text" id="l-operator" placeholder="istege bagli"></div>
      </div>
      <button type="submit" class="btn btn-success" style="margin-top:16px">Sayimi Baslat</button>
    </form>
  </div>
  <h3 style="margin-bottom:16px;font-size:16px">Makine Durumu</h3>
  <div class="machine-grid" id="live-machines"></div>
</div>
<div class="page" id="page-reports">
  <div class="form-card">
    <h3>Gunluk Rapor</h3>
    <div class="form-grid" style="max-width:400px">
      <div class="form-group"><label>Tarih</label><input type="date" id="r-date" onchange="loadReport()"></div>
    </div>
  </div>
  <div id="report-content" style="display:none">
    <div class="stats-grid" style="margin-bottom:24px">
      <div class="stat-card"><div class="label">Toplam Dongu</div><div class="value" id="r-total">--</div></div>
      <div class="stat-card"><div class="label">Oturum Sayisi</div><div class="value" id="r-sessions">--</div></div>
    </div>
    <div class="report-section">
      <h3>Makine Bazli Uretim</h3>
      <div class="bar-chart" id="r-machine-chart"></div>
    </div>
    <div class="report-section">
      <h3>Urun Dagilimi</h3>
      <div id="r-product-dist"></div>
    </div>
  </div>
</div>
</div></div>
<div class="toast-container" id="toast-container"></div>
<script>

let currentPage='overview';
const PAGES=['overview','training','machines','live','reports'];
let refreshTimers={};

function showPage(id){
  currentPage=id;
  PAGES.forEach(p=>{
    document.getElementById('page-'+p).classList.toggle('active',p===id);
  });
  document.querySelectorAll('.nav-link').forEach(a=>{
    a.classList.toggle('active',a.dataset.page===id);
  });
  document.getElementById('page-title').textContent={
    overview:'Genel Bakis',training:'Urun Egitimi',machines:'Makineler',live:'Canli Sayim',reports:'Raporlar'
  }[id];
  Object.values(refreshTimers).forEach(clearInterval);
  refreshTimers={};
  if(id==='overview'){loadOverview();refreshTimers.ov=setInterval(loadOverview,8000)}
  if(id==='training'){loadProducts();refreshTimers.tr=setInterval(loadProducts,5000)}
  if(id==='machines')loadMachines();
  if(id==='live'){loadLiveDropdowns();loadLiveStatus();refreshTimers.lv=setInterval(loadLiveStatus,8000)}
  if(id==='reports'){document.getElementById('r-date').value=new Date().toISOString().slice(0,10);loadReport()}
  closeSidebar();
}

function toast(msg,type){
  let c=document.getElementById('toast-container');
  let t=document.createElement('div');
  t.className='toast toast-'+type;
  t.textContent=msg;
  c.appendChild(t);
  setTimeout(()=>t.remove(),4000);
}

async function api(url,opts){
  try{let r=await fetch(url,opts);let d=await r.json();if(!r.ok)throw new Error(d.detail||'Hata');return d}
  catch(e){toast(e.message,'error');throw e}
}

// OVERVIEW
async function loadOverview(){
  try{
    let [sessions,products,live]=await Promise.all([
      api('/api/sessions?limit=10'),api('/api/products'),api('/api/live/status')
    ]);
    let today=new Date().toISOString().slice(0,10);
    let todaySessions=sessions.filter(s=>s.started_at&&s.started_at.startsWith(today));
    let totalCycles=todaySessions.reduce((a,s)=>a+(s.total_cycles||0),0);
    let activeMachines=live.filter?live.filter(m=>m.is_active).length:(live.machines?live.machines.filter(m=>m.is_active).length:0);
    let readyProducts=products.filter(p=>p.status==='ready').length;
    let speeds=todaySessions.filter(s=>s.cycles_per_minute>0).map(s=>s.cycles_per_minute);
    let avgSpeed=speeds.length?((speeds.reduce((a,b)=>a+b,0)/speeds.length).toFixed(1)):'--';
    document.getElementById('st-total').textContent=totalCycles;
    document.getElementById('st-active').textContent=activeMachines;
    document.getElementById('st-products').textContent=readyProducts;
    document.getElementById('st-speed').textContent=avgSpeed;
    let badge=document.getElementById('live-badge');
    if(activeMachines>0){badge.style.display='inline';badge.textContent=activeMachines}else{badge.style.display='none'}
    let tbody=document.getElementById('sessions-tbody');
    if(!sessions.length){tbody.innerHTML='<tr><td colspan="8" style="text-align:center;color:var(--text2)">Oturum bulunamadi</td></tr>';return}
    tbody.innerHTML=sessions.map(s=>{
      let statusBadge=s.status==='active'?'badge-green':s.status==='completed'?'badge-blue':'badge-gray';
      return '<tr><td>'+s.id+'</td><td>'+s.product_name+'</td><td>'+s.machine_id+'</td><td>'+(s.operator_name||'-')+'</td><td style="font-family:JetBrains Mono,monospace;font-weight:700">'+s.total_cycles+'</td><td>'+(s.cycles_per_minute?s.cycles_per_minute.toFixed(1):'-')+'</td><td><span class="badge '+statusBadge+'">'+s.status+'</span></td><td>'+(s.started_at?s.started_at.replace('T',' ').slice(0,19):'-')+'</td></tr>';
    }).join('');
  }catch(e){}
}

// PRODUCTS
async function loadProducts(){
  try{
    let products=await api('/api/products');
    let tbody=document.getElementById('products-tbody');
    if(!products.length){tbody.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text2)">Henuz urun yok</td></tr>';return}
    tbody.innerHTML=products.map(p=>{
      let sc={'ready':'badge-green','training':'badge-yellow','failed':'badge-red','pending':'badge-gray'}[p.status]||'badge-gray';
      return '<tr><td style="font-weight:600">'+p.name+'</td><td>'+p.cycle_count+'</td><td>'+(p.avg_cycle_duration?p.avg_cycle_duration.toFixed(2)+'s':'-')+'</td><td><span class="badge '+sc+'">'+p.status+'</span></td><td>'+(p.trained_at||'-')+'</td><td><button class="btn btn-danger btn-sm" onclick="deleteProduct(\''+p.name+'\')">Sil</button></td></tr>';
    }).join('');
  }catch(e){}
}

async function trainProduct(e){
  e.preventDefault();
  let fd=new FormData();
  fd.append('product_name',document.getElementById('t-name').value);
  fd.append('cycle_count',document.getElementById('t-cycles').value);
  fd.append('video_duration_min',document.getElementById('t-duration').value);
  fd.append('notes',document.getElementById('t-notes').value);
  fd.append('video',document.getElementById('t-video').files[0]);
  try{await api('/api/products/create',{method:'POST',body:fd});toast('Egitim baslatildi','success');document.getElementById('train-form').reset();loadProducts()}catch(e){}
  return false;
}

async function deleteProduct(name){
  if(!confirm(name+' urununu silmek istediginize emin misiniz?'))return;
  try{await api('/api/products/'+encodeURIComponent(name),{method:'DELETE'});toast('Urun silindi','success');loadProducts()}catch(e){}
}

// MACHINES
async function loadMachines(){
  try{
    let machines=await api('/api/machines');
    let tbody=document.getElementById('machines-tbody');
    if(!machines.length){tbody.innerHTML='<tr><td colspan="6" style="text-align:center;color:var(--text2)">Henuz makine yok</td></tr>';return}
    tbody.innerHTML=machines.map(m=>{
      let st=m.is_active?'<span class="badge badge-green">Aktif</span>':'<span class="badge badge-gray">Pasif</span>';
      return '<tr><td style="font-weight:600">'+m.id+'</td><td>'+m.name+'</td><td style="font-family:JetBrains Mono,monospace;font-size:12px">'+m.camera_source+'</td><td>'+(m.operator||'-')+'</td><td>'+(m.current_product||'-')+'</td><td>'+st+'</td></tr>';
    }).join('');
  }catch(e){}
}

async function addMachine(e){
  e.preventDefault();
  let fd=new FormData();
  fd.append('machine_id',document.getElementById('m-id').value);
  fd.append('name',document.getElementById('m-name').value);
  fd.append('camera_source',document.getElementById('m-camera').value);
  fd.append('operator',document.getElementById('m-operator').value);
  try{await api('/api/machines',{method:'POST',body:fd});toast('Makine eklendi','success');document.getElementById('machine-form').reset();loadMachines()}catch(e){}
  return false;
}

// LIVE
async function loadLiveDropdowns(){
  try{
    let [machines,products]=await Promise.all([api('/api/machines'),api('/api/products')]);
    let ms=document.getElementById('l-machine');
    let ps=document.getElementById('l-product');
    ms.innerHTML='<option value="">Secin...</option>'+machines.map(m=>'<option value="'+m.id+'">'+m.id+' - '+m.name+'</option>').join('');
    ps.innerHTML='<option value="">Secin...</option>'+products.filter(p=>p.status==='ready').map(p=>'<option value="'+p.name+'">'+p.name+'</option>').join('');
  }catch(e){}
}

async function loadLiveStatus(){
  try{
    let data=await api('/api/live/status');
    let machines=Array.isArray(data)?data:(data.machines||[]);
    let grid=document.getElementById('live-machines');
    if(!machines.length){grid.innerHTML='<p style="color:var(--text2)">Henuz makine kaydi yok</p>';return}
    grid.innerHTML=machines.map(m=>{
      let active=m.is_active;
      let dotClass=active?'on':'off';
      let cycles=m.last_session?m.last_session.total_cycles:0;
      let product=m.current_product||'-';
      let stopBtn=active?'<button class="btn btn-danger btn-sm" onclick="stopLive(\''+m.id+'\')">Durdur</button>':'';
      return '<div class="machine-card"><div class="mc-header"><span class="mc-id">'+m.id+'</span><span class="mc-dot '+dotClass+'"></span></div><div class="mc-info">Urun: '+product+'</div><div class="mc-info">Operator: '+(m.operator||'-')+'</div><div class="mc-cycles">'+cycles+'</div><div style="margin-top:12px">'+stopBtn+'</div></div>';
    }).join('');
    let activeCnt=machines.filter(m=>m.is_active).length;
    let badge=document.getElementById('live-badge');
    if(activeCnt>0){badge.style.display='inline';badge.textContent=activeCnt}else{badge.style.display='none'}
  }catch(e){}
}

async function startLive(e){
  e.preventDefault();
  let fd=new FormData();
  fd.append('machine_id',document.getElementById('l-machine').value);
  fd.append('product_name',document.getElementById('l-product').value);
  fd.append('operator',document.getElementById('l-operator').value);
  try{await api('/api/live/start',{method:'POST',body:fd});toast('Sayim baslatildi','success');loadLiveStatus()}catch(e){}
  return false;
}

async function stopLive(machineId){
  if(!confirm(machineId+' sayimini durdurmak istiyor musunuz?'))return;
  try{await api('/api/live/stop/'+machineId,{method:'POST'});toast('Sayim durduruldu','success');loadLiveStatus()}catch(e){}
}

// REPORTS
async function loadReport(){
  let date=document.getElementById('r-date').value;
  if(!date)return;
  try{
    let data=await api('/api/reports/daily?date='+date);
    document.getElementById('report-content').style.display='block';
    document.getElementById('r-total').textContent=data.total_cycles||0;
    document.getElementById('r-sessions').textContent=data.session_count||0;
    // machine chart
    let byMachine=data.by_machine||{};
    let mKeys=Object.keys(byMachine);
    let maxVal=Math.max(...mKeys.map(k=>byMachine[k]),1);
    let chart=document.getElementById('r-machine-chart');
    if(!mKeys.length){chart.innerHTML='<p style="color:var(--text2)">Veri yok</p>'}
    else{chart.innerHTML=mKeys.map(k=>{
      let pct=Math.round((byMachine[k]/maxVal)*100);
      return '<div class="bar-col"><div class="bar-val">'+byMachine[k]+'</div><div class="bar" style="height:'+pct+'%"></div><div class="bar-label">'+k+'</div></div>';
    }).join('')}
    // product distribution
    let byProduct=data.by_product||{};
    let pKeys=Object.keys(byProduct);
    let pTotal=pKeys.reduce((a,k)=>a+byProduct[k],0)||1;
    let dist=document.getElementById('r-product-dist');
    if(!pKeys.length){dist.innerHTML='<p style="color:var(--text2)">Veri yok</p>'}
    else{dist.innerHTML=pKeys.map(k=>{
      let pct=Math.round((byProduct[k]/pTotal)*100);
      return '<div class="progress-row"><div class="pr-name">'+k+'</div><div class="pr-bar"><div class="pr-fill" style="width:'+pct+'%"></div></div><div class="pr-val">'+byProduct[k]+'</div></div>';
    }).join('')}
  }catch(e){document.getElementById('report-content').style.display='none'}
}

// CLOCK
function updateClock(){
  let now=new Date();
  let time=now.toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  let date=now.toLocaleDateString('tr-TR',{weekday:'long',year:'numeric',month:'long',day:'numeric'});
  document.getElementById('sidebar-clock').textContent=time;
  document.getElementById('sidebar-date').textContent=date;
  document.getElementById('header-clock').textContent=time;
}
setInterval(updateClock,1000);
updateClock();

// SIDEBAR MOBILE
function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}
function closeSidebar(){
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
}

// INIT
showPage('overview');

</script>
</body></html>'''
