#!/usr/bin/env python
"""Validation script for scRNA-seq signal correction.
Predictions file must be a zipped archive of imputed count files.
Each imputed count file must have a correct file format:
(pac_expId_ds_prop_imputed.csv).
"""

import argparse
import json
import pandas as pd
import os
import tarfile
import zipfile


def get_args():
    """Set up command-line interface and get arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--results", required=True,
                        help="validation results")
    parser.add_argument("-e", "--entity_type", required=True,
                        help="synapse entity type downloaded")
    parser.add_argument("-s", "--submission_file", help="Submission File")
    parser.add_argument("-g", "--goldstandard", required=True,
                        help="Goldstandard for scoring")
    return parser.parse_args()


def _filter_files(members):
    """Filter out non-csv files in zip file."""
    filenames = filter(lambda file: file.endswith(".csv"), members)
    filenames = list(filenames)
    return filenames


def unzip_file(f):
    """Untar or unzip file."""
    names = []
    dfs = []
    if zipfile.is_zipfile(f):
        with zipfile.ZipFile(f) as zip_ref:
            members = zip_ref.namelist()
            members = _filter_files(members)
            if members:
                for member in members:
                    # save basename as file names used to validate
                    # in case root dir is zipped
                    names.append(os.path.basename(member))
                    file = zip_ref.open(member)
                    df = pd.read_csv(file, index_col=0)
                    dfs.append(df)
    elif tarfile.is_tarfile(f):
        with tarfile.open(f) as zip_ref:
            members = zip_ref.getnames()
            members = _filter_files(members)
            if members:
                for member in members:
                    names.append(os.path.basename(member))
                    file = zip_ref.extractfile(member)
                    df = pd.read_csv(file, index_col=0)
                    dfs.append(df)
    return {"names": names, "files": dfs}


def get_dim_name(df):
    """Get all row names and column names of df"""
    out = {"rownames": list(df.index),
           "colnames": list(df.columns.values)}
    return out


def main():
    """Main function."""
    args = get_args()

    invalid_reasons = []

    # set variables to name files
    exp_ids = ["2400", "2401", "7200", "7201"]
    ds_props = ["0_125", "0_5", "drpc_20k", "drpc_50k"]

    # validate goldstandard file
    # check if all required data exists
    gs_files = unzip_file(args.goldstandard)
    true_gs_files = ["pac_" + id + "_gs.csv" for id in exp_ids]
    diff = list(set(true_gs_files) - set(gs_files["names"]))
    if diff:
        invalid_reasons.append("File not found : " + "', '".join(diff))

    # validate prediction file
    if args.submission_file is None:
        invalid_reasons.append(
            'Expected FileEntity type but found ' + args.entity_type
        )
    else:
        pred_files = unzip_file(args.submission_file)
        # exp names: pac_{expId}_ds_{prop}_imputed, e.g. pac_1111_ds_0_1
        true_pred_files = ["pac_" + id + "_ds_" + p + "_impute.csv"
                           for p in ds_props for id in exp_ids]
        # check if all required data exists
        diff = list(set(true_pred_files) - set(pred_files["names"]))
        if diff:
            invalid_reasons.append("File not found : " + "', '".join(diff))

    if not invalid_reasons:
        # get all rownames and colnames of gs files
        gs_names = [get_dim_name(gs_df) for gs_df in gs_files["files"]]
        # multiply number of downsampling props to match index of pred files
        true_names = gs_names * len(ds_props)
        # validate each prediction file
        for index, pred_df in enumerate(pred_files["files"]):
            file_name = pred_files["names"][index]
            # check if names of row/col match with what in goldstandard for each exp
            pred_names = get_dim_name(pred_df)
            cp1 = set(pred_names["rownames"]).issubset(
                true_names[index]["rownames"])
            cp2 = set(pred_names["colnames"]).issubset(
                true_names[index]["colnames"])
            if not (cp1 and cp2):
                invalid_reasons.append(
                    file_name + ": Do not contain all genes or cells")
            else:
                # check if all values are numeric
                cp3 = pred_df.apply(lambda s: pd.to_numeric(
                    s, errors='coerce').isnull().any())
                if cp3.any():
                    invalid_reasons.append(
                        file_name + ": Not all values are numeric")
                # check if all values are >= 0
                elif (pred_df < 0).any().any():
                    invalid_reasons.append(
                        file_name + ": Negative value is not allowed")
    print(invalid_reasons)
    validate_status = "INVALID" if invalid_reasons else "VALIDATED"
    result = {'submission_errors': "\n".join(invalid_reasons),
              'submission_status': validate_status}
    with open(args.results, 'w') as o:
        o.write(json.dumps(result))


if __name__ == "__main__":
    main()