#!/usr/bin/env bash
set -euo pipefail

BASE="https://raw.githubusercontent.com/acl-org/acl-style-files/refs/heads/master"

for file in acl.sty acl_natbib.bst acl_latex.tex; do
  if [[ -e "$file" ]]; then
    cp "$file" "$file.bak"
    echo "Backed up existing $file -> $file.bak"
  fi
  curl -fL --retry 3 --connect-timeout 15 "$BASE/$file" -o "$file"
  echo "Downloaded $file"
done

echo
echo "ACL style files are ready."
echo "Compile with: latexmk -pdf paper_acl_blueprint.tex"
