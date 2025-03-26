#!/bin/bash

# Fail on errored out commands
set -e

for var in REMOTE_TEST_URL REMOTE_TEST_KEY BUILD_VERSION; do
  if [[ -z "${!var}" ]]; then
  missing_vars+=" $var"
  fi
done

if [[ -n "$missing_vars" ]]; then
echo "Missing required environment variable values: $missing_vars"
exit 1
fi

i=0
if [[ $REMOTE_TEST_URL != *"localhost"* ]]; then
    echo "$(date): Waiting for deployment $BUILD_VERSION to go live..."
    while [[ true ]]
    do
        if [[ $i -eq 60 ]]
        then
            echo "$(date): Deployment failed to return build version $BUILD_VERSION"
            exit 1
        fi
        echo "Getting build version..."
        resp=$(curl -s --retry 5 --retry-delay 1 $REMOTE_TEST_URL/health)
        echo $resp
        if echo $resp | grep -q "$BUILD_VERSION\"" ; then
        echo "$(date): Deployment is on expected build version $BUILD_VERSION"
        break
        fi
        echo "$(date): Deployment is not on expected build version $BUILD_VERSION, health is: $resp. Trying again in 30 seconds."
        sleep 30
        i=$((i+1))
        echo "Incremented to $i"
    done

    # ECS containers can take some time to roll. While the new version is present on at least one active container,
    # its possible we'll end up testing against an old container, failing tests depending on new code. Build in a
    # delay to reduce the chance of this happening, allowing more time for the old containers to get rolled off
    echo "\n"
    echo "Waiting for pods to roll..."
    sleep 90
fi

poetry -C genai-engine run pytest -m "integration_tests"
if [[ $? == '1' ]]
then
    echo "$(date): Integration tests failed, returning with exit code 1"
    exit 1
fi
