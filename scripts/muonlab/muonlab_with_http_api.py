import time
from multiprocessing import Process, Pipe, Event
import logging
import signal

import tables
from flask import Flask, jsonify, redirect, request

app = Flask(__name__)

from pysparc.muonlab.muonlab_ii import MuonlabII, FakeMuonlabII
from pysparc.muonlab.ftdi_chip import DeviceNotFoundError


class LifeTime(tables.IsDescription):
    timestamp = tables.Time32Col()
    lifetime = tables.Float32Col()


def message(cmd, **kwargs):
    return dict(cmd=cmd, kwargs=kwargs)


@app.route('/')
def landing_page():
    return redirect('/data')


@app.route('/data')
def get_data():
    start = request.args.get('start', None)
    if start is not None:
        start = int(start)
    stop = request.args.get('stop', None)
    if stop is not None:
        stop = int(stop)
    app.muonlab.send(message('get', start=start, stop=stop))
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

    data = tables.openFile('muonlab.h5', 'a')
    if '/lifetime' not in data:
        table = data.createTable('/', 'lifetime', LifeTime)
    else:
        table = data.getNode('/lifetime')
    measurement = table.row

    try:
        muonlab = MuonlabII()
    except DeviceNotFoundError:
        logger.warning(
            "Hardware not detected, falling back to FAKE hardware")
        muonlab = FakeMuonlabII()

    muonlab.set_pmt1_voltage(900)
    muonlab.set_pmt1_threshold(100)
    muonlab.select_lifetime_measurement()

    while not must_shutdown.is_set():
        data = muonlab.read_lifetime_data()
        if data:
            measurement['timestamp'] = time.time()
            for value in data:
                measurement['lifetime'] = value
                measurement.append()
            table.flush()
        if conn.poll():
            msg = conn.recv()
            if msg['cmd'] == 'get':
                start = msg['kwargs']['start']
                stop = msg['kwargs']['stop']
                conn.send(table.col('lifetime')[start:stop].tolist())
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
