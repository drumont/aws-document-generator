import os
import boto3
import io
import logging
import json


s3_client = boto3.client('s3')
bucket_name = os.environ['BUCKET_NAME']

logger = logging.getLogger()


def lambda_handler(event, context):
    try:

        body = json.loads(event['body'])

        html_template_name = body['html_template_name']
        css_template_name = body['css_template_name']

        if html_template_name is None or css_template_name is None:
            raise Exception("html_template_name or css_template_name is missing")

        html_object = s3_client.get_object(Bucket=bucket_name, Key=html_template_name)
        css_object = s3_client.get_object(Bucket=bucket_name, Key=css_template_name)

        if html_object is None or css_object is None:
            raise Exception("Error while downloading html or css file")

        html_file = io.BytesIO(html_object['Body'].read())
        css_file = io.BytesIO(css_object['Body'].read())

        html_content = html_file.getvalue().decode('utf-8')
        css_content = css_file.getvalue().decode('utf-8')

        logger.info(f"html_content: {html_content}")
        logger.info(f"css_content: {css_content}")

        return {
            'statusCode': 200,
            'body': "Success"
        }

    except Exception as exec_code:
        return {
            'statusCode': 500,
            'body': str(exec_code)
        }
