import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_document_generator.aws_document_generator_stack import AwsDocumentGeneratorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_document_generator/aws_document_generator_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsDocumentGeneratorStack(app, "aws-document-generator")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
