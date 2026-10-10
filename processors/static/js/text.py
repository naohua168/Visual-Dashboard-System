# Author: naohua168 <bai_bai168@qq.com>
"""长名称折行 wrapName（与 Python 端 wrap_name 规则一致） —— JS 片段 `text`

由 processors/static/js_vars.py 拆分而来，内容与拆分前逐字节一致；
拼接顺序见 processors/static/js/__init__.py，改动内容请只在本文件里追加。
"""

JS = r"""/* ══════════════════════════════════════════════════════
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

"""
