import logging
import os

import cloudstorage
import six
from flask import Flask, render_template, request
from google.appengine.api import app_identity
from google.cloud import storage
from pyPdf import PdfFileWriter, PdfFileReader


app = Flask(__name__)


cloudstorage.set_default_retry_params(
    cloudstorage.RetryParams(
        initial_delay=0.2, max_delay=5.0, backoff_factor=2, max_retry_period=15
        ))


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/submitted', methods=['POST'])
def submitted_form():
    BUCKET_NAME = os.environ.get('BUCKET_NAME',
                                 app_identity.get_default_gcs_bucket_name())

    uploaded_files = request.files.getlist('files')

    if not uploaded_files:
        return 'No file uploaded.', 400

    # Merge files
    output = PdfFileWriter()
    for input in uploaded_files:
        append_pdf(PdfFileReader(input), output)
    # end merge

    # Save to Storage
    file_name = 'merged.pdf'
    path = '/' + BUCKET_NAME + '/' + file_name
    with cloudstorage.open(path, 'w',
                           content_type='application/pdf') as output_stream:
        output.write(output_stream)
    # end save

    url = get_url(BUCKET_NAME, file_name)

    return render_template(
        'submitted_form.html',
        link=url
    )


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


def append_pdf(input, output):
    [output.addPage(input.getPage(page_num)) for page_num in range(input.numPages)]


def get_url(bucket_name, filename):
    """
    Gets the uri to the object.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)

    url = blob.public_url

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')

    return url
