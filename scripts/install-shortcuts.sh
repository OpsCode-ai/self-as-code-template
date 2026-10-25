#!/bin/bash
# One word opens this repo with Claude Code running. Part of every OpsCode pack.
#
#   bash scripts/install-shortcuts.sh             install, or update after a move
#   bash scripts/install-shortcuts.sh --check     say whether it is installed, change nothing
#   bash scripts/install-shortcuts.sh --print     show what it would write, change nothing
#   bash scripts/install-shortcuts.sh --word me   pick the word yourself
#
# The word is `sac` in your private repo and `oac` in a business repo, read from
# .oac/manifest.yml. Open a new Terminal window, type it, press enter: you are in
# this folder with Claude Code running. Add an r (`sacr`) to pick up your last
# conversation instead of starting a new one.
#
# It writes one marked block into the file your shell reads when it starts:
# ~/.zshrc on zsh (every Mac since 2019), ~/.bash_aliases on bash when ~/.bashrc
# reads it, otherwise ~/.bashrc (Linux, and Git Bash on Windows). Running it
# again replaces the block for the same word. A second repo with a different
# word gets its own block beside it. Anything outside the markers is left alone.
#
# Deliberately not here: anything that skips Claude Code's permission prompts.
# Why it exists: the first build-day debrief (25 September 2026). 'Open
# Terminal, type one word, and it opens in the right folder, ready to go.'
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
WORD=""
MODE="install"
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --print) MODE="print" ;;
    --word) shift; WORD="${1:-}" ;;
    --word=*) WORD="${1#--word=}" ;;
    -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1 (try --check, --print or --word)" >&2; exit 2 ;;
  esac
  shift
done

if [ -z "$WORD" ]; then
  plane=""
  if [ -f "$REPO/.oac/manifest.yml" ]; then
    plane="$(sed -n 's/^plane:[[:space:]]*//p' "$REPO/.oac/manifest.yml" | head -1 | tr -d '[:space:]"'"'")"
  fi
  case "$plane" in
    self) WORD="sac" ;;
    *)    WORD="oac" ;;
  esac
fi
if ! printf '%s' "$WORD" | grep -Eq '^[a-z][a-z0-9_]{0,23}$'; then
  echo "the word must be lowercase letters, digits or _, starting with a letter: '$WORD'" >&2
  exit 2
fi
case "$WORD" in
  cd|ls|git|claude|code|python|python3|node|npm|source|exit|open|start)
    echo "'$WORD' is already a command on this computer. Pick another with --word." >&2; exit 2 ;;
esac
case "$REPO" in
  *[\"\$\`\\]*) echo "this folder's path has a character the shortcut cannot carry: $REPO" >&2; exit 2 ;;
esac

BEGIN="# >>> OpsCode: $WORD (managed by install-shortcuts.sh) >>>"
END="# <<< OpsCode: $WORD <<<"
BLOCK="$BEGIN
# Type \`$WORD\` in a new Terminal window: it opens $REPO with Claude Code running.
# \`${WORD}r\` picks up your last conversation there instead.
# Moved the folder? Run again: bash scripts/install-shortcuts.sh
$WORD() { cd \"$REPO\" && claude \"\$@\"; }
${WORD}r() { cd \"$REPO\" && claude --resume \"\$@\"; }
$END"

if [ "$MODE" = "print" ]; then
  printf '%s\n' "$BLOCK"
  exit 0
fi

# The file this person's shell reads when a new window opens.
if [ -n "${SHORTCUTS_FILE:-}" ]; then
  TARGET="$SHORTCUTS_FILE"
elif [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-bash}")" = "zsh" ]; then
  TARGET="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ] && grep -q "bash_aliases" "$HOME/.bashrc"; then
  TARGET="$HOME/.bash_aliases"
else
  TARGET="$HOME/.bashrc"
fi

present=no
current=""
if [ -f "$TARGET" ] && grep -qF -- "$BEGIN" "$TARGET"; then
  present=yes
  current="$(awk -v b="$BEGIN" -v e="$END" '$0==b{f=1} f{print} $0==e{f=0}' "$TARGET")"
fi

if [ "$MODE" = "check" ]; then
  echo "word    : $WORD"
  echo "folder  : $REPO"
  echo "file    : $TARGET"
  if [ "$present" = no ]; then
    echo "status  : not installed (run: bash scripts/install-shortcuts.sh)"; exit 1
  elif [ "$current" = "$BLOCK" ]; then
    echo "status  : installed and current"; exit 0
  else
    echo "status  : installed, but out of date (run it again)"; exit 1
  fi
fi

if [ "$current" = "$BLOCK" ]; then
  echo "already installed: type $WORD in a new Terminal window"
else
  if [ "$present" = yes ]; then
    cp "$TARGET" "$TARGET.bak"
    awk -v b="$BEGIN" -v e="$END" '$0==b{f=1} !f{print} $0==e{f=0}' "$TARGET.bak" > "$TARGET"
  fi
  [ -s "$TARGET" ] && printf '\n' >> "$TARGET"
  printf '%s\n' "$BLOCK" >> "$TARGET"
  echo "installed: open a new Terminal window and type $WORD"
  echo "  it opens $REPO with Claude Code running"
  echo "  ${WORD}r picks up your last conversation there instead"
fi
echo "  to use it in this window now:  source $TARGET"
if ! command -v claude >/dev/null 2>&1; then
  echo "  note: Claude Code is not installed yet, or this window cannot see it; the word works once it is"
fi
