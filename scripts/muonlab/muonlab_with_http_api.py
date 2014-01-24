import time
from multiprocessing import Process, Pipe, Event
import logging
import signal

from flask import Flask, jsonify, redirect

app = Flask(__name__)

from pysparc.muonlab.muonlab_ii import MuonlabII, FakeMuonlabII
from pysparc.muonlab.ftdi_chip import DeviceNotFoundError


def message(cmd, **kwargs):
    return dict(cmd=cmd, kwargs=kwargs)


@app.route('/')
def landing_page():
    return redirect('/data')


@app.route('/data/', defaults={'start': 0})
@app.route('/data/<int:start>')
def get_data(start):
    app.muonlab.send(message('get', start=start))
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

    try:
        muonlab = MuonlabII()
    except DeviceNotFoundError:
        logger.warning(
            "Hardware not detected, falling back to FAKE hardware")
        muonlab = FakeMuonlabII()

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
            if msg['cmd'] == 'get':
                start = msg['kwargs']['start']
                conn.send(all_data[start:])
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
