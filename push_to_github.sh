#!/usr/bin/env bash
# ============================================================
#  PIU PIU  ->  GitHub
# ============================================================
#
#  VARIANTE A - mit GitHub CLI (am einfachsten, legt Repo selbst an)
#      gh auth login
#      ./push_to_github.sh
#
#  VARIANTE B - ohne gh
#      1. Repo anlegen: https://github.com/new
#         Name: piu-piu   |   WICHTIG: komplett LEER lassen
#         (kein README, kein .gitignore, keine Lizenz!)
#      2. GH_USER=deinname ./push_to_github.sh
#
# ============================================================
set -e
cd "$(dirname "$0")"

REPO="${REPO:-piu-piu}"
DESC="${DESC:-ASCII-Endlosrunner fuers Terminal. Renn. Spring. Mach piu piu.}"

say(){ printf '\n\033[96m==> %s\033[0m\n' "$1"; }
ok(){  printf '\033[92m    %s\033[0m\n' "$1"; }
err(){ printf '\033[91m[!] %s\033[0m\n' "$1"; }

# --- 0. Repo-Zustand -----------------------------------------
[ -d .git ] || { err "Kein git-Repo hier."; exit 1; }
git branch -M main

if [ -n "$(git status --porcelain)" ]; then
  say "Uncommittete Aenderungen gefunden -> werden committet"
  git add -A
  git commit -m "update"
fi
ok "$(git rev-list --count HEAD) Commits bereit auf 'main'"

# --- 1. Push -------------------------------------------------
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  USER=$(gh api user -q .login)
  say "GitHub CLI erkannt (angemeldet als $USER)"

  if gh repo view "$USER/$REPO" >/dev/null 2>&1; then
    ok "Repo $USER/$REPO existiert bereits"
    git remote get-url origin >/dev/null 2>&1 \
      || git remote add origin "https://github.com/$USER/$REPO.git"
    git push -u origin main
  else
    say "Lege Repo $USER/$REPO an und pushe"
    gh repo create "$REPO" --public --source=. --remote=origin \
       --description "$DESC" --push
  fi

  say "Aktiviere GitHub Pages (main /docs)"
  gh api -X POST "repos/$USER/$REPO/pages" \
     -f "source[branch]=main" -f "source[path]=/docs" >/dev/null 2>&1 \
    && ok "Pages aktiv" \
    || ok "Pages evtl. schon aktiv (sonst: Settings -> Pages -> main /docs)"

  # Platzhalter im README/HTML auf echten Namen setzen
  if grep -q "USER" README.md 2>/dev/null; then
    say "Setze Platzhalter USER -> $USER"
    sed -i.bak "s|USER|$USER|g" README.md docs/index.html && rm -f README.md.bak docs/index.html.bak
    git add -A && git commit -m "Links auf $USER angepasst" && git push
  fi

  echo
  ok "FERTIG"
  ok "Repo : https://github.com/$USER/$REPO"
  ok "Page : https://$USER.github.io/$REPO/  (braucht 1-2 Min)"

else
  if [ -z "$GH_USER" ]; then
    err "Kein 'gh' oder nicht angemeldet."
    echo
    echo "  Option 1:  gh auth login   und Skript nochmal starten"
    echo "  Option 2:  Repo leer anlegen auf https://github.com/new (Name: $REPO)"
    echo "             dann:  GH_USER=deinname ./push_to_github.sh"
    exit 1
  fi

  say "Pushe nach github.com/$GH_USER/$REPO"
  git remote get-url origin >/dev/null 2>&1 \
    || git remote add origin "https://github.com/$GH_USER/$REPO.git"
  git push -u origin main

  say "Setze Platzhalter USER -> $GH_USER"
  sed -i.bak "s|USER|$GH_USER|g" README.md docs/index.html 2>/dev/null || true
  rm -f README.md.bak docs/index.html.bak
  if [ -n "$(git status --porcelain)" ]; then
    git add -A && git commit -m "Links auf $GH_USER angepasst" && git push
  fi

  echo
  ok "FERTIG"
  ok "Repo : https://github.com/$GH_USER/$REPO"
  echo
  echo "  Pages noch aktivieren:"
  echo "    Settings -> Pages -> Source: main, Ordner /docs"
  echo "    danach: https://$GH_USER.github.io/$REPO/"
fi
