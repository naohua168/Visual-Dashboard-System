# Author: naohua168 <bai_bai168@qq.com>
"""Chart.js 全局默认、图表注册与批量 resize —— JS 片段 `charts`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""// ══════════════════════════════════════════════════════
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

"""
