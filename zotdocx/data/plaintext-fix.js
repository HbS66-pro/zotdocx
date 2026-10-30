// zotdocx · Zotero Word integration patch (original code, MIT)
//
// Shipped inside the package. `zotdocx patch --auto` appends everything from
// "function" to the end of this file into integration.js and adds one call at
// the start of setText. `zotdocx patch --auto` without --apply only reports.
//
// Why: some Word installations refuse to delete the paragraph mark that Zotero's
//      RTF block insertion leaves behind. Zotero then reports "Cannot delete
//      range", and every refresh or new citation fails. Numeric styles such as
//      GB/T 7714 are rendered through the RTF path, so body citations are what
//      breaks.
//
// How: when a citation renders to a plain number (\super [n]\nosupersub{}), write
//      the text without the RTF wrapper. No RTF block is inserted, so there is
//      nothing left to delete. The bibliography block keeps the normal RTF path.
//
// Cost: the body citation number loses its superscript, because \super is
//       stripped. Set it back in Word, or leave it plain if the style allows.
//
// Recognises: citeproc output for numeric styles, i.e. \super [n]\nosupersub{}.
function _zoteroPlainCitationFix(text) {
  if (typeof text !== "string"
      || text.indexOf("\\super") === -1
      || text.indexOf("\\nosupersub") === -1) {
    return text;
  }
  var p = text;
  // Style-clear control word, e.g. \ulclear{\super [1]\nosupersub{}}
  if (p.indexOf("\\ulclear") === 0) {
    p = p.slice(8);
  }
  // Note whether an RTF wrapper is present before stripping the trailing brace.
  // The header must be "\rtf" followed directly by a space or a control word. A
  // looser pattern such as [^{}]* would consume "\super [1]\nosupersub" as part
  // of the header, so the test is anchored on that control word.
  var hasWrapper = /^\{\\rtf\d?[ \\]/.test(p);
  if (hasWrapper) {
    p = p.replace(/^\{\\rtf(\d)?(\\[a-z]+(\d+)?)*[ ]?/, "");
    p = p.replace(/\}\s*$/, "");
  }
  // Drop empty \nosupersub{} groups first, then any lone \super / \nosupersub
  p = p.replace(/\\nosupersub\s*\{\s*\}/g, "");
  p = p.replace(/\\super\s*/g, "").replace(/\\nosupersub\s*/g, "");
  p = p.replace(/[{}]/g, "").trim();
  // A backslash here means other RTF control words (italic, bold, ...) are still
  // in the string. Keep the original text rather than write control words into
  // the document as literal characters.
  if (p.indexOf("\\") === -1 && p.length) {
    return p;
  }
  return text;
}

Zotero.Integration._plainCitationFix = _zoteroPlainCitationFix;
