from flask import Blueprint, request, jsonify
from ..services.ai_service import search_similar_chunks, generate_content_from_model
from ..services.document_processor import process_document_task

api_bp = Blueprint('api', __name__)

@api_bp.route('/query', methods=['POST'])
def query():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Invalid JSON or missing request body'}), 400

        query_text = json_data.get('query')
        db_name = json_data.get('db_name', 'default')

        if not query_text:
            return jsonify({'error': 'Missing required field: query'}), 400
        if not db_name:
            return jsonify({'error': 'Missing required field: db_name'}), 400

        context = search_similar_chunks(query_text, db_name)

        prompt = f"""
        You are an AI assistant trained on the Arez Customer Support Manual.
        Use ONLY the information from the following document excerpts to answer the user's question clearly.

        --- DOCUMENT CONTEXT START ---
        {context[:15000]}
        --- DOCUMENT CONTEXT END ---

        Question: {query_text}

        Answer step-by-step, referencing relevant modules when possible.
        """

        response_text = generate_content_from_model(prompt)
        return jsonify({'result': response_text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/process-document', methods=['POST'])
def process_document():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Invalid JSON or missing request body'}), 400

        process_task_id = json_data.get('process_task_id')
        file_url = json_data.get('file_url')
        db_name = json_data.get('db_name', 'default')

        if not process_task_id:
            return jsonify({'error': 'Missing required field: process_task_id'}), 400
        if not file_url:
            return jsonify({'error': 'Missing required field: file_url'}), 400

        task = process_document_task.delay(process_task_id, file_url, db_name)

        return jsonify({
            'status': 'processing',
            'task_id': task.id,
            'process_task_id': process_task_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    try:
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        response = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }
        
        # If task failed, include error message
        if task_result.status == 'FAILURE':
            response['error'] = str(task_result.result)
            
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
