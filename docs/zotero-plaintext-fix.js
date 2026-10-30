// zotdocx · Zotero Word 集成补丁片段（原创代码，MIT）
//
// 背景：本机 Word 拒绝删除「RTF 块插入后多出来的段落标记」，Zotero 插件因此报
//       「无法删除范围」，刷新/插入引用必失败。GB/T 7714 数字制、引用号上标的样式
//       恰好走 RTF 路径，所以只有正文引注受影响。
//
// 办法：让正文引注改走纯文本写入（不触发 RTF 块插入），参考文献表的整块 RTF 不受影响。
//       代价是正文引用号失去上标，需要在 Word 侧补回（见 README）。
//
// 用法（不改 Zotero 源码文件结构，只加两处）：
//   1) 取出 <Zotero 目录>/app/omni.ja 里的 chrome/content/zotero/xpcom/integration.js；
//   2) 在 setText 实现的开头加一行：
//          text = _zoteroPlainCitationFix(text);
//   3) 在文件末尾追加本文件从 function 开始的全部内容；
//   4) 用 zotdocx patch --patched <改好的 integration.js> --apply 写回并自检。
//
// 识别特征：citeproc 为数字制渲染出的 \super [n]\nosupersub{}。
function _zoteroPlainCitationFix(text) {
  if (typeof text !== "string"
      || text.indexOf("\\super") === -1
      || text.indexOf("\\nosupersub") === -1) {
    return text;
  }
  var p = text;
  // 延迟更新样式清除控制字（形如 \ulclear{\super [1]\nosupersub{}}）
  if (p.indexOf("\\ulclear") === 0) {
    p = p.slice(8);
  }
  // 先记录有没有整块 RTF 外壳，再决定要不要剥结尾的 }。
  // 注意：RTF 头必须是 "\rtf" 后紧跟一个反斜杠控制字（穷尽 1~4 个反斜杠都兼容）；
  // 若写成 [^{}]*，会把 \super [1]\nosupersub 一路吃进"头"里，实测踩过这个坑。
  var hasWrapper = /^\{\\rtf\d?[ \\]/.test(p);
  if (hasWrapper) {
    p = p.replace(/^\{\\rtf(\d)?(\\[a-z]+(\d+)?)*[ ]?/, "");
    p = p.replace(/\}\s*$/, "");
  }
  // 先整体删掉 \nosupersub{} 空组，再清掉单独出现的 \super / \nosupersub
  p = p.replace(/\\nosupersub\s*\{\s*\}/g, "");
  p = p.replace(/\\super\s*/g, "").replace(/\\nosupersub\s*/g, "");
  p = p.replace(/[{}]/g, "").trim();
  // 若仍残留反斜杠，说明还有别的 RTF 控制字（斜体/粗体等）—— 保守起见不改写，
  // 宁可这条走原来的 RTF 路径，也不要把控制字当文字写进文档。
  if (p.indexOf("\\") === -1 && p.length) {
    return p;
  }
  return text;
}

Zotero.Integration._plainCitationFix = _zoteroPlainCitationFix;
