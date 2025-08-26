#!/usr/bin/env bash
set -exuo pipefail # script does not fail if a command fails

if [ "$#" -eq 0 ]; then
    echo "Please provide purpose and language runtime.\n"
    echo "Usage: ./openapi_client_utils.sh <purpose> [<runtime>]"
    echo "Possible values: \n purpose - 'none', 'generate'(default) or 'install', runtime - 'python'(default), 'typescript', 'go'"
    echo "No changes made. Exiting!"
    exit 2
fi

export OPENAPI_GENERATOR_VERSION=7.11.0

install_or_update_openapi_gen() {
  echo "Installing or updating openapi-generator-cli to version $OPENAPI_GENERATOR_VERSION..."
  if [[ $(uname) == 'Darwin' ]]; then
    # use npm to install and manage OpenAPI Generator on local macs
    brew install npm
    npm install -g @openapitools/openapi-generator-cli
    openapi-generator-cli version-manager set $OPENAPI_GENERATOR_VERSION
  else
    # use auto-updating linux scripts to install OpenAPI Generator on local CI server
    curl https://raw.githubusercontent.com/OpenAPITools/openapi-generator/master/bin/utils/openapi-generator-cli.sh > /usr/local/bin/openapi-generator-cli
    chmod u+x /usr/local/bin/openapi-generator-cli
  fi
}

# install cli if not present
if ! command -v openapi-generator-cli &> /dev/null; then
  echo "openapi-generator-cli is not installed."
  install_or_update_openapi_gen
else
  echo "openapi-generator-cli version `openapi-generator-cli version` already installed"
fi

# upgrade cli if not on desired version
version=$(openapi-generator-cli version)
if [ "$version" != "$OPENAPI_GENERATOR_VERSION" ]; then
  install_or_update_openapi_gen
  openapi-generator-cli version # confirm installation successful
fi

purpose=${1:-generate}
runtime=${2:-python} # use 'python' by default if no language runtime passed to script

if [[ "$purpose" == "generate" ]]; then
    rm -rf ../src/genai_client
    echo "cleared previous generated code"
    version=$(jq -r '.info.version' ../../genai-engine/staging.openapi.json)
    openapi-generator-cli generate -i ../../genai-engine/staging.openapi.json --skip-validate-spec -g "python" -o ../src/genai_client --package-name genai_client -p packageVersion=$version
fi

if [[ "$purpose" == "generate-common" ]]; then
    rm -rf ../src/common_client
    echo "cleared previous generated common code"
    version=$(jq -r '.info.version' ./staging.openapi.min.json)
    openapi-generator-cli generate -i ./staging.openapi.min.json --skip-validate-spec -g "python" -o ../src/common_client --package-name arthur_common -p packageVersion=$version --additional-properties=legacyDiscriminatorBehavior=false
fi

if [ "$purpose" == "install" ]; then
  echo "Installing the newly generated $runtime client"
  pip3 install ../src/genai_client -vvv
fi

if [ "$purpose" == "install-common" ]; then
  echo "Installing the newly generated common client"
  pip3 install ../src/common_client -vvv
fi
