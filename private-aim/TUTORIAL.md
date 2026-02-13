# FLAME nnUNet Segmentation Analysis Tutorial

This guide provides a complete walkthrough of the nnUNet segmentation analysis example. It explains how the analyzer and aggregator components work together in the STAR pattern to process distributed medical image input and return segmentation results as bytes.

The implementation described here is `private-aim/scripts/start_nnunet.py`.

## 1. Overview

This analysis is a practical baseline for nnUNet liver segmentation inference in FLAME.  
It accepts DICOM and/or NIfTI payloads, prepares nnUNet-compatible inputs, runs prediction, converts outputs to DICOM SEG where possible, and returns fallback NIfTI outputs when DICOM metadata is not available.

At runtime, the pipeline performs these steps:

1. Receives input bytes from FLAME (`data_type="s3"`)
2. Unpacks raw files and TAR archives into `/nnUNet_input`
3. Prepares nnUNet input data in `/nnUNet_output/nnunet_data_dir`
4. Runs `nnUNet_predict`
5. Converts predictions to DICOM SEG (when matching metadata is available)
6. Returns NIfTI predictions as fallback for cases without matching DICOM metadata
7. Cleans temporary directories

## 2. Code Walkthrough

### 2.1. STAR components

The workflow uses the standard STAR pattern:

- `nnUNetAnalyzer` for local analysis logic
- `MyAggregator` for aggregation (pass-through)
- `StarModel` for orchestration

```python
StarModel(
    analyzer=nnUNetAnalyzer,
    aggregator=MyAggregator,
    data_type="s3",
    simple_analysis=True,
    output_type="bytes"
)
```

### 2.2. Analyzer (`nnUNetAnalyzer`)

#### Input handling

`unpack_input(...)` supports:

- raw byte entries
- dictionary entries (`filename -> bytes`)
- multiple TAR archives in a single request

Each TAR is extracted; non-TAR content is written as a raw file.

#### Preparing nnUNet input

`prepare_nnunet_input(...)`:

- collects `*.nii` and `*.nii.gz`
- copies NIfTI files to `nnunet_data_dir`
- gzips plain `.nii`
- converts DICOM to NIfTI when `*.dcm` files are present

If `multi_modal=False`, `rename_single_modality_files(...)` renames files to:

- `<case>_0000.nii.gz`

#### Prediction

Inference command:

```bash
nnUNet_predict -i <nnunet_data_dir> -o <tmp> -t Task029_LiTS -tr nnUNetTrainerV2 -p nnUNetPlansv2.1 -m 3d_fullres
```

The script checks command return codes and raises an error if prediction fails.

#### Output conversion

After prediction:

- files with matching `*.mitklabel.json` are converted to DICOM SEG
- files without matching metadata are returned as NIfTI fallback

### 2.3. Aggregator (`MyAggregator`)

`MyAggregator` is pass-through and returns the analysis results unchanged:

```python
def aggregation_method(self, analysis_results):
    return analysis_results
```

The convergence method always returns `True`, because this workflow runs in one analysis round (`simple_analysis=True`).

### 2.4. `StarModel` configuration

```python
StarModel(
    analyzer=nnUNetAnalyzer,
    aggregator=MyAggregator,
    data_type="s3",
    simple_analysis=True,
    output_type="bytes"
)
```

## 3. Output

The analysis returns:

```json
{
  "status": "done",
  "dicom_seg_bytes": {
    "case1.dcm": "..."
  },
  "nifti_seg_bytes": {
    "case2.nii.gz": "..."
  }
}
```

- `dicom_seg_bytes`: preferred output format
- `nifti_seg_bytes`: fallback when DICOM SEG conversion is not possible

## 4. Practical notes

- Keep nnUNet paths consistent: `/nnUNet_input`, `/nnUNet_output`
- If a case has no DICOM SEG output, check whether matching metadata (`*.mitklabel.json`) exists
- Temporary directories are deleted at the end of each run
