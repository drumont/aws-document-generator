import os
import uuid

import boto3
import io
import logging
import json
from jinja2 import Template
from weasyprint import HTML, CSS


s3_client = boto3.client('s3')
bucket_name = os.environ['BUCKET_NAME']

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def render_template(html_content: str, context: dict) -> str:
    template = Template(html_content)
    html_content = template.render(context)
    return html_content


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])

        html_template_name = body['html_template_name']
        css_template_name = body['css_template_name']
        variables: dict = body['variables']

        if html_template_name is None or css_template_name is None:
            raise Exception("html_template_name or css_template_name is missing")

        html_object = s3_client.get_object(Bucket=bucket_name, Key=html_template_name)
        css_object = s3_client.get_object(Bucket=bucket_name, Key=css_template_name)

        if html_object is None or css_object is None:
            raise Exception("Error while downloading html or css file")

        html_file = io.BytesIO(html_object['Body'].read())
        css_file = io.BytesIO(css_object['Body'].read())

        html_content = html_file.getvalue().decode('utf-8')
        css = css_file.getvalue().decode('utf-8')

        template: str = render_template(html_content, variables)
        document = HTML(string=template, encoding="utf-8")

        logger.info("Generating PDF")

        pdf = document.write_pdf(stylesheets=[CSS(string=css)])

        pdf_key: str = f"{str(uuid.uuid4())}.pdf"

        logger.info(f"PDF generated {pdf.decode('utf-8')}")

        logger.info(f"Uploading {pdf_key} to {bucket_name}")

        s3_client.put_object(Bucket=bucket_name, Key=pdf_key, Body=pdf)

        return {
            'statusCode': 200,
            'body': "Success"
        }

    except Exception as exec_code:
        return {
            'statusCode': 500,
            'body': str(exec_code)
        }
