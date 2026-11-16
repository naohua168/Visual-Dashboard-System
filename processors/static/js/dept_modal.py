# Author: naohua168 <bai_bai168@qq.com>
"""部门完成度矩阵 → 客户明细弹窗 —— JS 片段 `dept_modal`

数据：页面内联的 `window.DEPT_CUSTOMERS = {部门: [行, ...]}`
  行 = `[客户, 收入实际, 收入指标, 回款实际, 回款指标]`
       `[客户, 收入实际, 收入指标, 回款实际, 回款指标, [[子公司, 收入实际, 收入指标, 回款实际, 回款指标], ...]]`
（单位万元；客户名已按母公司归拢，子公司明细是归拢前的原始数）

交互：点矩阵里任意部门行（或键盘 Enter/Space）→ 弹窗；客户行带 ▸ 的可展开子公司明细；
搜索框实时过滤（展开状态会被重置）；Esc / 点遮罩 / × 关闭；表头与首列冻结（CSS sticky）。
拼接顺序见 processors/static/js/__init__.py。
"""

JS = r"""// ══════════════════════════════════════════════════════
// 部门完成度矩阵 → 客户明细弹窗
// ══════════════════════════════════════════════════════
var __ddCurrent = '';

// 与矩阵里的部门色点一致
var DD_COLORS = {'检测': '#2563eb', '信息': '#8b5cf6', '能源': '#f59e0b', '海外': '#0d9488'};

function __ddEsc(s){
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function __ddWan(v){
  v = Number(v) || 0;
  return v.toLocaleString('zh-CN', {maximumFractionDigits: 0});
}

// 完成度格：细进度条 + 百分比（色阶口径同矩阵：≥100 绿 / ≥50 橙 / >0 浅橙 / 0 灰）
function __ddPctCell(act, tgt){
  var r = tgt > 0 ? act / tgt : (act > 0 ? 1 : 0);
  if (!r) { return '<td class="dd-rate is-empty">—</td>'; }
  var num = Math.min(r * 100, 100).toFixed(1);
  var cls = r >= 1 ? 'g' : (r >= 0.5 ? 'o' : (r > 0 ? 'l' : 'z'));
  return '<td class="dd-rate">'
    + '<span class="dd-bar"><span class="' + cls + '" style="width:' + num + '%"></span></span>'
    + '<b class="' + cls + '">' + Math.round(r * 100) + '%</b></td>';
}

// 一行 KPI（收入 / 回款）：目标 · 实际 · 完成度 · 缺口
function __ddKpiRow(cls, tag, tgt, act){
  var gap = act - tgt;
  var rate = tgt > 0 ? Math.round(act / tgt * 100) + '%' : '—';
  var cls2 = gap < 0 ? 'is-gap' : 'is-ok';
  var gapTxt = (gap < 0 ? '-' : '+') + __ddWan(Math.abs(gap));
  return '<div class="dk-row ' + cls + '">'
    + '<span class="dk-tag">' + tag + '</span>'
    + '<div class="dk-item"><i>目标</i><b>' + __ddWan(tgt) + '</b></div>'
    + '<div class="dk-item"><i>实际</i><b>' + __ddWan(act) + '</b></div>'
    + '<div class="dk-item"><i>完成度</i><b>' + rate + '</b></div>'
    + '<div class="dk-item"><i>' + (gap < 0 ? '缺口' : '超额') + '</i>'
    + '<b class="' + cls2 + '">' + gapTxt + '</b></div>'
    + '</div>';
}

// 一条明细行（母公司 / 子公司共用）
// 子公司的指标未细分 → 完成度列显示「—」，避免一屏 100% 误导
function __ddDataCells(r, isSub){
  var rate1 = isSub ? '<td class="dd-rate is-empty">—</td>' : __ddPctCell(r[1], r[2]);
  var rate2 = isSub ? '<td class="dd-rate is-empty">—</td>' : __ddPctCell(r[3], r[4]);
  return '<td>' + (r[2] > 0 ? __ddWan(r[2]) : '—') + '</td>'
    + '<td class="dd-strong">' + (r[1] ? __ddWan(r[1]) : '—') + '</td>'
    + rate1
    + '<td>' + (r[4] > 0 ? __ddWan(r[4]) : '—') + '</td>'
    + '<td class="dd-strong">' + (r[3] ? __ddWan(r[3]) : '—') + '</td>'
    + rate2;
}

function openDeptDetail(dept){
  var data = (window.DEPT_CUSTOMERS || {})[dept] || [];
  __ddCurrent = dept;

  var iT = 0, iA = 0, pT = 0, pA = 0;
  data.forEach(function(r){ iA += r[1]; iT += r[2]; pA += r[3]; pT += r[4]; });

  var modal = document.getElementById('deptDetail');
  if (!modal) { return; }
  modal.style.setProperty('--dd-accent', DD_COLORS[dept] || '#2563eb');

  document.getElementById('ddTitle').innerHTML =
    '<span class="dd-dept"><span class="dd-dot"></span>' + __ddEsc(dept) + '</span>'
    + '<span class="dd-sub">客户明细 · 按实际金额降序</span>';
  document.getElementById('ddKpi').innerHTML =
    __ddKpiRow('inc', '收入', iT, iA) + __ddKpiRow('pay', '回款', pT, pA);

  document.getElementById('ddSearch').value = '';
  __ddRender(data, '');

  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.classList.add('dd-lock');
  setTimeout(function(){
    var el = document.getElementById('ddSearch');
    if (el) { el.focus(); }
  }, 30);
}

function __ddRender(data, kw){
  var body = document.getElementById('ddBody');
  var foot = document.getElementById('ddFoot');
  var iT = 0, iA = 0, pT = 0, pA = 0, shown = 0, html = '';

  data.forEach(function(r){
    iT += r[2]; iA += r[1]; pT += r[4]; pA += r[3];
    if (kw && String(r[0]).toLowerCase().indexOf(kw) < 0) { return; }
    shown++;

    var subs = r[5] || [];
    var hasSub = subs.length > 0;
    html += '<tr class="dd-row' + (hasSub ? ' has-sub' : '') + '">'
      + '<td class="dd-cust">'
      + (hasSub
          ? '<button type="button" class="dd-toggle" aria-expanded="false" '
            + 'title="展开子公司明细" onclick="deptDetailToggle(this)">'
            + '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" '
            + 'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
            + '<path d="M9 6l6 6-6 6"/></svg></button>'
          : '<span class="dd-toggle is-empty"></span>')
      + '<span class="dd-name" title="' + __ddEsc(r[0]) + '">' + __ddEsc(r[0]) + '</span>'
      + (hasSub ? '<span class="dd-count">' + subs.length + ' 家子公司</span>' : '')
      + '</td>'
      + __ddDataCells(r)
      + '</tr>';

    subs.forEach(function(s){
      html += '<tr class="dd-subrow">'
        + '<td class="dd-cust dd-sub"><span class="dd-tree">└</span>'
        + '<span class="dd-name" title="' + __ddEsc(s[0]) + '">' + __ddEsc(s[0]) + '</span></td>'
        + __ddDataCells(s, true)
        + '</tr>';
    });
  });

  body.innerHTML = html || '<tr><td colspan="7" class="dd-empty">没有匹配的客户</td></tr>';
  foot.innerHTML = '<tr>'
    + '<td class="dd-cust">合计（' + data.length + ' 家客户）</td>'
    + '<td>' + __ddWan(iT) + '</td>'
    + '<td class="dd-strong">' + __ddWan(iA) + '</td>'
    + __ddPctCell(iA, iT)
    + '<td>' + __ddWan(pT) + '</td>'
    + '<td class="dd-strong">' + __ddWan(pA) + '</td>'
    + __ddPctCell(pA, pT)
    + '</tr>';

  var cnt = document.getElementById('ddCount');
  if (cnt) {
    cnt.textContent = kw ? ('匹配 ' + shown + ' / ' + data.length + ' 家')
                         : ('共 ' + data.length + ' 家客户');
  }
}

// 展开 / 收起某客户的子公司明细
function deptDetailToggle(btn){
  var tr = btn.closest('tr');
  if (!tr) { return; }
  var open = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', open ? 'false' : 'true');
  btn.classList.toggle('is-open', !open);
  var next = tr.nextElementSibling;
  while (next && next.classList.contains('dd-subrow')) {
    next.classList.toggle('is-open', !open);
    next = next.nextElementSibling;
  }
}

function deptDetailFilter(kw){
  var data = (window.DEPT_CUSTOMERS || {})[__ddCurrent] || [];
  __ddRender(data, String(kw || '').trim().toLowerCase());
}

function closeDeptDetail(){
  var el = document.getElementById('deptDetail');
  if (!el) { return; }
  el.classList.remove('open');
  el.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('dd-lock');
}

document.addEventListener('keydown', function(e){
  if (e.key === 'Escape') { closeDeptDetail(); }
});
"""
