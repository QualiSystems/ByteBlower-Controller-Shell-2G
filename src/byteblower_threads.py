
from __future__ import print_function # Only Python 2.x
import threading
import subprocess
import re
import rpyc


ep_clt = 'C:/Users/PC1xx2G/Desktop/ByteBlowerWirelessEndpoint/$PLUGINSDIR/BBWEP/byteblower-wireless-endpoint.exe'


class ServerThread(threading.Thread):

    def __init__(self, logger, clt, project, scenario, output, interval=0.1):
        threading.Thread.__init__(self)
        self.logger = logger
        self.clt = clt
        self.project = project
        self.scenario = scenario
        self.output = output
        self.interval = interval
        self.finished = threading.Event()
        self.setDaemon(True)
        self.logger.info("Server thread Initiated")

    def stop(self):
        self.logger.debug("Server thread Stopped")
        self.finished.set()
        self.join()
        self.popen.terminate()

    def run(self):
        self.logger.info("Server thread Started")
        server_cmd = [self.clt, '-project', self.project, '-scenario', self.scenario, '-output', self.output]
        self.logger.info('Run Server command - {}'.format(server_cmd))
        self.popen = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, universal_newlines=True)
        while not self.finished.isSet():
            server_stdout = self.popen.stdout.readline()
            self.logger.debug(server_stdout)
            if server_stdout.strip() == 'FINISHED':
                break
            self.finished.wait(self.interval)


class EpThread(threading.Thread):

    def __init__(self, logger, ip, meetingpoint, name, interval=1):
        threading.Thread.__init__(self)
        self.logger = logger
        self.ip = ip
        self.meetingpoint = meetingpoint
        self.name = name
        self.interval = interval
        self.finished = threading.Event()
        self.setDaemon(True)
        self.counters = []
        self.logger.info('EP {} thread Initiated'.format(self.name))

    def stop(self):
        self.logger.info('EP {} thread Stopped'.format(self.name))
        self.finished.set()
        self.join()
        self.popen.terminate()

    def run(self):
        self.logger.info('EP {} thread - Started'.format(self.name))
        c = rpyc.classic.connect(self.ip)
        ep_cmd = [ep_clt, self.meetingpoint]
        self.logger.debug('EP {} command: {}'.format(self.name, ep_cmd))
        self.popen = c.modules.subprocess.Popen(ep_cmd, stdout=c.modules.subprocess.PIPE, universal_newlines=True)
        while not self.finished.isSet():
            self.finished.wait(self.interval)
            raw_status = self.popen.stdout.readline().strip()
            self.logger.debug('EP {} raw: {}'.format(self.name, raw_status))
            status = raw_status if raw_status.startswith('Status:') else None
            if status:
                new_status = [status.split()[1]] + re.findall('\d+\.\d+', status)
                self.counters.append(new_status)
                self.logger.info('EP {} status: {}'.format(self.name, new_status))
