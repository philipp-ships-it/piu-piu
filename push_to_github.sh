#!/usr/bin/env bash
# PIU PIU -> GitHub pushen
#
# Variante A (mit GitHub CLI, legt Repo automatisch an):
#     gh auth login
#     ./push_to_github.sh
#
# Variante B (ohne gh): Repo vorher auf https://github.com/new anlegen
#     (LEER lassen: kein README, kein .gitignore, keine Lizenz!)
#     dann:  GH_USER=deinname ./push_to_github.sh

set -e
cd "$(dirname "$0")"

REPO="${REPO:-piu-piu}"
DESC="${DESC:-ASCII-Endlosrunner fuers Terminal. Renn. Spring. Mach piu piu.}"

if [ -z "$(git status --porcelain)" ]; then
  echo "[i] Arbeitsverzeichnis sauber."
else
  echo "[i] Uncommittete Aenderungen -> werden committet."
  git add -A && git commit -m "update"
fi

if command -v gh >/dev/null 2>&1; then
  echo "[1/2] Repo via gh anlegen (falls noch nicht da)..."
  gh repo create "$REPO" --public --source=. --remote=origin \
     --description "$DESC" --push || {
       echo "[i] Repo existiert wohl schon, pushe direkt..."
       git remote get-url origin >/dev/null 2>&1 || \
         git remote add origin "https://github.com/$(gh api user -q .login)/$REPO.git"
       git push -u origin main
     }
  echo "[2/2] GitHub Pages auf /docs aktivieren..."
  USER=$(gh api user -q .login)
  gh api -X POST "repos/$USER/$REPO/pages" \
     -f "source[branch]=main" -f "source[path]=/docs" 2>/dev/null \
     && echo "    -> https://$USER.github.io/$REPO/" \
     || echo "    (Pages ggf. manuell: Settings -> Pages -> main /docs)"
else
  if [ -z "$GH_USER" ]; then
    echo "[!] Kein 'gh' gefunden. Bitte GH_USER setzen:"
    echo "    GH_USER=deinname ./push_to_github.sh"
    exit 1
  fi
  echo "[1/1] Push nach github.com/$GH_USER/$REPO ..."
  git remote get-url origin >/dev/null 2>&1 || \
    git remote add origin "https://github.com/$GH_USER/$REPO.git"
  git branch -M main
  git push -u origin main
  echo
  echo "    Fertig. Pages aktivieren: Settings -> Pages -> Branch main, Ordner /docs"
fi
