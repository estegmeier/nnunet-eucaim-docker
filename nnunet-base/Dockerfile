# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

# Dockerfile for nnUNet base images
# Author: Ashis Ravindran, DKFZ
# Builds image nvidia/cuda:11.8.0-runtime-ubuntu22.04
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Maintainer information
LABEL maintainer="ashis.ravindran@dkfz-heidelberg.de"
LABEL version="1.0"
LABEL description="nnU-Net is a machine learning based semantic segmentation method."
LABEL image.source="https://github.com/MIC-DKFZ/nnUNet/tree/nnunetv1"
LABEL image.revision="commit-sha"
LABEL image.version="tag-or-version"
ENV PYTHONUNBUFFERED=1

# Set defaults for build arguments
ARG USER_UID=2323
ARG USER_GID=2323

# Create non-root user and group, and prevent login
RUN groupadd -g $USER_GID eucaim && \
    useradd -l -r -u $USER_GID -g eucaim -d /home/eucaim -m -s /usr/sbin/nologin eucaim

RUN apt-get update && apt-get install -y --no-install-recommends\
    git \
    wget \
    python3 \
    python3-pip \
    libx11-6 \ 
    ca-certificates \
    linux-libc-dev \
    libtiff5-dev \
    libwrap0-dev \
    libxcomposite1 \
    libxcursor1 \
    libxi-dev \
    libxkbcommon-x11-0 \
    mesa-common-dev \
    libssl-dev \
    libglu1-mesa-dev \
    libxt-dev \
    libgomp1 \
    qtbase5-dev \
    qtscript5-dev \
    libqt5svg5-dev \
    libqt5opengl5-dev \
    libqt5xmlpatterns5-dev \
    qtwebengine5-dev \
    qttools5-dev \
    libqt5x11extras5-dev \
    qtxmlpatterns5-dev-tools \
    libqt5webengine-data \
    at-spi2-core \
    libxcb-cursor0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python3 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install PyTorch+CUDA
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu118
    
RUN pip install --no-cache-dir pydicom==3.0.1 SimpleITK==2.5.2

WORKDIR /app
RUN mkdir -p nnunetv1 scripts mitk

RUN wget --no-check-certificate https://github.com/MITK/MITK/releases/download/v2025.08/MITK-v2025.08-ubuntu_22_04-x86_64.tar.gz -O /app/mitk.tar.gz \
    && tar -xzf /app/mitk.tar.gz --strip 1 -C /app/mitk/ MITK-v2025.08-linux-x86_64 \
    && rm -rf /app/mitk.tar.gz

# Clone nnU-Net v1
RUN git clone --branch nnunetv1 https://github.com/MIC-DKFZ/nnUNet.git ./nnunetv1

# Copy relevant files
COPY start_nnunet.sh ./start_nnunet.sh
COPY nnunetv1.patch ./nnunetv1/nnunetv1.patch
COPY scripts scripts

RUN chown -R root:root /app && chmod 755 ./start_nnunet.sh

# Install nnU-Net
RUN cd nnunetv1 && git apply --ignore-space-change --ignore-whitespace nnunetv1.patch
RUN pip3 install --no-cache-dir -e ./nnunetv1

# Switch to eucaim user
USER eucaim
WORKDIR /home/eucaim

# Set env vars required by nnU-Net
ENV nnUNet_input="/home/eucaim/nnUNet_input" 
ENV nnUNet_output="/home/eucaim/nnUNet_output"
ENV RESULTS_FOLDER="/home/eucaim/nnUNet_results_folder"

RUN mkdir -p $nnUNet_input $nnUNet_output $RESULTS_FOLDER

