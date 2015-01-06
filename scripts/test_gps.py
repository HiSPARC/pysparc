import curses
import logging

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS


class Main(object):

    def __init__(self):
        try:
            self.device = HiSPARCIII()
        except DeviceNotFoundError:
            self.device = HiSPARCII()
        self.gps = TrimbleGPS()

    def close(self):
        logging.info("Closing down")
        self.device.close()

    def run(self, stdscr):
        curses.curs_set(0)
        curses.halfdelay(10)

        while True:
            stdscr.erase()

            stdscr.refresh()
            c = stdscr.getch()
            if c == ord('q'):
                break


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = Main()
    curses.wrapper(app.run)
    app.close()
