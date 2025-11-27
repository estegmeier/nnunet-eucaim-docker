# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

import shutil
import os
import json
from pathlib import Path
from subprocess import PIPE, run
from os.path import join, exists
import generate_json

execution_timeout = 1200
convert_to = ".dcm"
dataset_dir = os.getenv("nnUNet_output")
nnunet_input_dir = os.getenv("nnUNet_input")

def convert_to_dcmseg(json_file_path: Path):
    with open(json_file_path, 'r') as f:
        json_dict = json.load(f)
    file = Path(json_dict['groups'][0]['_file'])
    file_id = Path(file.stem).stem
    #add labels info into the json dict
    if not generate_json.update_mitk_json_labels_property(json_dict):
        print('###########################')
        print('No segmentations were produced, skipping:', file_id)
        print('###########################')
        return

    # write back with label info
    with open(json_file_path, 'w') as file:
        json.dump(json_dict, file, indent=4)

    # get nifti file name
   
    output_filepath = json_file_path.parent.parent
    dcm_output_filepath = join(
        output_filepath, file_id + convert_to
    )
    if not exists(dcm_output_filepath):
        command = [
            "/app/mitk/apps/MitkFileConverter.sh",
            "-i",
            json_file_path,
            "-o",
            dcm_output_filepath
        ]
        print(command)
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=execution_timeout,
        )

        print("\nStandard Output:")
        print(output.stdout)
        print("\nStandard Error (if any):")
        print(output.stderr)

if __name__ == "__main__":
    nnUNet_seg_dir = Path(dataset_dir).joinpath('tmp')
    mitk_json_filepaths = list(nnUNet_seg_dir.rglob("*.mitklabel.json"))
    for mitk_json_file in mitk_json_filepaths:
        convert_to_dcmseg(mitk_json_file)
    shutil.rmtree(nnUNet_seg_dir) # delete tmp directory

    nnUNet_data_dir = Path(nnunet_input_dir).joinpath('nnunet_data_dir')
    shutil.rmtree(nnUNet_data_dir)
