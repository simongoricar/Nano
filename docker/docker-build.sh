#!/usr/bin/env bash

# Go to the "main" directory
cd ..

# Find bot version
VERSION=$(python ./utilities/find_version.py)

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
docker build -t nano:${TAG} . --build-arg VERSION=${VERSION}
echo "DONE!"
