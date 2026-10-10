# Author: naohua168 <bai_bai168@qq.com>
"""表格自动折叠（读取-写入分离） —— JS 片段 `tables`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""// ══════════════════════════════════════════════════════
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

"""
