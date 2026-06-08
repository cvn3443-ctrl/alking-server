from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "ok", "message": "Server is running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
