# Author: naohua168 <bai_bai168@qq.com>
"""数字递增计数、卡片交错入场 —— JS 片段 `counters`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""/* ══════════════════════════════════════════════════════
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

"""
