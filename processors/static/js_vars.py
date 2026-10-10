# Author: naohua168 <bai_bai168@qq.com>
"""看板全局 JS 常量 — 从 base.py 拆分"""
GLOBAL_JS = """
// ══════════════════════════════════════════════════════
// 页面切换 + 动画触发
// ══════════════════════════════════════════════════════
/* 导航下划线：跟随 active 项滑动（位置由 offsetLeft/Width 决定，手机横滑时跟着滚） */
function moveNavUnderline(){
  var nav=document.querySelector('.nav');
  if(!nav) return;
  var link=nav.querySelector('.nav-link.active');
  if(!link) return;
  var bar=nav.querySelector('.nav-underline');
  if(!bar){
    bar=document.createElement('span');
    bar.className='nav-underline';
    bar.style.transition='none';       // 首次出现直接落位，不做位移动画
    nav.appendChild(bar);
    bar.style.left=link.offsetLeft+'px';
    bar.style.width=link.offsetWidth+'px';
    requestAnimationFrame(function(){bar.style.transition='';});
    return;
  }
  bar.style.left=link.offsetLeft+'px';
  bar.style.width=link.offsetWidth+'px';
}

/* 页面切换 — 交叉淡化 + 页内逐块浮现（2026-10-10 定稿，同日二轮性能调优）
   做法：
     1) 新页先挂到旧页「下面」（旧页绝对定位 + 不透明底色盖在上面）
     2) 旧页 240ms 淡出 → 新页被逐渐揭开，全过程没有空白帧（此前"淡出→换内容→淡入"中间全白 = 白屏）
     3) 新页最上面 4 块逐个浮现（.anim-block，45ms 错峰）→ 数据是"逐渐加载"出来的，不是突然蹦出
   性能要点（大表格页面不掉帧的关键）：
     · 新旧两页在过渡期间都提到独立合成层（will-change:opacity）→ 整页淡化由合成器完成，
       不再逐帧把整页大表格重新栅格化
     · 只动 opacity/transform，绝不触发重排；表格折叠在同帧完成，图表重算挪到过渡结束后
   instant=true 或系统开启"减少动态效果"时直接切换 */
var _switchToken=0;   // 连点导航时作废上一次未落地的切换（见下方 requestAnimationFrame）
function showPage(id, instant){
  var tpl=document.getElementById('tpl-'+id);
  if(!tpl){console.warn('Template not found:',id);return;}
  var host=document.getElementById('page-host');
  if(!host)return;
  var token=++_switchToken;   // 每次调用都作废上一次还没落地的切换
  // 导航高亮先切（点击手感立刻有反馈），下划线滑动跟随
  document.querySelectorAll('.nav .nav-link').forEach(function(a){a.classList.remove('active');});
  var t=document.querySelector('.nav .nav-link[data-target="'+id+'"]');
  if(t)t.classList.add('active');
  moveNavUnderline();

  // 收尾上一次可能还没播完的切换：只保留最后一页作为"当前页"，
  // 其余残留页立即摘掉（连点导航时若不清理，容器里会堆着两三页 → 版面错乱/卡顿）
  var kids=[].slice.call(host.children);
  if(kids.length>1){
    kids.slice(0,-1).forEach(function(el){el.remove();});
    kids=[].slice.call(host.children);
  }
  if(kids.length===1) kids[0].classList.remove('page-leaving');

  var oldEl=kids.length?kids[kids.length-1]:null;
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var mount=function(){
    var node=document.importNode(tpl.content,true);
    var newEl=node.firstElementChild;
    if(newEl)newEl.classList.add('active');
    host.appendChild(node);
    if(typeof initTableCollapse==='function') initTableCollapse();   // 同帧折叠，动画途中不改版面
    // 顶层区块逐个浮现（"逐渐加载"）：只给最上面的 4 块，0/45/90/135ms 错峰。
    // 为什么限量（2026-10-10 二轮调优）：被动画的区块每帧都要重绘，
    // 本项目每页都是"超宽密集表"，动 15+ 个块等于每帧重绘整页 → 切换明显掉帧；
    // 前 4 块正好是首屏可见的横幅/指标/头图，下面的大表格直接出现更稳也更快。
    if(newEl && !instant && !reduce){
      var n=0;
      [].slice.call(newEl.children).forEach(function(el){
        if(n>=4) return;
        // 遮罩/弹窗/抽屉等覆盖层不参与浮现（2026-10-10）：
        // 它们默认 opacity:0 靠类名显隐，被淡入就会把整页压黑 —— 销售页那张全屏黑遮罩
        // （#salesModalOverlay rgba(0,0,0,.35)）就是这样被"淡入"的，切页时页面突然变黑。
        var cls=(el.className&&typeof el.className==='string')?el.className:'';
        if(/overlay|modal|backdrop|drawer|pnd-|mask/i.test(cls+' '+el.id)) return;
        if(getComputedStyle(el).position==='fixed') return;
        el.classList.add('anim-block');
        el.style.animationDelay=(n*45)+'ms';
        n++;
      });
    }
    // 新页在过渡期间也提到独立合成层：整页淡入若要逐帧重绘大表格，同样会掉帧
    if(newEl && !instant && !reduce) newEl.style.willChange='opacity';
    setTimeout(function(){
      if(newEl) newEl.style.willChange='';
      window.__resizeAllCharts();                                     // 图表重算放到淡化结束后
    },340);
    window.scrollTo(0,0);
  };

  if(!oldEl||instant||reduce){ host.innerHTML=''; mount(); return; }

  // 让浏览器先把"导航高亮 + 下划线"画出来，再开始换页：
  // 换页要解析/排版整页大表格（几十毫秒的长任务），同步做会把点击反馈一起拖住 → 用户觉得"卡在点击上"。
  // 拆成两步后点下去立刻有反馈，重活让给下一轮事件循环。
  // 用 setTimeout 而不是 requestAnimationFrame：rAF 在后台标签/无头预览里可能不触发，
  // 那样会变成"点了导航没反应"（本轮实测确认过），setTimeout 一定会执行。
  setTimeout(function(){
    if(token!==_switchToken||!oldEl.parentNode) return;   // 期间又点了别的页 → 本次作废
    oldEl.classList.add('page-leaving');    // 变成不透明遮罩，盖在新页上方（淡出 0.24s，含 30% 保持段）
    mount();                                // 新页挂在下层（此刻就被渲染好，但没有空白期）
    setTimeout(function(){
      if(oldEl.parentNode===host) oldEl.remove();   // 等遮罩淡完再摘掉，避免提前移除出现闪断
    },260);
  },0);
}
window.addEventListener('resize',function(){setTimeout(moveNavUnderline,60);});
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
    // 错峰封顶 20 项：长列表（销售/部门几十行）原来会一路排队浮现 1~2 秒，既拖沓又一直重绘（卡顿+眼晕）
    el.style.animationDelay=(Math.min(i,20)*delayMs)+'ms';
  });
}

/* ══════════════════════════════════════════════════════
   长名称折行（生成层统一出口）
   规则与 Python 端 processors/utils.py::wrap_name 完全一致：
   - 每行最多 w 字（默认 20）
   - 优先在自然断点断开：、，）空格等归上一行；左括号归下一行
   - 找不到断点则按 w 硬切
   仅用于**展示**；属性值（data-sub / onclick / title）仍须用原始名称
   ══════════════════════════════════════════════════════ */
function wrapName(s, w){
  w = w || 20;
  s = (s === null || s === undefined) ? '' : String(s).trim();
  if(s.length <= w) return s;
  var AFTER  = "、，,；;）)】」》 　·-—_/";
  var BEFORE = "（(【「《";
  var out = [], rest = s;
  while(rest.length > w){
    var win = rest.slice(0, w), cut = -1;
    for(var i = win.length - 1; i >= Math.max(Math.floor(win.length / 3), 1); i--){
      var ch = win.charAt(i);
      if(AFTER.indexOf(ch) >= 0){ cut = i + 1; break; }
      if(BEFORE.indexOf(ch) >= 0){ cut = i; break; }
    }
    if(cut <= 0) cut = w;
    out.push(rest.slice(0, cut));
    rest = rest.slice(cut);
  }
  out.push(rest);
  return out.join('<br>');
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
  // 自定义图表入场动画（Apple 风格：更快，EaseOutQuint）
  Chart.defaults.animation={duration:800,easing:'easeOutQuint'};
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
  var wraps=[];
  document.querySelectorAll('.page.active .table-wrap').forEach(function(w){
    if(w.classList.contains('_collapsed'))return;
    if(w.classList.contains('no-collapse'))return;
    wraps.push(w);
  });
  if(!wraps.length)return;
  // 读-写分离（2026-10-10 二轮调优）：原来"读一个 scrollHeight → 立刻改一次 DOM"交替进行，
  // 每次读都会把刚写完的整页重新排版一遍（N 张表 = N 次整页重排），换页长任务主要来自这里。
  // 现在先把高度一次性读完，再集中写 class/按钮。
  var heights=wraps.map(function(w){return w.scrollHeight;});
  wraps.forEach(function(w,i){
    if(heights[i]>500){
      w.classList.add('table-collapse','collapsed','_collapsed');
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

// 页面切换后兜底折叠（主体折叠已在 showPage 换页同帧完成，这里只在淡化结束后再确认一次）
var _origShowPage=showPage;
showPage=function(id){
  _origShowPage(id);
  setTimeout(initTableCollapse,320);
};
setTimeout(initTableCollapse,200);
// 首屏：区块逐个浮现由 showPage→mount() 统一负责（.anim-block），这里不再单独做逐项错峰，
// 避免与页面级的浮现叠加成"一直在动"的观感

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
