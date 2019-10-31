
from __future__ import print_function # Only Python 2.x
import subprocess
import threading
import time
import rpyc

ep_ip = '10.113.137.13'

mp_ip = '192.168.0.3'
ep_clt = 'C:/Users/PC1xx2G/Desktop/ByteBlowerWirelessEndpoint/$PLUGINSDIR/BBWEP/byteblower-wireless-endpoint.exe'
ep_cmd = [ep_clt, mp_ip]


class EpThread(threading.Thread):

    def __init__(self, logger, interval=0.1):
        threading.Thread.__init__(self)
        self.logger = logger
        self.interval = interval
        self.finished = threading.Event()
        self.setDaemon(True)
        self.logger.info("EP thread Initiated")

    def stop(self):
        self.popen.stdout.close()
        self.logger.debug("EP thread stopped")
        self.finished.set()
        self.join()

    def run(self):
        c = rpyc.classic.connect(ep_ip)
        self.popen = c.modules.subprocess.Popen(ep_cmd, stdout=c.modules.subprocess.PIPE, universal_newlines=True)
        while not self.finished.isSet():
            self.finished.wait(self.interval)
            self.logger.info(self.popen.stdout.readline().strip())
