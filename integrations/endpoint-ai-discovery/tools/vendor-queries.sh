#!/usr/bin/env bash
# Vendor osquery-ai-discovery's built artifacts at a pinned ref.
#
#     tools/vendor-queries.sh v0.2.0
#     tools/vendor-queries.sh 98eaeca        # a SHA, if no tag carries what you need
#
# WHY VENDOR RATHER THAN SUBMODULE OR FETCH-AT-BUILD. A vendored copy gives reviewable
# diffs, works with no network, and puts the pinned version in the tree where a reader
# sees it. A submodule adds clone and CI friction and is forgotten in exactly the
# situations that matter; fetch-at-build makes an offline build stop working.
#
# WHAT COMES ACROSS, AND WHERE IT GOES. Both halves ride the same ref, because a catalog
# that matched a different revision of the queries is a silent wrong answer:
#
#   bin/      the runner, the Docker guard and the wall-clock bound. Deployed to Macs.
#   dist/     the queries. Deployed to Macs inside the collector script.
#   catalog/  NOT vendored here any more. The signatures are the collector's, and the
#             collector is ml-engine/src/ml_engine/discovery/, which vendors them into
#             its own package because that is what ships in its wheel. A copy here had
#             no consumer once the collector moved: every reference to it in this tree
#             is a guard asserting it must NEVER reach a Mac.
#   tools/bundle.py   the self-extracting bundler, ONE NAMED FILE and not the directory.
#             It runs HERE, at build time, and tools/build-collector.py hands it the
#             Arthur driver. The rest of upstream's tools/ is maintainer tooling for that
#             repo -- catalog validation, coverage reports -- which this repo has no use
#             for and which would drag PyYAML behind it.
#
# The upstream tree is verified before anything is copied: `tools/build.py --check` must
# pass at that ref, or the artifacts do not match the queries that produced them and this
# repo would vendor a lie.
set -uo pipefail

REPO="${VENDOR_REPO:-https://github.com/arthur-ai/osquery-ai-discovery.git}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HERE/vendor/osquery-ai-discovery"

REF="${1:-}"
[ -n "$REF" ] || { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

work="$(mktemp -d "${TMPDIR:-/tmp}/vendor.XXXXXX")" || exit 1
trap 'rm -rf "$work"' EXIT

echo "fetching $REPO at $REF"
git clone --quiet --no-checkout "$REPO" "$work/src" || { echo "clone failed" >&2; exit 1; }
git -C "$work/src" checkout --quiet "$REF" 2>/dev/null || {
  echo "vendor: no such ref: $REF" >&2; exit 1; }

sha="$(git -C "$work/src" rev-parse HEAD)"
# Is the ref an annotated or lightweight tag, or a bare commit? A SHA pin is legitimate
# but provisional, and the VERSION file has to say which it was.
if git -C "$work/src" rev-parse --verify --quiet "refs/tags/$REF" >/dev/null; then
  kind=tag
else
  kind="commit (PROVISIONAL -- pin a tag once one carries this)"
fi

# THE UPSTREAM GATE. dist/ is generated from queries/, and a stale dist/ at that ref means
# the artifacts do not match the SQL. Catching it here is the difference between vendoring
# a mismatch and discovering it on a fleet.
( cd "$work/src" && python3 tools/build.py --check >/dev/null ) || {
  echo "vendor: tools/build.py --check FAILS at $REF -- dist/ does not match queries/." >&2
  echo "        Refusing to vendor artifacts that do not match the SQL that made them." >&2
  exit 1; }

for d in bin dist; do
  [ -d "$work/src/$d" ] || { echo "vendor: $REF has no $d/" >&2; exit 1; }
done

# THE BUNDLER IS REQUIRED, AND A REF WITHOUT ONE IS NAMED AS THE CAUSE. dist/collect.sh is
# built by it now -- this repo stopped carrying its own copy of the extraction preamble --
# so vendoring a ref that predates it would fail later, in build-collector.py, as an import
# error about a path. v0.6.0 is the first release that carries it.
[ -f "$work/src/tools/bundle.py" ] || {
  echo "vendor: $REF has no tools/bundle.py. dist/collect.sh is built by upstream's" >&2
  echo "        bundler, so this repo cannot vendor a ref older than v0.6.0." >&2
  exit 1; }

rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$work/src/bin" "$DEST/bin"
cp -R "$work/src/dist" "$DEST/dist"
mkdir -p "$DEST/tools"
cp "$work/src/tools/bundle.py" "$DEST/tools/bundle.py"
chmod +x "$DEST"/bin/* 2>/dev/null

# Arthur-specific deployment glue must not come across. Upstream has since deleted
# dist/jamf-collect.sh itself -- the seam moved the right way -- so this no longer fires. It
# stays because the boundary belongs in code rather than in a reviewer's memory, and glue is
# exactly the kind of thing that reappears upstream by convenience.
for stray in "$DEST"/dist/jamf-collect.sh "$DEST"/dist/*.plist; do
  [ -e "$stray" ] && { echo "vendor: removing Arthur-specific $(basename "$stray") -- it belongs in this repo, not upstream"; rm -f "$stray"; }
done

# THE TREE IS VERBATIM, AND A MANIFEST IS HOW THAT STAYS TRUE. A repo-wide formatter
# rewrote bin/classify and tools/bundle.py here once, in place, and every test still
# passed -- a vendored program quietly reformatted is no longer the upstream it claims to
# be, and the next re-vendor produces a diff nobody can explain. test/lint.sh checks this.
( cd "$DEST" && find . -type f ! -name VERSION ! -name SHA256SUMS -print0 \
    | sort -z | xargs -0 shasum -a 256 > SHA256SUMS )

cat > "$DEST/VERSION" <<EOF
repo   $REPO
ref    $REF
kind   $kind
sha    $sha
at     $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo
echo "vendored into vendor/osquery-ai-discovery/"
sed 's/^/  /' "$DEST/VERSION"
echo "  files: $(find "$DEST" -type f | wc -l | tr -d ' ')"
echo
echo "next: tools/build-collector.py   (rebuilds the deployable around these)"
