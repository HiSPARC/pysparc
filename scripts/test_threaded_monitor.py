from __future__ import division

import threading
import time

from flask import Flask, request

import requests


app = Flask(__name__)


@app.route('/', methods=["POST"])
def hello_world():
    assert request.form['foo'] == 'bar'
    time.sleep(.2)
    return 'Hello, World!'


def run_flask_server():
    app.run()


def mean(values):
    return sum(values) / len(values)


def test_response_times():
    response_times = []
    for _ in range(10):
        t0 = time.time()
        fire_and_forget_post("http://localhost:5000", data={'foo': 'bar'})
        t1 = time.time()
        response_times.append(t1 - t0)

    print "Response times (mean, max): %.2f, %.2f" % (
        mean(response_times), max(response_times))


def fire_and_forget_post(url, data):
    thread = threading.Thread(target=requests.post, args=(url,), kwargs={'data': data})
    thread.start()


if __name__ == '__main__':
    thread = threading.Thread(target=run_flask_server)
    thread.daemon = True
    thread.start()

    # give server some time to start up
    time.sleep(.2)

    print "Number of threads:", len(threading.enumerate())

    test_response_times()

    print "Number of threads:", len(threading.enumerate())
    time.sleep(1)
    print "Number of threads:", len(threading.enumerate())
