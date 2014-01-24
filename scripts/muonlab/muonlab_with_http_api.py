import time
from multiprocessing import Process, Pipe, Event
import logging
import signal

from flask import Flask, jsonify

app = Flask(__name__)

#from pysparc.muonlab.muonlab_ii import MuonlabII
from pysparc.muonlab.muonlab_ii import FakeMuonlabII as MuonlabII


@app.route('/')
def hello_world():
    app.muonlab.send("GET")
    data = app.muonlab.recv()
    app.mylogger.info("Sending data")
    return jsonify(lifetime_data=data)


# You could shut down the app remotely by uncommenting the following code.
# Beware!  Browsers may preload content while you type in a url and shut
# down the application in the process.
#
#@app.route('/stop')
#def stop():
#    app.must_shutdown.set()
#    app.mylogger.info("RECV SHUTDOWN")
#    return 'Shutting down.'


def muonlab(conn, must_shutdown):
    # Ignore interrupt signal, let main process catch ctrl-c
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    logger = logging.getLogger('muonlab')

    muonlab = MuonlabII()
    muonlab.set_pmt1_voltage(900)
    muonlab.set_pmt1_threshold(100)
    muonlab.select_lifetime_measurement()

    all_data = []

    while not must_shutdown.is_set():
        data = muonlab.read_lifetime_data()
        if data:
            all_data.extend(data)
        if conn.poll():
            msg = conn.recv()
            if msg == 'GET':
                conn.send(all_data)
    logger.info("MUONLAB shutting down.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    conn1, conn2 = Pipe()
    must_shutdown = Event()

    app.muonlab = conn1
    app.must_shutdown = must_shutdown
    app.mylogger = logging.getLogger('http_api')

    p = Process(target=app.run)
    p2 = Process(target=muonlab, args=(conn2, must_shutdown))

    p2.start()
    p.start()

    while True:
        try:
            time.sleep(2)
            if not p.is_alive() or not p2.is_alive():
                break
        except KeyboardInterrupt:
            logging.info("CATCHED CTRL_C IN MAIN THREAD")
            break

    logging.info("SHUTTING DOWN")
    p.terminate()
    must_shutdown.set()
    p2.join()
