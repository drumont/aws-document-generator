import os
import uuid
import boto3
import io
import logging
import json
from jinja2 import Template
from weasyprint import HTML, CSS

s3_client = boto3.client("s3")
dynamodb_client = boto3.client("dynamodb")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def render_template(html_content: str, context: dict) -> str:
    template = Template(html_content)
    html_content = template.render(context)
    return html_content


# TODO: Out Get S3 Object in a function for better error handling


def lambda_handler(event, context):
    try:
        bucket_name = os.environ.get("BUCKET_NAME")
        document_table = os.environ.get("TABLE_NAME")

        body = json.loads(event.get("body"))

        html_template_name = body.get("html_template_name")
        css_template_name = body.get("css_template_name")
        document_id = body.get("document_id")
        variables: dict = body.get("variables")

        if html_template_name is None or css_template_name is None:
            raise Exception("html_template_name or css_template_name is missing")

        html_object = s3_client.get_object(Bucket=bucket_name, Key=html_template_name)
        css_object = s3_client.get_object(Bucket=bucket_name, Key=css_template_name)

        if html_object is None or css_object is None:
            raise Exception("Error while downloading html or css file")

        html_file = io.BytesIO(html_object["Body"].read())
        css_file = io.BytesIO(css_object["Body"].read())

        html_str = html_file.getvalue().decode("utf-8")
        css_str = css_file.getvalue().decode("utf-8")

        template: str = render_template(html_str, variables)
        document = HTML(string=template, encoding="utf-8")

        pdf = document.write_pdf(stylesheets=[CSS(string=css_str)])

        pdf_key: str = f"generated/{str(uuid.uuid4())}.pdf"

        logger.info(f"Uploading {pdf_key} to {bucket_name}")

        s3_client.put_object(
            Bucket=bucket_name,
            Key=pdf_key,
            Body=pdf,
            ContentType="application/pdf",
            Metadata={"document-id": document_id},
        )

        logger.info(f"Storing {pdf_key} in {document_table} store")

        dynamodb_client.put_item(
            TableName=document_table,
            Item={
                "pdf_key": {"S": pdf_key},
                "document_id": {"S": document_id},
                "document_url": {
                    "S": f"https://{bucket_name}.s3.amazonaws.com/{pdf_key}"
                },
                "variables": {"S": json.dumps(variables)},
            },
        )

        document = {
            "document_id": document_id,
            "document_url": f"https://{bucket_name}.s3.amazonaws.com/{pdf_key}",
        }

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps(document),
        }

    except Exception as exec_code:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "OPTIONS,GET",
            },
            "body": str(exec_code),
        }
