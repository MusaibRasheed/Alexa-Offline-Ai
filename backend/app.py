from flask import Flask, render_template, request, jsonify
from project import Alexa
import os

print("Starting Flask app...")
template_dir = os.path.join(os.path.dirname(__file__), '..', 'Front-end', 'Tempelates')
static_dir = os.path.join(os.path.dirname(__file__), '..', 'Front-end', 'Static')
print(f"Template dir: {template_dir}")
print(f"Static dir: {static_dir}")

app = Flask(__name__,
            template_folder=template_dir,
            static_folder=static_dir)

print("Creating Alexa instance...")
alexa = Alexa()
alexa.silent_mode = True  # Disable TTS for web interface

print("Alexa created, setting up routes...")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/command', methods=['POST'])
def command():
    data = request.get_json()
    cmd = data.get('command', '')
    response = alexa.handle_request(cmd)
    return jsonify({'response': response})

print("Routes set up, starting server...")

if __name__ == '__main__':
    app.run(debug=True)