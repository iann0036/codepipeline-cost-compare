# CodePipeline Cost Compare

> Compare the costs of V1 and V2 CodePipeline types based on historic usage

## Usage

```
python3 main.py
```

The script will process all pipelines within your AWS account and may take a few minutes to run in its entirety. Per pipeline assessments will be printed as they complete.

For credentials, the [standard chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) is respected, including the `AWS_REGION` environment variable.

## Requirements

- Python 3.6+
- boto3 (latest)
