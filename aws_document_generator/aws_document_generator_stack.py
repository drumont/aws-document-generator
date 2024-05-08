from aws_cdk import (
    # Duration,
    Stack,
    Aws,
    CfnOutput,
    # aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_apigateway as _gateway,
    aws_s3 as _s3,
    aws_iam as _iam,
    aws_s3objectlambda as _s3objectlambda, BundlingOptions
)
from constructs import Construct

S3_ACCESS_POINT_NAME = "document_bucket_access_point"
OBJECT_LAMBDA_ACCESS_POINT_NAME = "s3-object-lambda-ap"


class AwsDocumentGeneratorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.access_point = f"arn:aws:s3:{Aws.REGION}:{Aws.ACCOUNT_ID}:accesspoint/" \
                            f"{S3_ACCESS_POINT_NAME}"

        # The code that defines your stack goes here
        document_bucket = _s3.Bucket(
            self,
            "og-template-bucket",
            bucket_name="og-document-generator-bucket",
            access_control=_s3.BucketAccessControl.BUCKET_OWNER_FULL_CONTROL,

        )

        generate_pdf_function = _lambda.Function(
            self,
            "generate-pdf-function",
            function_name="generate-pdf-function",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(path="lambda",
                                         bundling=BundlingOptions(
                                                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                                                command=[
                                                    "bash", "-c",
                                                    "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                                                ]
                                            )),
            handler="generate_pdf.lambda_handler",
            environment={
                "BUCKET_NAME": document_bucket.bucket_name
            }
        )

        document_bucket.grant_read_write(generate_pdf_function)

        api = _gateway.LambdaRestApi(
            self,
            "api-gateway",
            rest_api_name="api-gateway",
            handler=generate_pdf_function,
            proxy=False
        )

        generate_pdf_resource = api.root.add_resource("generate")
        generate_pdf_resource.add_method("POST")
