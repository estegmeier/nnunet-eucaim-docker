import argparse
import convert_dcm2nifti
import convert_nifti2dcmseg
from io import BytesIO
import os
from pathlib import Path
import shutil
import tarfile

from flame.star import StarAnalyzer, StarAggregator, StarModel


class nnUNetAnalyzer(StarAnalyzer):
    def __init__(self, flame, task_name="Task029_LiTS", multi_modal=False):
        """
        Initializes the nnUNet Analyzer node.

        :param flame: Instance of FlameCoreSDK to interact with the FLAME components.
        :param task_name: Name of the nnUNet task to use.
        :param multi_modal: Boolean indicating if input is multi-modal.
        """
        super().__init__(flame)

        self.task_name = task_name
        self.multi_modal = multi_modal
        self.nnUNet_input = os.environ.get("nnUNet_input", "/nnUNet_input")
        self.nnUNet_output = os.environ.get("nnUNet_output", "/nnUNet_output")

        print("Init of nnUNet analyzer finished ...")


    def unpack_input(self, data):
        """
        Extracts all input files from FLAME into /nnUNet_input.
        Handles multiple TAR archives and/or direct binary files.

        :param data: List of input entries from FLAME, each either a dict {filename: bytes} or raw bytes.
        """
        os.makedirs(self.nnUNet_input, exist_ok=True)

        if not data:
            print("No input data provided.")
            return

        for idx, entry in enumerate(data):
            # Handle dict {filename: bytes} or raw bytes
            if isinstance(entry, dict):
                items = entry.items()
            else:
                items = [(f"input_file_{idx}", entry)]

            for key, content in items:
                filename = os.path.basename(key)
                file_path = Path(self.nnUNet_input) / filename

                # Try to interpret as TAR archive
                try:
                    tar_obj = BytesIO(content)
                    with tarfile.open(fileobj=tar_obj) as tar:
                        tar.extractall(path=self.nnUNet_input)
                    print(f"[{idx}] Extracted TAR archive to {self.nnUNet_input}: {filename}")
                except tarfile.ReadError:
                    with open(file_path, "wb") as f:
                        f.write(content)
                    print(f"[{idx}] Wrote raw input file: {file_path}")


    def prepare_nnunet_input(self, nnUNet_input, data_dir):
        """
        Prepares nnUNet input data.
        Copies NIfTI files and runs DICOM to NIfTI conversion if needed.

        :param nnUNet_input: Path to the extracted input directory.
        :param data_dir: Path to the nnUNet input data directory.
        """
        # Check for NIfTI files
        nii_files = list(nnUNet_input.rglob("*.nii")) + list(nnUNet_input.rglob("*.nii.gz"))
        if nii_files:
            print(f"Found {len(nii_files)} NIfTI files, copying to nnunet_data_dir...")
            for f in nii_files:
                target_path = data_dir / f.name
                if target_path.exists():
                    base_name = f.name
                    if f.name.endswith(".nii.gz"):
                        base_name = f.name[:-7]
                        ext = ".nii.gz"
                    else:
                        base_name = f.stem
                        ext = f.suffix
                    idx = 1
                    while target_path.exists():
                        target_path = data_dir / f"{base_name}_{idx}{ext}"
                        idx += 1
                shutil.copy(f, target_path)
            # gzip plain .nii files
            for f in data_dir.glob("*.nii"):
                if os.system(f"gzip '{f}'") != 0:
                    raise RuntimeError(f"Failed to gzip file: {f}")
        else:
            print("No NIfTI files found.")

        # Check for DICOM files
        dcm_files = list(nnUNet_input.rglob("*.dcm"))
        if dcm_files:
            print("DICOM input detected, running DICOM to NIfTI conversion...")
            convert_dcm2nifti.main()
        else:
            print("No DICOM input detected.")


    def rename_single_modality_files(self, data_dir):
        """
        Renames single-modality files to nnUNet format *_0000.nii.gz.

        :param data_dir: Path to the nnUNet input data directory.
        """
        for f in data_dir.glob("*.nii.gz"):
            if not f.name.endswith("_0000.nii.gz"):
                base_name = f.name[:-7]
                new_name = f.with_name(base_name + "_0000.nii.gz")
                f.rename(new_name)
                print(f"Renamed {f.name} to {new_name.name}")


    def analysis_method(self, data, aggregator_results):
        """
        Replicates start_nnUNet.sh in pure Python.
        Handles input unpacking, NIfTI/DICOM conversion, nnUNet prediction,
        DICOM SEG conversion, and cleanup. Returns all segmentations as bytes.

        :param data: List of input entries from FLAME (dict {filename: bytes} or raw bytes)
        :param aggregator_results: Previous aggregator results (unused)
        :return: dict containing
                 - 'status': string indicating completion
                 - 'dicom_seg_bytes': dictionary {dicom_filename: dicom_bytes}
                 - 'nifti_seg_bytes': dictionary {nifti_filename: nifti_bytes}
        """
        self.unpack_input(data)

        task_name = self.task_name
        multi_modal = self.multi_modal
        nnUNet_input = Path(self.nnUNet_input)
        nnUNet_output = Path(self.nnUNet_output)
        data_dir = nnUNet_output / "nnunet_data_dir"
        data_dir.mkdir(parents=True, exist_ok=True)

        print(f"Using pre-downloaded model for {task_name}")
        self.prepare_nnunet_input(nnUNet_input, data_dir)
        
        # If single modality, rename files to *_0000.nii.gz
        if not multi_modal:
            self.rename_single_modality_files(data_dir)

        # Change task folder 
        src = Path("/nnUNet_results_folder/nnUNet/3d_fullres/Task029_LITS")
        dst = Path("/nnUNet_results_folder/nnUNet/3d_fullres/Task029_LiTS")

        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"Moved {src} to {dst} safely across devices")

        # Run nnUNet prediction
        print("Running nnUNet prediction...")
        predict_rc = os.system(
            f"nnUNet_predict -i {data_dir} -o {nnUNet_output}/tmp "
            f"-t {task_name} -tr nnUNetTrainerV2 -p nnUNetPlansv2.1 -m 3d_fullres"
        )
        if predict_rc != 0:
            raise RuntimeError(f"nnUNet prediction failed with exit code {predict_rc}")

        # Convert predicted segmentations to DICOM SEG
        print("Converting NIfTI to DICOM SEG...")
        nnUNet_seg_dir = nnUNet_output / "tmp"
        mitk_json_filepaths = list(nnUNet_seg_dir.rglob("*.mitklabel.json"))
        nifti_seg_filepaths = list(nnUNet_seg_dir.glob("*.nii.gz"))
        mitk_json_stems = {p.name.replace(".mitklabel.json", "") for p in mitk_json_filepaths}

        # Convert predicted segmentations to DICOM SEG and return as bytes
        dicom_bytes_dict = {}
        for mitk_json_file in mitk_json_filepaths:
            dcm_path = convert_nifti2dcmseg.convert_to_dcmseg(mitk_json_file)
            if dcm_path and dcm_path.exists():
                with open(dcm_path, "rb") as f:
                    dicom_bytes_dict[dcm_path.name] = f.read()

        # Collect only fallback NIfTI segmentations (no matching DICOM SEG metadata available)
        nifti_bytes_dict = {}
        for nifti_path in nifti_seg_filepaths:
            if nifti_path.name[:-7] in mitk_json_stems:
                continue
            with open(nifti_path, "rb") as f:
                nifti_bytes_dict[nifti_path.name] = f.read()

        # Cleanup
        if nnUNet_seg_dir.exists():
            shutil.rmtree(nnUNet_seg_dir)
        if data_dir.exists():
            shutil.rmtree(data_dir)

        print("nnUNet pipeline completed successfully.")
        return {
            "status": "done",
            "dicom_seg_bytes": dicom_bytes_dict,
            "nifti_seg_bytes": nifti_bytes_dict
        }


