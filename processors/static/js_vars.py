"""看板全局 JS 常量 — 从 base.py 拆分"""
GLOBAL_JS = """
// ══════════════════════════════════════════════════════
// 页面切换 + 动画触发
// ══════════════════════════════════════════════════════
function showPage(id){
  document.querySelectorAll('.nav a').forEach(function(a){a.classList.remove('active');});
  var t=document.querySelector('.nav a[data-target="'+id+'"]');
  if(t)t.classList.add('active');
  var tpl=document.getElementById('tpl-'+id);
  if(!tpl){console.warn('Template not found:',id);return;}
  var host=document.getElementById('page-host');
  if(!host)return;
  host.innerHTML='';
  host.appendChild(document.importNode(tpl.content,true));
  var pageEl=host.firstElementChild;
  if(pageEl)pageEl.classList.add('active');
  delayAnim(host,'.kpi,.hero-kpi,.ring-kpi,.mini-rate,.kpi-row>*',80);
  setTimeout(window.__resizeAllCharts,100);
  window.scrollTo(0,0);
}
// 初始加载第一页（延迟确保 DOM 就绪）
setTimeout(function(){
  var firstTpl=document.querySelector('template[id^="tpl-"]');
  if(firstTpl)showPage(firstTpl.id.replace('tpl-',''));
}, 50);

/* ══════════════════════════════════════════════════════
   数字递增计数（#3）
   ══════════════════════════════════════════════════════ */
function animateNumber(el, target, suffix, duration){
  if(!el) return;
  var start=0;
  var step=Math.max(1, Math.floor(target / (duration/16)));
  var current=start;
  function tick(){
    current+=step;
    if(current>=target){
      el.textContent=target.toLocaleString('zh-CN')+(suffix||'');
      return;
    }
    el.textContent=current.toLocaleString('zh-CN')+(suffix||'');
    requestAnimationFrame(tick);
  }
  tick();
}

/* ══════════════════════════════════════════════════════
   卡片交错入场（#2）
   ══════════════════════════════════════════════════════ */
function delayAnim(container, selector, delayMs){
  if(!container) return;
  var items=container.querySelectorAll(selector);
  items.forEach(function(el,i){
    el.classList.add('anim-fade-up');
    el.style.animationDelay=(i*delayMs)+'ms';
  });
}

// ══════════════════════════════════════════════════════
// Chart.js 全局默认（蓝白主题 + 自定义动画 #6）
// ══════════════════════════════════════════════════════
if(typeof Chart!=='undefined'){
  Chart.defaults.color='#595959';
  Chart.defaults.borderColor='#d4d4d4';
  Chart.defaults.font.family='"Segoe UI","Microsoft YaHei",Arial,sans-serif';
  Chart.defaults.font.size=10;
  Chart.defaults.maintainAspectRatio=false;
  // 自定义图表入场动画
  Chart.defaults.animation={duration:1200,easing:'easeOutQuart'};
}

// ══════════════════════════════════════════════════════
// 图表注册器（直接创建 + 切换时 resize）
// ══════════════════════════════════════════════════════
window.__charts={};
window.__regChart=function(id,config){
  var el=document.getElementById(id);if(!el)return null;
  try{
    var chart=new Chart(el,config);
    window.__charts[id]=chart;
    setTimeout(function(){try{chart.resize();}catch(e){}}, 50);
    return chart;
  }catch(e){
    console.warn('Chart init failed:', id, e);
    return null;
  }
};
window.__resizeAllCharts=function(){
  if(window.__charts)Object.values(window.__charts).forEach(function(c){try{c.resize()}catch(e){}});
};

// ══════════════════════════════════════════════════════
// 自动表格折叠
// ══════════════════════════════════════════════════════
function initTableCollapse(){
  document.querySelectorAll('.page.active .table-wrap').forEach(function(w){
    if(w.classList.contains('_collapsed'))return;
    if(w.classList.contains('no-collapse'))return;
    var h=w.scrollHeight;
    if(h>500){
      w.classList.add('table-collapse','collapsed');
      w.classList.add('_collapsed');
      var ov=document.createElement('div');
      ov.className='collapse-overlay';
      w.appendChild(ov);
      var btn=document.createElement('button');
      btn.className='collapse-btn';
      btn.textContent='展开全部数据 ▾';
      btn.onclick=function(){
        w.classList.toggle('collapsed');
        this.textContent=w.classList.contains('collapsed')?'展开全部数据 ▾':'收起多余 ▴';
      };
      w.parentNode.insertBefore(btn,w.nextSibling);
    }else{
      w.classList.add('_collapsed');
    }
  });
}

// 页面切换时触发
var _origShowPage=showPage;
showPage=function(id){
  _origShowPage(id);
  setTimeout(initTableCollapse,50);
};
setTimeout(initTableCollapse,200);
// 首屏动画
setTimeout(function(){
  var firstPage=document.querySelector('.page.active');
  if(firstPage) delayAnim(firstPage, '.kpi, .hero-kpi, .ring-kpi, .mini-rate, .kpi-row>*', 80);
}, 300);

// ══════════════════════════════════════════════════════
// Tab 切换（统一事件委托 + 淡入 #5）
// ══════════════════════════════════════════════════════
function switchTab(btn){
  var tabId = btn.getAttribute('data-tab');
  if(!tabId) return;
  var container = btn.closest('.yoy-cust-tabs, .cust-tabs');
  if(!container) return;
  container.querySelectorAll('.tab-btn, .cust-tab').forEach(function(b){
    b.classList.remove('active');
  });
  btn.classList.add('active');
  container.querySelectorAll('.tab-panel, [id]').forEach(function(p){
    if(p.classList && p.classList.contains('tab-panel')){
      p.classList.remove('active');
      if(p.id === tabId) p.classList.add('active');
    }
  });
  var target = document.getElementById(tabId);
  if(target){
    if(target.classList.contains('tab-panel')){
      // 已在上面处理
    } else {
      var parent = target.parentElement;
      if(parent){
        Array.from(parent.children).forEach(function(c){
          if(c.id) c.classList.add('hidden');
        });
      }
      target.classList.remove('hidden');
    }
  }
}
// 统一 .cust-tab 事件委托
document.addEventListener('click', function(e){
  var tab = e.target.closest('.cust-tab');
  if(!tab) return;
  // 优先用 data-tab 属性触发 switchTab
  if(tab.getAttribute('data-tab')){
    switchTab(tab);
    return;
  }
  // 否则自动根据 class 切换同容器内的 panel
  var container = tab.closest('.cust-tabs');
  if(!container) return;
  var panels = container.parentElement.querySelectorAll('.tab-panel');
  var m = tab.classList.contains('inc')?'inc':'pay';
  panels.forEach(function(panel){panel.classList.remove('active');});
  var target = container.parentElement.querySelector('.tab-panel.tab-panel-'+m);
  if(target) target.classList.add('active');
});
"""
