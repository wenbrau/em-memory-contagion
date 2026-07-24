# gdoc — CLI for Google Docs & Drive

A token-efficient CLI designed for AI agents to interact with Google Docs and Google Drive via bash.

## Install

```bash
pip install gdoc
gdoc auth   # OAuth2 flow, stores creds in ~/.config/gdoc/
```

## Design Principles

1. **Token-efficient output** — terse by default, `--json` for machine parsing, `--verbose` for humans
2. **Intuitive verbs** — `ls`, `cat`, `edit`, `write`, `comment` feel like unix commands
3. **Minimal round-trips** — compound operations in single commands where possible
4. **Pipe-friendly** — reads stdin, writes stdout, exits with proper codes

## Command Reference

```
gdoc auth                                    # OAuth2 flow, stores creds in ~/.config/gdoc/
gdoc ls [FOLDER_ID] [--type docs|sheets|all] # List files (default: root)
gdoc find "query"                            # Search by name/content
gdoc cat DOC_ID                              # Export doc as markdown to stdout
gdoc cat DOC_ID --comments                   # Line-numbered with comment annotations
gdoc cat DOC_ID --plain                      # Export as plain text
gdoc cat DOC_ID > local.md                   # Save locally

gdoc edit DOC_ID "old text" "new text"       # Find unique match & replace
gdoc edit DOC_ID "old text" "new text" --all # Replace all occurrences
gdoc write DOC_ID FILE.md                    # Overwrite doc body from local markdown

gdoc comments DOC_ID                         # List open comments
gdoc comments DOC_ID --all                   # Include resolved
gdoc comment DOC_ID "comment text"           # Add unanchored comment
gdoc reply DOC_ID COMMENT_ID "reply text"    # Reply to a comment
gdoc resolve DOC_ID COMMENT_ID              # Resolve a comment
gdoc reopen DOC_ID COMMENT_ID               # Reopen a resolved comment

gdoc info DOC_ID                             # Title, owner, last modified, word count
gdoc share DOC_ID EMAIL [--role reader|writer|commenter]
gdoc new "Document Title" [--folder FOLDER_ID]  # Create blank doc
gdoc cp DOC_ID "Copy Title"                  # Duplicate a doc
```

## Annotated View: `cat --comments`

Output uses line-numbered format with comment annotations on un-numbered lines. Numbered lines = content, un-numbered = metadata.

```bash
$ gdoc cat 1aBcDeFg --comments
--- no changes ---
     1	# Q3 Planning Doc
     2
     3	We need to ship the roadmap by end of month.
      	  [#1 open] alice@co.com on "ship the roadmap":
      	    "This paragraph needs a citation"
      	    > bob@co.com: "Done, added the citation"
     4
     5	The budget is $2M for infrastructure.
      	  [#3 open] carol@co.com on "budget is $2M":
      	    "Can we add metrics here?"
```

## Awareness System

Every command first checks what changed since the last interaction:

```bash
$ gdoc edit 1aBcDeFg "old text" "new text"
--- since last interaction (3 min ago) ---
 ✎ doc edited by alice@co.com (v847 → v851)
 💬 new comment #3 by carol@co.com: "Can we add metrics here?"
 ↩ new reply on #1 by bob@co.com: "Done, added the citation"
 ✓ comment #2 resolved by alice@co.com
---
OK replaced 1 occurrence
```

```bash
$ gdoc cat 1aBcDeFg
--- no changes ---
# Q3 Planning Doc
...
```

### Notification Types

| Symbol | Meaning |
|--------|---------|
| `✎` | Doc body edited |
| `💬` | New comment |
| `↩` | New reply on existing comment |
| `✓` | Comment resolved |
| `↺` | Comment reopened |

### Conflict Warning

If the doc was edited since your last `cat`, `edit` warns you. `write` (full overwrite) blocks unless you pass `--force`.

### `--quiet` Flag

Skips the pre-flight check entirely — saves 2 API calls. Use for batch operations.

## Output Examples

```bash
$ gdoc ls
ID                             TITLE                    MODIFIED
1aBcDeFgHiJkLmNoPqRsTuVwXyZ   Q3 Planning Doc          2025-01-15

$ gdoc comments 1aBcDeFg
#1 [open] alice@co.com 2025-01-15
  "This paragraph needs a citation"
  → bob@co.com: "Added, see line 42"

$ gdoc edit 1aBcDeFg "finalize the roadmap" "ship the roadmap"
OK replaced 1 occurrence

$ gdoc resolve 1aBcDeFg 1
OK resolved comment #1

$ gdoc info 1aBcDeFg --json
{"id":"1aBcDeFg","title":"Q3 Planning Doc","owner":"alice@co.com","modified":"2025-01-15T10:30:00Z"}
```

## URL-to-ID Resolution

Accepts both raw IDs and full URLs:

```bash
gdoc cat 1aBcDeFgHiJkLmNoPqRsTuVwXyZ
gdoc cat "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit"
```

## Error Codes

```
ERR: file not found (404)
ERR: no match found for "text not in doc"
ERR: multiple matches (3 found). Use --all to replace all occurrences.
```

Exit codes: 0=success, 1=API error, 2=auth error, 3=usage error

## Key Notes

- **`edit` is the workhorse** — mirrors Claude Code's Edit tool. `cat` the doc, find the text, `edit` with an exact unique match.
- **`write` is destructive** — full doc replacement. Prefer `edit` for targeted edits.
- **Markdown export is native** — Drive API supports `text/markdown` export natively.
- **Comments use Drive API** — not Docs API. CRUD on comments is exclusively through Drive API v3.
