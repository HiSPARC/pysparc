import threading

from flask import Flask
app = Flask(__name__)

import requests


@app.route('/')
def hello_world():
    return 'Hello, World!'


def run_flask_server():
    app.run()


if __name__ == '__main__':
    thread = threading.Thread(target=run_flask_server)
    thread.daemon = True
    thread.start()

    response = requests.get("http://localhost:5000")
    print response.text
