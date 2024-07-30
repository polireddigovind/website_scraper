from flask import Flask, request, jsonify,send_file,make_response
from flask_cors import CORS
from testing import scrap_sample_data
from scrap_full_file import scrap_fillurls_file,set_socketio_instance
import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from flask_socketio import SocketIO

app = Flask(__name__)
CORS(app) 
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Pass the socketio instance to the scrap_fillurls module
set_socketio_instance(socketio)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No file selected for uploading'}), 400
    if file and file.filename.endswith('.csv'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'scrap.csv')
        file.save(file_path)
        return jsonify({'message': 'File successfully uploaded'}), 200
    else:
        return jsonify({'message': 'Allowed file types are csv'}), 400


@app.route('/urls', methods=['GET'])
def get_urls_data():
    try:
        textPrompt = request.args.get('textPrompt', '').strip()
        model = request.args.get('model', '').strip()
        textPrompt_openai = request.args.get('textPrompt_openai', '').strip()
        openaimodel = request.args.get('openaimodel', '').strip()
        file_name = request.args.get('file_name', '').strip()

        url1 = request.args.get('url1', '').strip()
        url2 = request.args.get('url2', '').strip()
        url3 = request.args.get('url3', '').strip()
        urls = [url for url in [url1, url2, url3] if url]

        if model == '':
            return jsonify({'error': 'Please select a model'}), 400
        if len(textPrompt) == 0:
            return jsonify({'error': 'Please provide a non-empty textPrompt'}), 400
        if len(textPrompt_openai) == 0 and len(openaimodel) > 0:
            return jsonify({'error': 'Please provide a non-empty textPrompt_openai'}), 400
        if len(textPrompt_openai) > 0 and openaimodel == '':
            return jsonify({'error': 'Please select an openaimodel'}), 400


        urls_data = scrap_sample_data(textPrompt, model, textPrompt_openai, openaimodel, urls,file_name)
        
        app.logger.info(f"textPrompt: {textPrompt}, URLs: {urls}")
        return jsonify({'urls': urls_data})

    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500
    

@app.route('/fullurls', methods=['GET'])
def get_fullurls_data():
    try:
        textPrompt = request.args.get('textPrompt').strip()
        model = request.args.get('model').strip()
        textPrompt_openai = request.args.get('textPrompt_openai').strip()
        openaimodel = request.args.get('openaimodel').strip()
        email = request.args.get('email').strip()

        if model == '':
            return jsonify({'error': 'Please select a model'}), 400
        if len(textPrompt) == 0:
            return jsonify({'error': 'Please provide a non-empty textPrompt'}), 400
        if len(textPrompt_openai) == 0 and len(openaimodel) > 0:
            return jsonify({'error': 'Please provide a non-empty textPrompt_openai'}), 400
        if len(textPrompt_openai) > 0 and openaimodel == '':
            return jsonify({'error': 'Please select an openaimodel'}), 400

        df = scrap_fillurls_file(textPrompt, model, textPrompt_openai, openaimodel)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Email setup
        sender_email = "leads@evergrowadvisors.com"
        receiver_email = email
        smtp_password = os.getenv('GMAIL_APP_PASSWORD')

        if not smtp_password:
            raise Exception("Gmail app password is not set")

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = "CSV File for all the URLs"

        body = "Please find the attached CSV file."
        message.attach(MIMEText(body, "plain"))

        part = MIMEBase("application", "octet-stream")
        part.set_payload(csv_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename=data.csv")

        message.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, smtp_password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        response = make_response(csv_buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response

    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'An error occurred while processing the request'}), 500


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
