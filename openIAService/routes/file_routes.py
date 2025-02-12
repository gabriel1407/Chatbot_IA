from flask import Blueprint, request, jsonify
import os
import logging
from werkzeug.utils import secure_filename
from services.files_processing_service import process_pdf

file_bp = Blueprint('file', __name__)
UPLOAD_FOLDER = os.path.join('local', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@file_bp.route('/upload-pdf/', methods=['POST'])
def upload_pdf():
    """Maneja la carga y procesamiento de archivos PDF."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        content = process_pdf(file_path)
        return jsonify({"message": "PDF uploaded and content processed successfully", "content": content}), 200
    else:
        return jsonify({"error": "Only PDF files are allowed"}), 400
