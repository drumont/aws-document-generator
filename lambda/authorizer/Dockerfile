FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}
COPY authorizer.py ${LAMBDA_TASK_ROOT}

RUN dnf install -y libjpeg-turbo-devel libffi-devel cairo pango

RUN pip install --no-cache-dir -r requirements.txt

CMD ["authorizer.lambda_handler"]