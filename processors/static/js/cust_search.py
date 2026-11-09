# Author: naohua168 <bai_bai168@qq.com>
"""收入/回款 工具条：Tab 切换 + 客户/子公司搜索 —— JS 片段 `cust_search`

由 components.cust_tab_bar / cust_search_box 生成的 HTML 配套脚本：
  · switchCustTab(el, incId, payId, metric)：切换收入/回款容器，并重算搜索
  · 搜索框过滤「当前可见」那张表：按 tr[data-search]（母公司 + 子公司名）做包含匹配，
    2 个字符起才生效（单字命中太多，反而没法用；口径 2026-11-03 用户确认）
  · 折叠区 tr.row-hidden 在搜索时强制展开，清空后恢复原折叠状态（靠 .cs-searching 类）
  · 无命中时插一行「未找到匹配的客户」，切换 tab 时按新表重算
  · 销售卡3 的表格是 JS 重建的，用 MutationObserver 兜底重新过滤
拼接顺序见 processors/static/js/__init__.py。
"""

JS = r"""// ══════════════════════════════════════════════════════
// 收入/回款 工具条：Tab 切换 + 客户/子公司搜索（2026-11-03）
// ══════════════════════════════════════════════════════
function __csNorm(s){
  return String(s == null ? '' : s)
    .replace(/[\uFF01-\uFF5E]/g, function(ch){ return String.fromCharCode(ch.charCodeAt(0) - 0xFEE0); })
    .replace(/\u3000/g, '')
    .replace(/\s+/g, '')
    .toLowerCase();
}

function __csRows(box){
  return Array.prototype.slice.call(box.querySelectorAll('table tbody tr.row-data'));
}

function __csApply(bar){
  if(!bar){ return; }
  var input = bar.querySelector('[data-cust-search]');
  if(!input){ return; }
  var kw = __csNorm(input.value);
  var ids = String(input.getAttribute('data-targets') || '').split(',');
  var countEl = bar.querySelector('[data-cust-count]');
  var shown = null;

  ids.forEach(function(id){
    id = id.trim();
    if(!id){ return; }
    var box = document.getElementById(id);
    if(!box){ return; }
    var rows = __csRows(box);
    var hit = 0;
    rows.forEach(function(tr){
      if(!kw){ tr.classList.remove('cs-hide'); return; }
      var hay = tr.getAttribute('data-search') || tr.textContent || '';
      var keep = __csNorm(hay).indexOf(kw) >= 0;
      tr.classList.toggle('cs-hide', !keep);
      if(keep){ hit++; }
    });
    box.classList.toggle('cs-searching', !!kw);

    // 空结果提示放在表格【外面】（不改 table/tbody 结构，避免任何列宽/行布局被带偏）
    var note = box.querySelector('.cs-empty-note');
    if(kw && rows.length && hit === 0){
      if(!note){
        note = document.createElement('div');
        note.className = 'cs-empty-note';
        var wrap = box.querySelector('.table-wrap');
        if(wrap && wrap.insertAdjacentElement){
          wrap.insertAdjacentElement('afterend', note);
        } else {
          box.appendChild(note);
        }
      }
      note.textContent = '未找到匹配「' + input.value.trim() + '」的客户';
    } else if(note){
      note.remove();
    }

    if(!shown && !box.classList.contains('hidden')){ shown = {hit: hit, total: rows.length}; }
  });

  if(countEl){ countEl.textContent = (kw && shown) ? (shown.hit + '/' + shown.total) : ''; }
  var clear = bar.querySelector('[data-cust-clear]');
  if(clear){ clear.classList.toggle('is-on', !!kw); }
}

// 供外部（Tab 切换 / 表格重建）重算：不传参=全部重算
window.reapplyCustSearch = function(bar){
  if(bar){ __csApply(bar); return; }
  document.querySelectorAll('.cust-tabs').forEach(__csApply);
};

window.switchCustTab = function(el, incId, payId, metric){
  var bar = el.closest('.cust-tabs');
  var inc = document.getElementById(incId);
  var pay = document.getElementById(payId);
  if(inc){ inc.classList.toggle('hidden', metric !== 'inc'); }
  if(pay){ pay.classList.toggle('hidden', metric !== 'pay'); }
  if(bar){
    bar.querySelectorAll('.cust-tab').forEach(function(t){
      var on = (t === el);
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.setAttribute('tabindex', on ? '0' : '-1');
    });
  }
  // 页面自定义切换（如销售卡3 的 switchSc3Metric）
  var extra = el.getAttribute('data-extra');
  if(extra && typeof window[extra] === 'function'){ window[extra](metric); }
  if(bar){ __csApply(bar); }
};

document.addEventListener('input', function(e){
  var input = (e.target && e.target.closest) ? e.target.closest('[data-cust-search]') : null;
  if(!input){ return; }
  __csApply(input.closest('.cust-tabs'));
});

document.addEventListener('keydown', function(e){
  var tab = (e.target && e.target.closest) ? e.target.closest('.cust-tab') : null;
  if(tab && (e.key === 'Enter' || e.key === ' ')){
    e.preventDefault();
    tab.click();
    return;
  }
  if(e.key !== 'Escape'){ return; }
  var input = (e.target && e.target.closest) ? e.target.closest('[data-cust-search]') : null;
  if(!input){ return; }
  e.preventDefault();
  input.value = '';
  __csApply(input.closest('.cust-tabs'));
  input.blur();
});

document.addEventListener('click', function(e){
  var clear = (e.target && e.target.closest) ? e.target.closest('[data-cust-clear]') : null;
  if(!clear){ return; }
  var bar = clear.closest('.cust-tabs');
  var input = bar ? bar.querySelector('[data-cust-search]') : null;
  if(!input){ return; }
  input.value = '';
  __csApply(bar);
  input.focus();
});

// 表格被脚本重建（销售卡3 切换销售/收入回款）后自动重新过滤
(function(){
  if(typeof MutationObserver === 'undefined'){ return; }
  var queued = false;
  var observer = new MutationObserver(function(){
    if(queued){ return; }
    queued = true;
    setTimeout(function(){
      queued = false;
      document.querySelectorAll('.cust-tabs').forEach(function(bar){
        var input = bar.querySelector('[data-cust-search]');
        if(input && __csNorm(input.value)){ __csApply(bar); }
      });
    }, 0);
  });
  function watch(){
    document.querySelectorAll('[data-cust-search]').forEach(function(input){
      String(input.getAttribute('data-targets') || '').split(',').forEach(function(id){
        var box = document.getElementById(id.trim());
        if(box && !box.__csWatched){
          box.__csWatched = true;
          observer.observe(box, {childList: true, subtree: true});
        }
      });
    });
  }
  function boot(){
    watch();
    document.querySelectorAll('.cust-tabs').forEach(__csApply);
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
"""
