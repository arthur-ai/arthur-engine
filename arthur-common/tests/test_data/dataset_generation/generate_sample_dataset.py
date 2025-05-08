import argparse
import json
import math
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3
import pandas as pd
from axios_dataset import AxiosDataset
from botocore.exceptions import NoCredentialsError
from expel_dataset import ExpelDataset
from google.api_core import retry
from google.cloud import bigquery
from m_and_a_dataset import MAndADataset
from sample_dataset import SampleDataset


def write_to_s3(data: List[Dict[str, Any]], bucket: str, file_name: str) -> bool:
    s3 = boto3.client("s3")
    try:
        # Convert data to DataFrame and write as parquet if file ends with .parquet
        if file_name.endswith(".parquet"):
            df = pd.DataFrame(data)
            parquet_buffer = df.to_parquet()
            s3.put_object(Body=parquet_buffer, Bucket=bucket, Key=file_name)
        else:
            json_data = json.dumps(data, indent=2)
            s3.put_object(Body=json_data, Bucket=bucket, Key=file_name)
        print(f"Successfully uploaded {file_name} to {bucket}")
        return True
    except NoCredentialsError:
        print("Credentials not available")
        return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False


def write_to_local(data: List[Dict[str, Any]], directory: str, file_name: str) -> bool:
    try:
        full_path = os.path.join(directory, file_name)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write as parquet if file ends with .parquet
        if file_name.endswith(".parquet"):
            df = pd.DataFrame(data)
            df.to_parquet(full_path)
        else:
            with open(full_path, "w") as f:
                json.dump(data, f, indent=2)
        print(f"Successfully wrote {file_name} to {directory}")
        return True
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False


def write_to_bigquery(
    dataset: SampleDataset,
    data_batch: List[Dict[str, Any]],
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> bool:
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    try:
        rows = [dataset.format_row_as_json(data) for data in data_batch]
        errors = client.insert_rows_json(
            table_ref,
            rows,
            retry=retry.Retry(deadline=30),
        )
        if errors:
            print(f"Encountered errors while inserting batch: {errors}")
            return False

        print(f"Successfully wrote {len(rows)} records to BigQuery table {table_ref}")
        return True
    except Exception as e:
        print(f"An error occurred writing to BigQuery: {str(e)}")
        return False


def dataset_from_arg(dataset_type: str) -> SampleDataset:
    if dataset_type == "expel":
        return ExpelDataset()
    elif dataset_type == "axios":
        return AxiosDataset()
    elif dataset_type == "manda":
        return MAndADataset()
    else:
        raise ValueError(f"Unsupported dataset type: {dataset_type}")


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate sample dataset")
    parser.add_argument(
        "--output",
        choices=["local", "s3", "bigquery"],
        default="local",
        help="Output destination (local, s3, or bigquery)",
    )
    parser.add_argument(
        "--path",
        default="./output",
        help="Local directory, S3 bucket name, or BigQuery project ID",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to generate data for",
    )
    parser.add_argument(
        "--inferences",
        type=int,
        default=2,
        help="Number of inferences per day",
    )
    parser.add_argument("--dataset-id", help="BigQuery dataset ID")
    parser.add_argument("--table-id", help="BigQuery table ID")
    parser.add_argument(
        "--dataset",
        choices=["expel", "axios", "manda"],
        default="expel",
        help="Type of dataset to generate",
    )
    parser.add_argument(
        "--add-variation",
        default=False,
        action="store_true",
    )
    return parser


if __name__ == "__main__":
    arg_parser = arg_parser()
    args = arg_parser.parse_args()
    if args.output == "bigquery" and (not args.dataset_id or not args.table_id):
        raise ValueError("dataset-id and table-id are required for BigQuery output")

    num_inferences_per_day = args.inferences
    num_days_to_sample = args.days
    output_path = args.path
    start_date = datetime(2024, 10, 1)
    end_date = start_date + timedelta(days=num_days_to_sample)
    dataset = dataset_from_arg(args.dataset)

    current_date = start_date
    batch_size = 3000
    batch = []

    while current_date < end_date:
        inferences_sampled = 0
        # generate num_inferences_per_day for each day. each file should be sized according to dataset specs.
        # one dataset might want one inference per file, another may want several.
        if args.add_variation:
            # if add variation is specified, fluctuate the number of inferences each day
            inferences_today = num_inferences_per_day + random.randint(
                0,
                math.floor(num_inferences_per_day * 1.2),
            )
        else:
            inferences_today = num_inferences_per_day
        while inferences_sampled < inferences_today:
            sample = []
            timestamp = current_date
            for j in range(dataset.inferences_per_file):
                if inferences_sampled + j < inferences_today:
                    # add random number of seconds to date to make inference from a point in the day
                    timestamp = current_date + timedelta(
                        seconds=random.randint(0, 86399),
                    )
                    sample.append(dataset.generate_sample(timestamp))
                else:
                    break
            inferences_sampled += len(sample)

            # write to output data stores
            if args.output == "bigquery":
                batch += sample
                if len(batch) >= batch_size:
                    success = write_to_bigquery(
                        dataset,
                        batch,
                        output_path,
                        args.dataset_id,
                        args.table_id,
                    )
                    if success:
                        print(f"Successfully wrote {len(batch)} records to BigQuery")
                    else:
                        print(f"Failed to write batch to BigQuery")
                        exit(1)
                    batch = []  # Clear the batch after writing
            else:
                file_name = dataset.file_name(timestamp)
                if args.output == "s3":
                    success = write_to_s3(sample, output_path, file_name)
                else:
                    success = write_to_local(sample, output_path, file_name)

                if success:
                    print(
                        f"Generated {len(sample)} inferences for {current_date.strftime('%Y%m%d')} and saved them to {args.output}: {file_name}",
                    )
                else:
                    print(
                        f"Failed to save {len(sample)} inferences for {current_date.strftime('%Y%m%d')} to {args.output}",
                    )

        # Move to the next day
        current_date += timedelta(days=1)

    # Write any remaining records in the batch to bigquery
    if args.output == "bigquery" and batch:
        success = write_to_bigquery(
            dataset,
            batch,
            output_path,
            args.dataset_id,
            args.table_id,
        )
        if success:
            print(f"Successfully wrote final batch of {len(batch)} records to BigQuery")
        else:
            print(f"Failed to write final batch to BigQuery")

    print(
        f"Finished generating files over a range of {num_days_to_sample} days starting on Oct 1, 2024.",
    )
