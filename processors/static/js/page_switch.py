# Author: naohua168 <bai_bai168@qq.com>
"""页面切换：交叉淡化 + 逐块浮现 + 首屏加载 —— JS 片段 `page_switch`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""/* 页面切换 — 交叉淡化 + 页内逐块浮现（2026-10-10 定稿，同日二轮性能调优）
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

"""
