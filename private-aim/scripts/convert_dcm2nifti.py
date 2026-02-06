# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

import os
from os.path import join, exists, basename
import pydicom
from pathlib import Path
from subprocess import PIPE, run
import generate_json

execution_timeout = 1200
convert_to = ".nii.gz"
dataset_dir = os.getenv("nnUNet_input")
nnunet_output_dir = os.getenv("nnUNet_output")

def process_input_file(dcm_series_paths:list, convert_output_dir:Path, json_output_dir:Path):
    global execution_timeout, convert_to
    for dcm_series_path in dcm_series_paths:
        print(dcm_series_path)
        input_filepath = list(dcm_series_path.glob("*.dcm"))[0]
        try:
            # Try to get the SeriesInstanceUID from the dicom file
            incoming_dcm_series_id = str(
                pydicom.dcmread(input_filepath, force=True, stop_before_pixels=True).SeriesInstanceUID
            )
        except:
            # If the SeriesInstanceUID could not be read, use the filename
            file_name = basename(input_filepath).split(".")[0]
            incoming_dcm_series_id = file_name

        output_filepath = join(
            convert_output_dir, incoming_dcm_series_id + convert_to )
        json_filepath = join(
            json_output_dir, incoming_dcm_series_id +'.mitklabel.json')
        seg_out_filename  = join(
            json_output_dir, incoming_dcm_series_id + convert_to)
        
        generate_json.create_mitklabel_json(seg_out_filename, dcm_series_path, json_filepath)

        if not exists(output_filepath):
            command = [
                "/app/mitk/apps/MitkFileConverter.sh",
                "-i",
                input_filepath,
                "-o",
                output_filepath
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
    folder = Path(dataset_dir)
    subfolders = [f for f in folder.iterdir() if f.is_dir()]
    
    nnUNet_data_dir = Path(nnunet_output_dir).joinpath('nnunet_data_dir')
    nnUNet_data_dir.mkdir(exist_ok=True)

    nnunet_output_dir = Path(nnunet_output_dir).joinpath('tmp')
    nnunet_output_dir.mkdir(exist_ok=True)

    process_input_file(subfolders, nnUNet_data_dir, nnunet_output_dir)