class MyAggregator(StarAggregator):
    def __init__(self, flame):
        """
        Initializes the custom Aggregator node.

        :param flame: Instance of FlameCoreSDK to interact with the FLAME components.
        """
        super().__init__(flame)

        print("Init of aggregator finished ...")


    def aggregation_method(self, analysis_results):
        """
        Aggregates the analysis results from multiple analyzers into one dictionary.

        :return: analysis_results (dict): A single dictionary combining all individual results.
        """
        return analysis_results
    

    def has_converged(self, result, last_result, num_iterations=None):
        """
        Checks whether the analysis has converged if 'simple_analysis' in 'StarModel' is set to False.
        Always returns True, since only one iteration round is performed.  

        :return (bool): True, indicating convergence after a single round.
        """
        return True 


def main():
    """
    Entry point to initialize and run the StarModel pipeline with nnUNetAnalyzer.
    Parses console arguments and passes them to MyAnalyzer.
    """
    parser = argparse.ArgumentParser(description="Run StarModel pipeline with custom analyzer parameters.")
    parser.add_argument("--query_key", type=str, default=None, help="Optional S3 query key for StarModel")

    args, unknown = parser.parse_known_args()
    query = [args.query_key] if args.query_key else []

    StarModel(
        analyzer=nnUNetAnalyzer,
        aggregator=MyAggregator,
        data_type="s3",
        query=query,
        simple_analysis=True,
        output_type="bytes"
    )


if __name__ == "__main__":
    main()
