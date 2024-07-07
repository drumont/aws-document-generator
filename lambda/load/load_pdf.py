import os
import boto3
import logging
import json

dynamodb_client = boto3.client("dynamodb")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        document_table = os.environ.get("TABLE_NAME")

        query_string = event.get("queryStringParameters")
        document_id = query_string.get("document")

        if document_id is None:
            raise Exception("document_id is missing")

        logger.info("Search document object with key {}".format(document_id))

        document_object = dynamodb_client.get_item(
            TableName=document_table, Key={"document_id": {"S": document_id}}
        )

        if document_object.get("Item") is None:
            raise Exception("Document not found")

        logger.info(
            "Successfully retrieved document object with id {}".format(
                document_object["Item"]["document_id"]["S"]
            )
        )

        document = {
            "document_id": document_object["Item"]["document_id"]["S"],
            "document_url": document_object["Item"]["document_url"]["S"],
        }

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Methods": "OPTIONS,GET",
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
