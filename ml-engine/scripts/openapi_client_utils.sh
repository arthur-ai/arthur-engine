#!/usr/bin/env bash
set -exuo pipefail # script does not fail if a command fails

if [ "$#" -eq 0 ]; then
    echo "Please provide purpose and language runtime.\n"
    echo "Usage: ./openapi_client_utils.sh <purpose> [<runtime>]"
    echo "Possible values: \n purpose - 'none', 'generate'(default) or 'install', runtime - 'python'(default), 'typescript', 'go'"
    echo "No changes made. Exiting!"
    exit 2
fi

export OPENAPI_GENERATOR_VERSION=7.12

install_openapi_gen() {
  echo "Installing openapi-generator-cli $OPENAPI_GENERATOR_VERSION..."
  # The PyPI distribution bundles its own JVM via jdk4py, so no system Java install is
  # needed. Same generator and pin CI uses in .github/workflows/arthur-engine-workflow.yml.
  python3 -m pip install "openapi-generator-cli[jdk4py]==$OPENAPI_GENERATOR_VERSION"
  # Prefer this install over an older npm-installed shim left on PATH by previous versions
  # of this script, which shells out to a system JVM instead of the bundled one.
  PATH="$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts"))'):$PATH"
}

install_openapi_gen

purpose=${1:-generate}
runtime=${2:-python} # use 'python' by default if no language runtime passed to script

if [[ "$purpose" == "generate" ]]; then
    rm -rf ../src/genai_client
    echo "cleared previous generated code"
    version=$(jq -r '.info.version' ../../genai-engine/staging.openapi.json)
    openapi-generator-cli generate -i ../../genai-engine/staging.openapi.json --skip-validate-spec -g "python" -o ../src/genai_client --package-name genai_client -p packageVersion=$version
fi

if [ "$purpose" == "install" ]; then
  echo "Installing the newly generated $runtime client"
  uv pip install ../src/genai_client -vvv
fi
