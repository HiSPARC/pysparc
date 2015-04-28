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
        # default terminal colors
        curses.use_default_colors()
        # no blinking cursor
        # curses.curs_set(0)
        # getch() pauses for one second
        curses.halfdelay(10)

        while True:
            stdscr.erase()

            stdscr.addstr("GPS messages since last refresh:\n")

            stdscr.refresh()
            c = stdscr.getch()
            if c == ord('q'):
                break


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)

    app = Main()
    curses.wrapper(app.run)
    app.close()
