# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

# Dockerfile for nnUNet task images
# Author: Ashis Ravindran, DKFZ
# Builds image nnunet:base
FROM nnunet:base
ARG MULTI_MODAL=False

# Maintainer information
LABEL maintainer="ashis.ravindran@dkfz-heidelberg.de"
LABEL version="1.0"
LABEL description="nnUNet model pretrained on Task017_AbdominalOrganSegmentation targeting thirteen different abdominal organs."
LABEL image.source="https://github.com/MIC-DKFZ/nnUNet/blob/nnunetv1/"
LABEL image.revision="db16c6cef5fdd5a180159184e46b58bcca670446"
LABEL image.version="1.7.1"

USER eucaim
ENV TASK_NAME=Task017_AbdominalOrganSegmentation
ENV MULTI_MODAL=$MULTI_MODAL
RUN nnUNet_download_pretrained_model $TASK_NAME

CMD ["/bin/bash", "/app/start_nnunet.sh" ]
HEALTHCHECK --interval=60s --timeout=10s --retries=3 CMD python /app/scripts/health_check.py || exit 1

# Commands:
# docker build -t harbor.eucaim.cancerimage.eu/processing-tools/nnunet-abdominal-organ-segmentation:latest .
# docker push harbor.eucaim.cancerimage.eu/processing-tools/nnunet-abdominal-organ-segmentation:latest
# docker run --rm \
# -v $(pwd)/toy_datasets:/home/eucaim/nnUNet_input \  # mounting data volume (read only)
# -v $(pwd)/toy_out:/home/eucaim/nnUNet_output \      # mounting sandbox to save output (read and write)
# --gpus all \
# nnunet-abdominal-organ-segmentation:latest          # image to run