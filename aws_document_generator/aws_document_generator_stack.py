from aws_cdk import (
    Stack,
    Aws,
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as _gateway,
    aws_s3 as _s3,
    aws_dynamodb as _dynamodb,
    aws_iam as _iam,
)
from constructs import Construct

S3_ACCESS_POINT_NAME = "document_bucket_access_point"
OBJECT_LAMBDA_ACCESS_POINT_NAME = "s3-object-lambda-ap"

JWT_AUDIENCE = "account"
JWT_AUTHORITY_DOMAIN = "shield.nathos.dev/realms/shield"

TABLE_NAME = "document-table"


class AwsDocumentGeneratorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDb Table
        document_table = _dynamodb.Table(
            self,
            TABLE_NAME,
            table_name=TABLE_NAME,
            partition_key=_dynamodb.Attribute(
                name="document_id", type=_dynamodb.AttributeType.STRING
            ),
        )

        document_bucket = _s3.Bucket(
            self,
            "og-template-bucket",
            bucket_name="og-document-generator-bucket",
            # public_read_access=True,
        )

        # document_bucket_policy = _iam.PolicyStatement(
        #     actions=["s3:GetObject"],
        #     resources=[f"{document_bucket.bucket_arn}/generated/*"],
        #     effect=_iam.Effect.ALLOW,
        #     principals=[_iam.AnyPrincipal()],
        # )
        #
        # document_bucket.add_to_resource_policy(
        #     permission=document_bucket_policy,
        # )

        authorizer_function = _lambda.DockerImageFunction(
            self,
            "authorizer-function",
            function_name="authorizer-function",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="lambda/authorizer"
            ),
            timeout=Duration.minutes(2),
            memory_size=1024,
            architecture=_lambda.Architecture.ARM_64,
            # vpc=vpc,
            # vpc_subnets=_ec2.SubnetSelection(
            #     subnet_type=_ec2.SubnetType.PRIVATE_ISOLATED
            # ),
            environment={
                "JWT_AUTHORITY_DOMAIN": JWT_AUTHORITY_DOMAIN,
                "JWT_AUDIENCE": JWT_AUDIENCE,
            },
        )

        generate_pdf_function = _lambda.DockerImageFunction(
            self,
            "generate-pdf-function",
            function_name="generate-pdf-function",
            code=_lambda.DockerImageCode.from_image_asset(directory="lambda/generate"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            architecture=_lambda.Architecture.ARM_64,
            # vpc=vpc,
            # vpc_subnets=_ec2.SubnetSelection(
            #     subnet_type=_ec2.SubnetType.PRIVATE_ISOLATED
            # ),
            environment={
                "BUCKET_NAME": document_bucket.bucket_name,
                "TABLE_NAME": document_table.table_name,
            },
        )

        load_pdf_function = _lambda.DockerImageFunction(
            self,
            "load-pdf-function",
            function_name="load-pdf-function",
            code=_lambda.DockerImageCode.from_image_asset(directory="lambda/load"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            architecture=_lambda.Architecture.ARM_64,
            environment={"TABLE_NAME": document_table.table_name},
        )

        document_bucket.grant_read_write(generate_pdf_function)
        document_table.grant_write_data(generate_pdf_function)
        document_table.grant_read_data(load_pdf_function)

        api = _gateway.RestApi(
            self,
            "document-api-gateway",
            rest_api_name="document-api-gateway",
            description="This service generates PDFs",
            cloud_watch_role=True,
        )

        authorizer = _gateway.RequestAuthorizer(
            self,
            handler=authorizer_function,
            id="gateway-keycloak-authorizer",
            authorizer_name="gateway-keycloak-authorizer",
            results_cache_ttl=Duration.minutes(0),
            identity_sources=[_gateway.IdentitySource.header("Authorization")],
        )

        mock_cors_integration = _gateway.MockIntegration(
            integration_responses=[
                {
                    "statusCode": "200",
                    "responseParameters": {
                        "method.response.header.Access-Control-Allow-Headers": "'*'",
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Methods": "'OPTIONS,GET,PUT,POST,DELETE'",
                    },
                }
            ],
            passthrough_behavior=_gateway.PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={"application/json": '{"statusCode": 200}'},
        )

        integration_responses = [
            {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Origin": True,
                    "method.response.header.Access-Control-Allow-Methods": True,
                },
            }
        ]

        generate_pdf_resource = api.root.add_resource("generate")
        generate_function_integration = _gateway.LambdaIntegration(
            handler=generate_pdf_function, proxy=True
        )
        generate_pdf_resource.add_method(
            http_method="POST",
            authorizer=authorizer,
            integration=generate_function_integration,
        )
        generate_pdf_resource.add_method(
            "OPTIONS", mock_cors_integration, method_responses=integration_responses
        )

        load_pdf_resource = api.root.add_resource("load")
        load_function_integration = _gateway.LambdaIntegration(
            handler=load_pdf_function,
            proxy=True,
        )
        load_pdf_resource.add_method(
            http_method="GET",
            authorizer=authorizer,
            integration=load_function_integration,
            request_parameters={"method.request.querystring.document": True},
        )
        load_pdf_resource.add_method(
            "OPTIONS", mock_cors_integration, method_responses=integration_responses
        )
