# Zotero integration patch

`zotdocx patch` inspects `<Zotero directory>/app/omni.ja` and can write back an
`integration.js` that you have edited yourself. It does not ship Zotero code, and
it changes nothing until you pass `--apply`.

The snippet it refers to is [`zotero-plaintext-fix.js`](zotero-plaintext-fix.js)
in this directory. The steps below are the whole procedure.

## When it helps

On some Word installations Zotero cannot delete the paragraph mark left by its RTF
block insertion. Zotero then reports **Cannot delete range**; every refresh and
every new citation fails, and citation fields keep breaking.

Numeric styles (GB/T 7714, IEEE, Nature, Vancouver) render citations through that
RTF path, so the body citations are the ones affected. Author–date styles usually
are not.

## What the snippet does

Zotero's Word integration writes citation text in two forms: an RTF block, or plain
text. The snippet watches the text about to be written. When it is a bare number
(`\super [n]\nosupersub{}`), it strips the RTF wrapper and writes plain text
instead, so no RTF block is inserted and there is nothing to delete afterwards.
The bibliography block is left on the normal RTF path.

Trade-off: `\super` is part of what gets stripped, so body citation numbers lose
their superscript. Set superscript back in Word, or accept plain numbers if the
target style allows them.

## Steps

Close Word first.

### 1. Extract integration.js

```powershell
$omni = "$env:ProgramFiles\Zotero\app\omni.ja"
Copy-Item $omni "$env:TEMP\omni.zip" -Force
Expand-Archive "$env:TEMP\omni.zip" "$env:TEMP\omni" -Force
```

The file you want is `$env:TEMP\omni\chrome\content\zotero\xpcom\integration.js`.

### 2. Edit it

In a text editor:

- find the `setText` implementation and add this as its first statement

  ```js
  text = _zoteroPlainCitationFix(text);
  ```

- append the snippet — everything from `function` to the end of
  `zotero-plaintext-fix.js` — at the end of the file

### 3. Write it back

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --patched "$env:TEMP\omni\chrome\content\zotero\xpcom\integration.js"
```

Without `--apply` this is a dry run. With `--apply` the original `omni.ja` is
backed up next to itself as `omni.ja.bak_<timestamp>`, one entry is replaced, the
rebuilt package is verified, and Zotero is restarted by you.

Writing into `Program Files` needs an elevated shell.

## Check, undo, re-apply

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero"
```

prints the package size and whether the patch marker is present. To undo, copy
the `omni.ja.bak_<timestamp>` file back over `omni.ja`.

A Zotero update replaces `omni.ja`. After each update, run the check again and
repeat step 3 if the marker is gone.
