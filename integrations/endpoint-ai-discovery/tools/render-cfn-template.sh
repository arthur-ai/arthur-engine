#!/usr/bin/env bash
# Print the EC2 CloudFormation template pinned to one arthur-engine ref, ready for
# `aws cloudformation deploy --template-file` or `create-stack-set --template-body file://`.
#
#   tools/render-cfn-template.sh [REF]      # REF defaults to the commit checked out
#
# The file URL gets REF, and every file the install script fetches gets the sha256 of the bytes
# REF holds, read out of git rather than off the working tree: the script refuses a file whose
# checksum does not match, so an uncommitted edit would pin bytes that no URL serves. The
# template itself is REF's copy too. REF must be pushed to GitHub for raw.githubusercontent.com
# to serve it, unless the stack's FileBaseUrl names a mirror of it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TREE="integrations/endpoint-ai-discovery"
TEMPLATE="deploy/arthur-ai-discovery.cfn.yaml"
BASE="https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/$TREE"
# fetch SOURCE DESTINATION MODE PLACEHOLDER, the shape the template's comment promises.
FETCH='^[[:space:]]*fetch[[:space:]]+([^[:space:]]+)[[:space:]]+[^[:space:]]+[[:space:]]+[0-7]+[[:space:]]+(SHA256_[A-Z]+)$'

die() { echo "render-cfn-template: $*" >&2; exit 1; }

ref="${1:-HEAD}"
commit="$(git -C "$ROOT" rev-parse --verify --quiet "$ref^{commit}")" \
  || die "$ref is not a commit in this clone; fetch it first (git fetch --tags)"
# A tag stays readable in the URL; anything else is pinned to its commit, because a branch
# moves and the checksums would stop matching what it serves.
if git -C "$ROOT" show-ref --verify --quiet "refs/tags/$ref"; then pin="$ref"; else pin="$commit"; fi

template="$(git -C "$ROOT" cat-file blob "$commit:$TREE/$TEMPLATE" 2>/dev/null)" \
  || die "$ref has no $TREE/$TEMPLATE; render a ref that carries it"

# Held until the whole template has rendered: a failure part-way would otherwise leave a
# shorter template in the redirect target, which may still deploy and install less.
out=""
urls=0
fetches=0
while IFS= read -r line; do
  if [[ "$line" =~ $FETCH ]]; then
    src="${BASH_REMATCH[1]}"
    placeholder="${BASH_REMATCH[2]}"
    git -C "$ROOT" cat-file -e "$commit:$TREE/$src" 2>/dev/null || die "$ref has no $TREE/$src"
    sum="$(git -C "$ROOT" cat-file blob "$commit:$TREE/$src" | shasum -a 256 | cut -d' ' -f1)"
    line="${line%"$placeholder"}$sum"
    fetches=$((fetches + 1))
  else
    case "$line" in
      *"$BASE")
        line="${line%"$BASE"}https://raw.githubusercontent.com/arthur-ai/arthur-engine/$pin/$TREE"
        urls=$((urls + 1))
        ;;
      *"/COMMIT/"*) die "a URL is not $BASE, so it cannot be pinned: $line" ;;
      *SHA256_*) die "a checksum placeholder outside a fetch line: $line" ;;
    esac
  fi
  out="$out$line"$'\n'
done <<<"$template"
[ "$urls" -gt 0 ] || die "no line ends in $BASE, so nothing names where the files are"
[ "$fetches" -gt 0 ] || die "no fetch line, so nothing is pinned"
printf '%s' "$out"
