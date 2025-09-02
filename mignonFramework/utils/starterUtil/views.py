# mignonFramework/utils/starterUtil/views.py
from flask import Blueprint, render_template, request, jsonify, make_response, send_from_directory
from mignonFramework.utils.utilClass.Curl2Request import CurlToRequestsConverter
from .code_generator import generate_scraper_code_and_configs
import io
import zipfile
import os
import traceback

bp = Blueprint('starter', __name__)
current_dir = os.path.dirname(os.path.abspath(__file__))
@bp.route('/')
def landing():
    return render_template('landing.html')

@bp.route('/app')
def app():
    return render_template('app.html')


@bp.route('/favicon.ico')
def favicon():
    static_folder = os.path.join(current_dir, 'static', "ico")
    return send_from_directory(static_folder, 'favicon.ico')


@bp.route('/convert_and_run', methods=['POST'])
def convert_and_run():
    data = request.get_json()
    curl_command = data.get('curl_command')
    if not curl_command: return jsonify({"error": "No cURL command provided"}), 400
    try:
        converter = CurlToRequestsConverter(curl_command)
        generated_code, execution_output, is_json, status_code = converter.convert_and_execute()
        parsed_details = converter._parsed_data

        return jsonify({
            "generated_code": generated_code, "execution_output": execution_output,
            "status_code": status_code, "is_json": is_json,
            "url": parsed_details.get('url', ''),
            "method": parsed_details.get('method', 'post'),
            "extracted_headers": parsed_details.get('headers', {}),
            "extracted_cookies": parsed_details.get('cookies', {}),
            "extracted_json_data": parsed_details.get('json', {}),
            "extracted_params": parsed_details.get('params', {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/generate_final_code', methods=['POST'])
def generate_final_code_route():
    try:
        app_state = request.get_json()
        if not app_state:
            return jsonify({"error": "No application state provided"}), 400

        # FIX: The generator now returns a dictionary of all files to be created.
        generated_files = generate_scraper_code_and_configs(app_state)

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # FIX: Iterate through the new file structure and write to the zip archive.

            # Write Python files
            for filename, content in generated_files.get("py", {}).items():
                zf.writestr(filename, content)

            # Write INI files
            for filename, content in generated_files.get("ini", {}).items():
                config_path = os.path.join('resources', 'config', filename)
                zf.writestr(config_path, content)

            # Write JS files
            for filename, content in generated_files.get("js", {}).items():
                js_path = os.path.join('resources', 'js', filename)
                zf.writestr(js_path, content)

        memory_file.seek(0)

        response = make_response(memory_file.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = 'attachment; filename=mignon_scraper.zip'

        return response

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"服务器在打包时发生意外错误: {e}"}), 500
