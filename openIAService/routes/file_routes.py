from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
from services.files_processing_service import process_pdf
from core.exceptions.custom_exceptions import APIException
from core.logging.logger import get_app_logger

file_bp = Blueprint('file', __name__)
logger = get_app_logger()
UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@file_bp.route('/upload-pdf/', methods=['POST'])
def upload_pdf():
    """Maneja la carga y procesamiento de archivos PDF."""
    if 'file' not in request.files:
        raise APIException(
            message="No file part in the request",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    file = request.files['file']
    if file.filename == '':
        raise APIException(
            message="No file selected",
            status_code=400,
            code="VALIDATION_ERROR",
        )

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        content = process_pdf(file_path)
        logger.info(f"PDF cargado y procesado: {filename}")
        return jsonify({"message": "PDF uploaded and content processed successfully", "content": content}), 200

    raise APIException(
        message="Only PDF files are allowed",
        status_code=400,
        code="UNSUPPORTED_FILE_EXTENSION",
    )
