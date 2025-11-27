# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0
import os, sys

def is_healthy():
    try:
        log_file = "/home/eucaim/nnUNet_output/tmp/plans.pkl"
        if os.path.exists(log_file): # process started
            return True
    except Exception as e:
        return False

if __name__ == "__main__":
    if is_healthy():
        sys.exit(0)
    else:
        sys.exit(1)
