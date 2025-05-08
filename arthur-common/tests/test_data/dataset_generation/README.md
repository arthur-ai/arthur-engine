## Prerequisites—Install Dependencies

`pip install google-cloud-bigquery`
`pip install pyarrow`

## Running generate sample dataset script

To generate sample data run the following script: `generate_sample_dataset.py`.
The script takes the following options:

1. `--output`: can be `local`, `s3` or `bigquery`; `local` writes the data to your local filesystem,
   `s3` writes the data to an AWS S3 bucket, `bigquery` writes the data to a `BigQuery` table in GCP.
2. `--dataset`: Type of dataset to generate. Can choose between `expel` demo dataset, `axios` demo dataset, and
   `manda`.
2. `--path`: name of S3 bucket, BigQuery project ID, or directory to write inferences to.
3. `--days`: Number of days to generate data for.
4. `--inferences`: Number of inferences to generate per day.
5. `--dataset-id`: BigQuery dataset ID. Required for writing to BigQuery.
6. `--table-id`: BigQuery table ID. Required for writing to BigQuery.
7. `--add-variation`: Adds randomness to the amount of inferences per day to make the graphs more variable

Example: Write 2 inferences per day over 2 days to local folder (run from `test_data/dataset_generation` root):
`python generate_sample_dataset.py --output local --path ./output --days 2 --inferences 2 --dataset expel`

Example: Write 2 inferences per day to s3 (AWS creds will be sourced from environment):

```bash
aws-profile-sandbox
python generate_sample_dataset.py --output s3 --path v4-expel-tabular-data-demo --days 2 --inferences 2 --dataset expel
```

Note: If you're writing a lot of inferences at once, it may be faster to write the inferences to a local
folder and then sync that folder with the S3 bucket:

```bash
aws s3 sync local_folder s3://bucket-name
```

Example: Write 2 inferences per day to BigQuery:

```bash
python generate_sample_dataset.py --output bigquery --path oval-day-438819-k4 --days 2 --inferences 2 --dataset-id expel_tabular_data_demo --table-id b306e823-9fea-4adb-bbbc-670bea1a9c2e --dataset expel
```

This will only work if you've already followed the Authenticating with GCP section in the app plane ReadMe so that
you're already authenticated with GCP.

## Generation of existing demo datasets

These are the commands used to generate existing demo datasets, used in the E2E tests.

### Expel

In S3:

```bash
python generate_sample_dataset.py --output s3 --path v4-expel-tabular-data-demo --days 600 --inferences 3000 --dataset expel
```

In BigQuery:

```bash
python generate_sample_dataset.py --output bigquery --path oval-day-438819-k4 --days 600 --inferences 3000 --dataset-id expel_tabular_data_demo --table-id b306e823-9fea-4adb-bbbc-670bea1a9c2e --dataset expel
```

In GCS:
For this dataset, we just wrote the S3 sample files to a local folder & synced that folder with GCS.

```bash
python generate_sample_dataset.py --output local --path ./output --days 600 --inferences 3000 --dataset expel
gsutil -m rsync -r ./output gs://expel-tabular-data-demo/1889f7a2-c49a-4d07-b55d-3679d12e5110
```

### Axios

In S3:

```bash
python generate_sample_dataset.py --output s3 --path axios-demo-dataset --days 300 --inferences 100 --dataset axios
```

### BAM M&A Dataset

In BigQuery:

```bash
python generate_sample_dataset.py --output bigquery --path oval-day-438819-k4 --days 365 --inferences 30 --dataset-id m_and_a_demo_dataset --table-id m_and_a_demo_dataset --dataset manda --add-variation
```
