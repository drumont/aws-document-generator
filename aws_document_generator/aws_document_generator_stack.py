from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_apigateway as _gateway,
    aws_s3 as _s3,
    aws_iam as _iam
)
from constructs import Construct


class AwsDocumentGeneratorStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        document_bucket = _s3.Bucket(
            self,
            "og-template-bucket",
            bucket_name="og-document-generator-bucket",
            access_control=_s3.BucketAccessControl.BUCKET_OWNER_FULL_CONTROL
        )

        document_bucket.add_to_resource_policy(
            _iam.PolicyStatement(
                actions=["*"],
                principals=[_iam.AnyPrincipal()],
                resources=[
                    document_bucket.bucket_arn,
                    document_bucket.arn_for_objects("*")
                ],
            )
        )

        generate_pdf_function = _lambda.Function(
            self,
            "generate-pdf-function",
            function_name="generate-pdf-function",
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset("lambda"),
            handler="generate_pdf.lambda_handler",
            environment={
                "BUCKET_NAME": document_bucket.bucket_name
            }
        )

        generate_pdf_function.add_to_role_policy(
            _iam.PolicyStatement(
                effect=_iam.Effect.ALLOW,
                resources=["*"],
                actions=["s3-object-lambda:WriteGetObjectResponse"]
            )
        )

        api = _gateway.LambdaRestApi(
            self,
            "api-gateway",
            rest_api_name="api-gateway",
            handler=generate_pdf_function,
            proxy=False
        )

        generate_pdf_resource = api.root.add_resource("generate")
        generate_pdf_resource.add_method("POST")
