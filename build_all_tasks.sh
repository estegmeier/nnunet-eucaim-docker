#!/bin/bash
# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

# !! This is not relevant for EUCAIM !!!
# List TASK_NAMES here
TASK_NAMES=(
  Task001_BrainTumour 
  Task002_Heart
  Task003_Liver
  Task004_Hippocampus
  Task005_Prostate
  Task006_Lung
  Task007_Pancreas
  Task008_HepaticVessel
  Task009_Spleen
  Task010_Colon
)

# User UID and Group ID defaults
UID=${1:-1000}
GID=${2:-1000}

# Build base image first
docker build \
    --build-arg USER_UID=$UID\
    --build-arg USER_GID=$GID\
    -t "nnunet:base" nnunet-base/
echo "nnUNet base image build finshed"

# Build each task-specific image
for TASK_NAME in "${TASK_NAMES[@]}"; do
  echo "Building image for: $TASK_NAME"
  
  BUILD_CMD="docker build --build-arg TASK_NAME=$TASK_NAME"

  case "$TASK_NAME" in
    Task001_Brain|Task005_Prostate)
    BUILD_CMD+=" --build-arg MULTI_MODAL=True"
      ;;
  esac

  # Finalize and run the build command
  BUILD_CMD+=" -t nnunet:${TASK_NAME} nnunet-task/"
  eval $BUILD_CMD

  echo "Building finshed for image: $TASK_NAME"
done
