"""Communicate with the HiSPARC infrastructure monitoring solution.

Contents
--------

:class:`Monitor`
    Communicate with the HiSPARC infrastructure monitoring solution.

"""

import logging
import subprocess
import re
import threading
import json

import requests
from requests.exceptions import ConnectionError, Timeout


logger = logging.getLogger(__name__)


NRDP_TOKEN = 'nrdp4hisp'  # not a secret: used inside VPN
NRDP_URL = 'http://194.171.82.1/nrdp'

OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
STATUS_MSG = {OK: 'OK', WARNING: 'WARNING', CRITICAL: 'CRITICAL',
              UNKNOWN: 'UNKNOWN'}

CPU_THRESHOLD = 2.0


class Monitor(object):

    """Communicate with the HiSPARC infrastructure monitoring solution."""

    def __init__(self, host):
        """Instantiate the Monitor class.

        :param host: the name of the local host.

        """
        self.host = host

    def send_uptime(self):
        """Send the system uptime to the monitor."""

        uptime = self._get_uptime()
        self._send_status_for_service('Uptime Pi', OK, uptime)

    def _get_uptime(self):
        """Return the system uptime."""

        output = subprocess.check_output('uptime')
        uptime = re.search('up (.*),[ 0-9]+ user', output).group(1)
        return uptime

    def send_trigger_rate(self, trigger_rate):
        """Send the trigger rate to the monitor."""

        if trigger_rate:
            status = OK
            msg = "%.1f Hz" % trigger_rate
        else:
            status = CRITICAL
            msg = "No recorded events."

        self._send_status_for_service('TriggerRate', status, msg)

    def send_cpu_load(self):
        """Send the system cpu load to the monitor."""

        cpu_loads = self._get_cpu_load()

        # the loads are 1, 5 and 15 minute averages
        avg1, avg5, avg15 = cpu_loads

        # warning if only 5 min average high, critical if 15 min average
        # *also* high.  If 1 min average low, than all is OK again.
        if avg1 < CPU_THRESHOLD:
            status = OK
        elif avg5 > CPU_THRESHOLD:
            if avg15 > CPU_THRESHOLD:
                status = CRITICAL
            else:
                status = WARNING
        else:
            status = OK

        msg = '%.2f (1 min), %.2f (5 min), %.2f (15 min)' % \
            (avg1, avg5, avg15)
        self._send_status_for_service('CPU Load Pi', status, msg)

    def _get_cpu_load(self):
        """Return the system CPU load."""

        output = subprocess.check_output('uptime')
        cpu_loads = re.search(
            'load average: ([0-9.]+), ([0-9.]+), ([0-9.]+)',
            output).groups()
        return [float(u) for u in cpu_loads]

    def _send_status_for_service(self, service, status, msg=''):
        """Send status to monitor server.

        Spin up a thread to send monitor data.

        :param service: name of the service
        :param status: numerical status code
        :param msg: optional informational message

        The status code can be 0 (OK), 1 (WARNING), 2 (CRITICAL) or 3
        (UNKNOWN).

        """
        thread = threading.Thread(target=self._do_send_status_for_service,
                                  args=(self.host, service, status, msg))
        thread.start()

    @staticmethod
    def _do_send_status_for_service(host, service, status, msg=''):
        """Send status to monitor server.

        :param host: name of the host
        :param service: name of the service
        :param status: numerical status code
        :param msg: optional informational message

        The status code can be 0 (OK), 1 (WARNING), 2 (CRITICAL) or 3
        (UNKNOWN).

        """

        nrdp_json = {
            "checkresults": [
                {
                    "checkresult": {
                        "type": "service",
                        "checktype": "passive"
                    },
                    "hostname": host,
                    "servicename": service,
                    "state": status,
                    "output": msg
                }
            ]
        }

        params = {
           'token': NRDP_TOKEN,
           'cmd': 'submitcheck',
           'JSONDATA': json.dumps(nrdp_json),
        }

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            requests.post(NRDP_URL, params=params, headers=headers, timeout=1)
        except (ConnectionError, Timeout) as exc:
            logger.warning("Unable to upload status for service %s (%s)",
                           service, exc)
        else:
            logger.info("Send status for service %s (%s)", service,
                        STATUS_MSG[status])
