# Zotero integration patch

`zotdocx patch` reads `<Zotero directory>/app/omni.ja`, rewrites the
`integration.js` inside it, and writes the package back after verifying the
result. It carries no Zotero code: the added snippet is this project's own
MIT-licensed JavaScript (`zotdocx/data/plaintext-fix.js`).

## When it helps

On some Word installations Zotero cannot delete the paragraph mark left by its RTF
block insertion. Zotero then reports **Cannot delete range**; every refresh and
every new citation fails, and citation fields keep breaking.

Numeric styles (GB/T 7714, IEEE, Nature, Vancouver) render citations through that
RTF path, so the body citations are the ones affected. Author–date styles usually
are not.

## What it changes

Two edits inside `integration.js`:

1. one call at the start of `setText` — `<arg> = _zoteroPlainCitationFix(<arg>);`
2. the snippet appended at the end of the file

For a citation that renders to a bare number (`\super [n]\nosupersub{}`), the
snippet writes plain text instead of an RTF block. No RTF block is inserted, so
there is nothing left to delete afterwards. The bibliography block keeps the
normal RTF path.

Trade-off: `\super` is part of what gets stripped, so body citation numbers lose
their superscript. Set superscript back in Word, or accept plain numbers if the
target style allows them.

## Run it

Close Zotero and Word first.

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto
```

Without `--apply` this only reports what would change. To write:

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero" --auto --apply
```

`--apply` backs the package up next to itself as `omni.ja.bak_<timestamp>`,
replaces one entry, works out the rest of the package byte for byte, and verifies
the rebuilt archive before putting it in place. Restart Zotero to load it.

Writing into `Program Files` needs an elevated shell.

## If it stops

`--auto` refuses instead of guessing when:

- `setText` is not where it expects (an unusual Zotero version) — the file is left
  untouched;
- the patch marker is already present — use `--force` to reapply.

For the first case, patch by hand and feed the result back:

1. copy `app/omni.ja` somewhere writable, `Expand-Archive` it as a zip;
2. add the call as the first statement of `setText`, append the snippet from
   `zotdocx/data/plaintext-fix.js` (everything from `function` down);
3. `zotdocx patch --zotero-dir "C:\Program Files\Zotero" --patched <edited integration.js> --apply`

## Check, undo, re-apply

```powershell
zotdocx patch --zotero-dir "C:\Program Files\Zotero"
```

prints the package size and whether the patch marker is present. To undo, copy the
`omni.ja.bak_<timestamp>` file back over `omni.ja`.

A Zotero update replaces `omni.ja`. After each update, run the check again and
re-run `--auto --apply` if the marker is gone.
