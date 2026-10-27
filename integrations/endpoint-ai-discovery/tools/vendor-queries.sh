#!/usr/bin/env bash
# Vendor ai-detection-spec's osquery binding -- its built artifacts -- at a pinned ref.
#
#     tools/vendor-queries.sh v0.16.2
#     tools/vendor-queries.sh 98eaeca        # a SHA, if no tag carries what you need
#
# WHY VENDOR RATHER THAN SUBMODULE OR FETCH-AT-BUILD. A vendored copy gives reviewable
# diffs, works with no network, and puts the pinned version in the tree where a reader
# sees it. A submodule adds clone and CI friction and is forgotten in exactly the
# situations that matter; fetch-at-build makes an offline build stop working.
#
# WHAT COMES ACROSS, AND WHERE IT GOES. Upstream keeps the osquery binding under osquery/;
# it lands here flattened, because tools/bundle.py packs the tree it sits in:
#
#   osquery/bin/   -> bin/    the runner, the Docker guard and the wall-clock bound.
#                             Deployed to every endpoint.
#   osquery/dist/  -> dist/   the queries. Deployed inside the collector script.
#   osquery/tools/bundle.py -> tools/bundle.py   the self-extracting bundler, ONE NAMED
#                             FILE and not the directory. It runs HERE, at build time, and
#                             tools/build-collector.py hands it the Arthur driver. The rest
#                             of upstream's tools is maintainer tooling for that repo.
#
# NOT the catalog, and NOT bin/classify, the matcher at the top of upstream's tree. Both are
# the collector's, and the collector is ml-engine/src/ml_engine/discovery/, which vendors
# them into its own package because that is what ships in its wheel. Both halves must ride
# the same ref -- a catalog that matched a different revision of the queries is a silent
# wrong answer -- so ml-engine/scripts/vendor_ai_detection_spec.py reads the ref from the
# VERSION this writes, and ml-engine's test_vendor_parity.py asserts that they match.
#
# The upstream tree is verified before anything is copied: `osquery/tools/build.py --check`
# must pass at that ref, or the artifacts do not match the queries that produced them and
# this repo would vendor a lie.
set -uo pipefail

REPO="${VENDOR_REPO:-https://github.com/arthur-ai/ai-detection-spec.git}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HERE/vendor/ai-detection-spec"

REF="${1:-}"
[ -n "$REF" ] || { sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

# THE OTHER HALF COMES FROM GITHUB. ml-engine/scripts/vendor_ai_detection_spec.py reads the
# repo from the VERSION written below and takes the catalog and matcher from that repo's
# release at this ref. A repo it cannot fetch from leaves the two trees at different refs,
# so refuse it here, before anything is cloned or cleared.
case "$REPO" in
  https://github.com/*) ;;
  *)
    echo "vendor: $REPO is not an https://github.com/ URL, which ml-engine needs to fetch the" >&2
    echo "        catalog and matcher from the same release. Set VENDOR_REPO to that form, or unset it." >&2
    exit 1 ;;
esac

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

# THE BINDING MUST BE WHERE THIS SCRIPT COPIES FROM, AND A REF WITHOUT IT IS NAMED AS THE
# CAUSE. v0.15.0 moved the scanner under osquery/ and renamed the bundler's driver interface
# to AI_DETECTION_SPEC_ROOT, which tools/build-collector.py's driver reads. An older ref has
# neither, so vendoring one would fail later, as an import error about a path or a driver that
# exits 1 on every endpoint.
for p in osquery/bin osquery/dist osquery/tools/bundle.py osquery/tools/build.py; do
  [ -e "$work/src/$p" ] || {
    echo "vendor: $REF has no $p. This repo vendors the osquery binding as" >&2
    echo "        ai-detection-spec lays it out, so it cannot vendor a ref older than v0.15.0." >&2
    exit 1; }
done

# THE UPSTREAM GATE. dist/ is generated from queries/, and a stale dist/ at that ref means
# the artifacts do not match the SQL. Catching it here is the difference between vendoring
# a mismatch and discovering it on a fleet.
( cd "$work/src" && python3 osquery/tools/build.py --check >/dev/null ) || {
  echo "vendor: osquery/tools/build.py --check FAILS at $REF -- dist/ does not match queries/." >&2
  echo "        Refusing to vendor artifacts that do not match the SQL that made them." >&2
  exit 1; }

# FROM HERE THE DESTINATION IS GONE, SO A FAILED COPY MUST NOT REACH THE MANIFEST. A
# partial tree with SHA256SUMS written over it is one test/lint.sh certifies as verbatim --
# the integrity check approving the defect it exists to catch.
fatal() { echo "vendor: $1" >&2; echo "        $DEST is now incomplete; re-run this script." >&2; exit 1; }

rm -rf "$DEST" || fatal "could not clear the destination"
mkdir -p "$DEST" || fatal "could not create the destination"
cp -R "$work/src/osquery/bin" "$DEST/bin" || fatal "could not copy osquery/bin/"
cp -R "$work/src/osquery/dist" "$DEST/dist" || fatal "could not copy osquery/dist/"
mkdir -p "$DEST/tools" || fatal "could not create tools/"
cp "$work/src/osquery/tools/bundle.py" "$DEST/tools/bundle.py" || fatal "could not copy bundle.py"
chmod +x "$DEST"/bin/* 2>/dev/null

# Arthur-specific deployment glue must not come across. Nothing upstream ships it today;
# the guard stays because the boundary belongs in code rather than a reviewer's memory.
for stray in "$DEST"/dist/jamf-collect.sh "$DEST"/dist/*.plist; do
  [ -e "$stray" ] && { echo "vendor: removing Arthur-specific $(basename "$stray") -- it belongs in this repo, not upstream"; rm -f "$stray"; }
done

# The manifest is what makes "verbatim" checkable: the ref stamp names a release, and only
# this says the files still match it. test/lint.sh verifies it.
( cd "$DEST" && find . -type f ! -name VERSION ! -name SHA256SUMS -print0 \
    | sort -z | xargs -0 shasum -a 256 > SHA256SUMS ) || fatal "could not write SHA256SUMS"

cat > "$DEST/VERSION" <<EOF
repo   $REPO
ref    $REF
kind   $kind
sha    $sha
at     $(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo
echo "vendored into vendor/ai-detection-spec/"
sed 's/^/  /' "$DEST/VERSION"
echo "  files: $(find "$DEST" -type f | wc -l | tr -d ' ')"
echo
echo "next: tools/build-collector.py   (rebuilds the deployable around these)"
if [ "$kind" = tag ]; then
  echo "      then, in ml-engine/: uv run python scripts/vendor_ai_detection_spec.py"
  echo "                           (the catalog and matcher, at this same tag)"
else
  echo "      the catalog and matcher cannot follow a bare commit: ml-engine vendors them from a"
  echo "      tag's release. ml-engine's test_vendor_parity.py fails until a tag is pinned here."
fi
