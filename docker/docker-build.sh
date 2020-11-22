#!/usr/bin/env bash

# Update the requirements.txt file
./scripts/generate_requirements.sh

# Find Nano version
VERSION=$(python ./scripts/find_version.py)

# If ran with additional argument, use that as tag
# Otherwise use current Nano version
if [[ $1 ]];
then
  TAG=$1
  echo "Using tag: ${TAG}"
else
  echo "No argument passed, using Nano version."
  TAG=$VERSION
  echo "Using tag: ${TAG}"
fi

echo "Building..."
docker build -t nano:"${TAG}" . --build-arg VERSION="${VERSION}"
echo "DONE!"
