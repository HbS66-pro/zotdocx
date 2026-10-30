# Word-side macro: restore superscript citation numbers

`zotdocx patch` makes Zotero write body citations as plain text, which strips `\super`. That removes the "Cannot delete range" error, at the cost of flattening the citation numbers. This macro puts the superscript back.

It only touches citation fields whose code contains `ZOTERO_ITEM`. The bibliography field (`CSL_BIBLIOGRAPHY`) is counted and left alone, so entry numbers never become superscript.

You only need it if you ran `zotdocx patch`. Without the patch, Zotero already renders these numbers as superscript.

## Two modes

| Mode | What to install | When it fixes |
|---|---|---|
| Manual | `docs/macros/ZoteroFixManual.bas` only | Run `ZoteroFixCitationsSuper` (`Alt+F8`) before you submit |
| Automatic | plus `ZoteroFixAuto.bas`, `WordEvents.cls` and the `AutoExec` in `ThisDocument` | Checks every 5 seconds; refresh freely |

The manual mode is simpler, but if the numbers come out flat again after a refresh, run it again. The automatic mode installs once and then keeps up.

## Install (into Normal.dotm, global)

Back up `%APPDATA%\Microsoft\Templates\Normal.dotm` and close every Word window first.

1. Open Word, press `Alt+F11`.
2. In the project tree, right-click `Normal` → **Insert → Module**, paste all of `docs/macros/ZoteroFixManual.bas`.
3. Right-click `Normal` → **Insert → Module**, paste `docs/macros/ZoteroFixAuto.bas`.
4. Right-click `Normal` → **Insert → Class Module**, paste `docs/macros/WordEvents.cls`; rename the class module to `WordEvents` in the Properties window (`F4`).
5. Double-click `ThisDocument` and paste `docs/macros/ThisDocument.txt`.
6. Save (`Ctrl+S`); when Word asks whether to save into Normal.dotm, say yes.
7. Restart Word.

For the manual mode, steps 1–2 are enough; skip 3–7. Do not install `ZoteroFixAuto.bas` on its own — it references the `WordEvents` class and will not compile without it.

Paste the text — do not use **File → Import**. The `.bas` files are UTF-8 while VBE imports with the system code page, which garbles the Chinese comments.

## What it does

- `ZoteroFixCitationsSuper` sets `Result.Font.Superscript = True` on every `ZOTERO_ITEM` field that is not superscript already.
- `ZoteroFixTick` runs every 5 seconds and re-applies the fix as soon as any citation field loses it.
- `ZoteroFixNow` fixes once, silently.
- `ZoteroCitationList` prints each citation and its superscript state to the Immediate window (`Ctrl+G`).
- `ZoteroFixStop` stops the check loop.

## Why a refresh no longer needs attention

The manual mode applies at the moment you run it: if a refresh flattens the numbers again, run it again. The automatic mode removes that decision — the check looks at the active document every 5 seconds and re-applies the superscript as soon as any citation field loses it, so after a refresh you do nothing and still see superscript.

## Verify

```bash
zotdocx status paper.docx
```

```
上标   数字制引注 32 个：整条上标 32 · 整条非上标 0 · 域内混排 0
```

`none` should be 0. A non-zero `mixed` means one field result holds several runs (for example a locator after the number) and needs a look.

`--json` reports `superscript: {numeric, all, none, mixed}`.

## Turn off or remove

- Stop the loop: run `ZoteroFixStop` in the Immediate window (`Ctrl+G`).
- Resume: restart Word, or run `WordEventsKick`.
- Remove: delete both modules and clear `ThisDocument`, then save Normal.dotm.

## Notes

- Normal.dotm is global: the macro applies to every document on this machine. It only changes formatting of `ZOTERO_ITEM` field results, never body text.
- Macros must be allowed: File → Options → Trust Center → Macro Settings. Normal.dotm sits in a trusted location, so this usually needs no change.
- Reinstall after switching machines or reinstalling Office.
