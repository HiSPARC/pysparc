import time
from multiprocessing import Process, Pipe, Event
import logging

from flask import Flask
app = Flask(__name__)

from pysparc.muonlab.muonlab_ii import MuonlabII


@app.route('/')
def hello_world():
    app.muonlab.send("GET")
    data = app.muonlab.recv()
    return repr(data)


@app.route('/stop')
def stop():
    app.must_shutdown.set()
    print "RECV SHUTDOWN"
    return 'Shutting down.'


def muonlab(conn, must_shutdown):
    muonlab = MuonlabII()
    muonlab.set_pmt1_voltage(900)
    muonlab.set_pmt1_threshold(100)
    muonlab.select_lifetime_measurement()

    all_data = []

    while not must_shutdown.is_set():
        data = muonlab.read_lifetime_data()
        if data:
            all_data.extend(data)
            print len(all_data)
        if conn.poll():
            msg = conn.recv()
            if msg == 'GET':
                conn.send(all_data)
    print "MUONLAB shutting down."


if __name__ == '__main__':
    logging.basicConfig()

    conn1, conn2 = Pipe()
    must_shutdown = Event()

    app.muonlab = conn1
    app.must_shutdown = must_shutdown

    p = Process(target=app.run)
    p2 = Process(target=muonlab, args=(conn2, must_shutdown))

    p.start()
    p2.start()

    p2.join()
    must_shutdown.wait()
    p.terminate()
