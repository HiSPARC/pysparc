import time
from multiprocessing import Process, Pipe, Event
import logging
import signal

from flask import Flask
app = Flask(__name__)

#from pysparc.muonlab.muonlab_ii import MuonlabII
from pysparc.muonlab.muonlab_ii import FakeMuonlabII as MuonlabII


@app.route('/')
def hello_world():
    app.muonlab.send("GET")
    data = app.muonlab.recv()
    raise RuntimeError("WOH")
    return repr(data)


@app.route('/stop')
def stop():
    app.must_shutdown.set()
    print "RECV SHUTDOWN"
    return 'Shutting down.'


def muonlab(conn, must_shutdown):
    # Ignore interrupt signal, let main process catch ctrl-c
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    t0 = time.time()

    muonlab = MuonlabII()
    muonlab.set_pmt1_voltage(900)
    muonlab.set_pmt1_threshold(100)
    muonlab.select_lifetime_measurement()

    all_data = []

    while not must_shutdown.is_set():
        if time.time() - t0 > 3:
            raise RuntimeError("Timing exceeded!")
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
    logging.basicConfig(level=logging.INFO)

    conn1, conn2 = Pipe()
    must_shutdown = Event()

    app.muonlab = conn1
    app.must_shutdown = must_shutdown

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
            print "CATCHED IN MAIN THREAD"
            break

    print "SHUTTING DOWN"
    p.terminate()
    must_shutdown.set()
    p2.join()
