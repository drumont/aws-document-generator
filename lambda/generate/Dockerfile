FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ./
COPY generate.py ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["generate_pdf.lambda_handler"]