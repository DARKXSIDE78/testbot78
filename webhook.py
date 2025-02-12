from flask import Flask

app = Flask(__name__)

@app.route("/health")
def health_check():
    return "OK", 200

def start_webhook():
    app.run(host="0.0.0.0", port=8000, threaded=True)

if __name__ == "__main__":
    start_webhook()
