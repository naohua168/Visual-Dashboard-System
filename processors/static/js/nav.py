# Author: naohua168 <bai_bai168@qq.com>
"""导航下划线跟随（含 resize 重算） —— JS 片段 `nav`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""
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

"""
