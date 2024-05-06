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
    aws_s3objectlambda as _s3objectlambda
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
            #bucket_name="og-document-generator-bucket",
            access_control=_s3.BucketAccessControl.BUCKET_OWNER_FULL_CONTROL,

        )

        document_bucket.add_to_resource_policy(
            _iam.PolicyStatement(
                actions=["*"],
                principals=[_iam.AnyPrincipal()],
                resources=[
                    document_bucket.bucket_arn,
                    document_bucket.arn_for_objects("*")
                ],
                conditions={
                    "StringEquals": {
                        "s3:DataAccessPointAccount": f"{Aws.ACCOUNT_ID}"
                    }
                }
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

        # Object lambda s3 access
        generate_pdf_function.add_to_role_policy(
            _iam.PolicyStatement(
                effect=_iam.Effect.ALLOW,
                resources=["*"],
                actions=["s3-object-lambda:WriteGetObjectResponse"]
            )
        )

        # Restrict Lambda to be invoked from own account
        generate_pdf_function.add_permission("invocationRestriction",
                                             action="lambda:InvokeFunction",
                                             principal=_iam.AccountRootPrincipal(),
                                             source_account=Aws.ACCOUNT_ID)

        # Associate Bucket's access point with lambda get access
        if generate_pdf_function.role is not None:
            policy_doc = _iam.PolicyDocument()
            policy_statement = _iam.PolicyStatement(
                effect=_iam.Effect.ALLOW,
                actions=["s3:GetObject"],
                principals=[
                    _iam.ArnPrincipal(generate_pdf_function.role.role_arn)
                ],
                resources=[
                   f"{self.access_point}/object/*"
                ])

        policy_statement.sid = "AllowLambdaToUseAccessPoint"
        policy_doc.add_statements(policy_statement)

        document_bucket_access_point = _s3.CfnAccessPoint(
            self, "document_bucket_access_point",
            bucket=document_bucket.bucket_name,
            # name=S3_ACCESS_POINT_NAME,
            policy=policy_doc
        )

        # Access point to receive GET request and use lambda to process objects
        object_lambda_ap = _s3objectlambda.CfnAccessPoint(
            self,
            "document_bucket_access_point_object_lambda",
            name=OBJECT_LAMBDA_ACCESS_POINT_NAME,
            object_lambda_configuration=_s3objectlambda.CfnAccessPoint.ObjectLambdaConfigurationProperty(
                supporting_access_point=self.access_point,
                transformation_configurations=[
                    _s3objectlambda.CfnAccessPoint.TransformationConfigurationProperty(
                        actions=["GetObject"],
                        content_transformation={
                            "AwsLambda": {
                                "FunctionArn": f"{generate_pdf_function.function_arn}"
                            }
                        }
                    )
                ]
            )
        )

        CfnOutput(self, "exampleBucketArn", value=document_bucket.bucket_arn)
        CfnOutput(self, "objectLambdaArn",
                  value=generate_pdf_function.function_arn)
        CfnOutput(self, "objectLambdaAccessPointArn", value=object_lambda_ap.attr_arn)
        CfnOutput(self, "objectLambdaAccessPointUrl",
                  value=f"https://console.aws.amazon.com/s3/olap/{Aws.ACCOUNT_ID}/"
                        f"{OBJECT_LAMBDA_ACCESS_POINT_NAME}?region={Aws.REGION}")

        api = _gateway.LambdaRestApi(
            self,
            "api-gateway",
            rest_api_name="api-gateway",
            handler=generate_pdf_function,
            proxy=False
        )

        generate_pdf_resource = api.root.add_resource("generate")
        generate_pdf_resource.add_method("POST")
