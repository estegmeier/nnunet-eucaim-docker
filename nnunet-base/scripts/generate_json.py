# Copyright 2025 German Cancer Research Center (DKFZ) and contributors.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import pydicom
from pydicom.errors import InvalidDicomError
import uuid
import random
import SimpleITK as sitk
import numpy as np
from pathlib import Path


def get_sorted_reference_files(dicom_folder_path):
    z_sorted = []
    for fname in os.listdir(dicom_folder_path):
        if not fname.lower().endswith(".dcm"):
            continue
        fpath = os.path.join(dicom_folder_path, fname)
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=True)
            image_position = ds.get("ImagePositionPatient", None)
            if image_position is not None and len(image_position) == 3:
                z_pos = float(image_position[2])
                z_sorted.append((z_pos, os.path.abspath(fpath)))
            else:
                print(f"Skipping file (no z pos): {fpath}")
        except InvalidDicomError:
            print(f"Skipping invalid DICOM file: {fpath}")
    z_sorted.sort(key=lambda tup: tup[0])
    reference_files = [[i, path] for i, (_, path) in enumerate(z_sorted)]
    return reference_files

def get_dicom_value(ds, tag):
    elem = ds.get(tag)
    return str(elem.value) if elem and elem.value is not None else ""

def create_mitklabel_json(file: str, dicom_folder_path: str, output_json_path: str):
    reference_files = get_sorted_reference_files(dicom_folder_path)
    zmax = len(reference_files)-1 

    # Reading the first DICOM for metadata
    first_dicom_path = os.path.join(dicom_folder_path, reference_files[0][1])
    ds = pydicom.dcmread(first_dicom_path, stop_before_pixels=True)

    tags_to_extract = [
        "0008,0050", "0008,1030", "0010,0010", "0010,0020", "0010,0030",
        "0010,0040", "0012,0050", "0012,0060", "0012,0071", "0020,000D"
    ]
    
    # Extract TemporoSpatialStringProperty values
    temporo_spatial = {}
    for tag_str in tags_to_extract:
        group, element = (int(x, 16) for x in tag_str.split(","))
        tag_key = f"DICOM.{tag_str.replace(',', '.')}"
        value = get_dicom_value(ds, (group, element))
        temporo_spatial[tag_key] = {
            "values": [{
                "t": 0,
                "value": value,
                "z": 0,
                "zmax": zmax
            }]
        }

    temporo_spatial["DICOM.0008.0060"] = {     # hardcoded tags
        "values": [{
            "t": 0,
            "value": "SEG",
            "z": 0
        }]
    }
    temporo_spatial["DICOM.0008.103E"] = {    # hardcoded tags
        "values": [{
            "t": 0,
            "value": "nnUNet Segmentation",
            "z": 0
        }]
    }
    temporo_spatial["DICOM.0070.0084"] = {    # hardcoded tags
        "values": [{
            "t": 0,
            "value": "EUCAIM",
            "z": 0
        }]
    }

    data = {
        "groups": [
            {
                "_file": file
            }
        ],
        "properties": {
            "StringLookupTableProperty": {
                "referenceFiles": reference_files
            },
            "TemporoSpatialStringProperty": temporo_spatial
        },
        "type": "org.mitk.multilabel.segmentation.stack",
        "uid": str(uuid.uuid4()),
        "version": 3,
    }

    with open(output_json_path, 'w') as f:
        json.dump(data, f, indent=4)

def _count_labels_in_nifti(nifti_path):
    nifti_image = sitk.ReadImage(nifti_path)
    data = sitk.GetArrayFromImage(nifti_image)
    unique_labels = np.unique(data)
    labels = unique_labels[unique_labels != 0]  # Exclude background (0)
    return len(labels)

def update_mitk_json_labels_property(json_dict: Path):
    def random_color():
        return [random.random(), random.random(), random.random()]
    file = json_dict['groups'][0]['_file']
    n_labels = _count_labels_in_nifti(file)
    if n_labels > 0:
        labels = [
            {
                "DICOM.0062.0002.0062.0008":
                    {
                        "type": "TemporoSpatialStringProperty",
                        "value": {
                            "values": [
                                {
                                    "t": 0,
                                    "value": "AUTOMATIC",
                                    "z": 0
                                }
                            ]
                        }
                    },
                "color": random_color(),
                "locked": True,
                "name": f"Label {label}",
                "opacity": 0.6,
                "tracking_id": str(label),
                "value": label,
                "visible": True   
            }
            for label in range(1, n_labels + 1)
        ]
        json_dict['groups'][0]['labels'] = labels
        return True
    else:
        return False