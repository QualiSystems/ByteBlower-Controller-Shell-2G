
from __future__ import print_function # Only Python 2.x
import threading
import subprocess
import re
import rpyc
import io
import os


class ServerThread(threading.Thread):

    def __init__(self, logger, clt, project, scenario, output, interval=1):
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
        self.failed = None
        self.popen = None
        self.traffic_running = False

    def stop(self):
        self.logger.debug('Stopping Server thread')
        self.finished.set()
        self.join()
        self.popen.terminate()
        self.traffic_running = False

    def run(self):
        self.logger.info('Starting Server thread')
        server_cmd = [self.clt, '-project', self.project, '-scenario', self.scenario, '-output', self.output]
        self.logger.info('Run Server command - {}'.format(server_cmd))
        self.traffic_running = False
        filename, suffix = os.path.splitext(self.logger.handlers[0].baseFilename)
        clt_logger = filename + '-clt' + suffix
        with io.open(clt_logger, 'wb') as writer, io.open(clt_logger, 'rb', 1) as reader:
            self.popen = subprocess.Popen(server_cmd, stdout=writer, stderr=writer, universal_newlines=True)
            while self.popen.poll() is None:
                output = reader.read()
                self._parse_output(output)
                self.finished.wait(self.interval)
            output = reader.read()
            self._parse_output(output)
        self.popen.wait()

    def _parse_output(self, output):
        if 'StartTraffic' in output:
            self.traffic_running = True
        elif 'StopTraffic' in output:
            self.traffic_running = False
        elif 'Action failed' in output:
            self.failed = [l for l in output.split('\n') if 'Action failed' in l][0]
        elif '!MESSAGE Failed' in output:
            self.failed = [l for l in output.split('\n') if '!MESSAGE Failed' in l][0]
        if self.failed:
            raise Exception(self.failed)


class EpThread(threading.Thread):

    def __init__(self, logger, ip, meetingpoint, ep_clt, name, interval=0.25):
        threading.Thread.__init__(self)
        self.logger = logger
        self.ip = ip
        self.meetingpoint = meetingpoint
        self.ep_clt = ep_clt
        self.name = name
        self.interval = interval
        self.finished = threading.Event()
        self.setDaemon(True)
        self.counters = []
        self.popen = None
        self.logger.info('EP {} thread Initiated'.format(self.name))

    def stop(self):
        self.logger.info('Stopping {} thread'.format(self.name))
        self.finished.set()
        self.join()
        self.popen.terminate()

    def run(self):
        self.logger.info('Starting {} thread'.format(self.name))
        c = rpyc.classic.connect(self.ip)
        ep_cmd = [self.ep_clt, self.meetingpoint]
        self.logger.debug('EP {} command: {}'.format(self.name, ep_cmd))
        self.popen = c.modules.subprocess.Popen(ep_cmd, stdout=c.modules.subprocess.PIPE, stderr=c.modules.subprocess.PIPE)
        while not self.finished.isSet():
            self.finished.wait(self.interval)
            raw_status = self.popen.stdout.readline().strip()
            self.logger.debug('EP {} raw: {}'.format(self.name, raw_status))
            status = raw_status if raw_status.startswith('Status:') else None
            if status:
                new_status = [status.split()[1]] + re.findall('\d+\.\d+', status)
                self.counters.append(new_status)
                self.logger.info('EP {} status: {}'.format(self.name, new_status))
