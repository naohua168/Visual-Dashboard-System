# Author: naohua168 <bai_bai168@qq.com>
"""Tab 切换与 .cust-tab 事件委托 —— JS 片段 `tabs`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""// ══════════════════════════════════════════════════════
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
