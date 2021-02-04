
import io
import os
import psutil
import re
import subprocess
import threading

import rpyc


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
        self.logger.info('Server thread Initiated')
        self.failed = None
        self.popen = None
        self.traffic_running = False

    def stop(self):
        self.logger.debug('Stopping Server thread')
        self.finished.set()
        if self.popen:
            self.popen.terminate()
        self.logger.debug('Past Server Thread Terminate Call')
        self.traffic_running = False

        # in case clt exists, kill the pid just to be sure
        if self.popen:
            self._kill_clt_by_pid(self.popen.pid)

    def run(self):
        self.logger.info('Starting Server thread')
        server_cmd = [self.clt, '-project', self.project, '-scenario', self.scenario, '-output', self.output]
        self.logger.info(f'Run Server command - {server_cmd}')
        self.traffic_running = False
        self.failed = None
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

    def _kill_clt_by_pid(self, pid):
        name = 'ByteBlower-CLT'
        processes = []
        for process in psutil.process_iter():
            name_, exe, cmdline = '', '', []
            try:
                name_ = process.name()
                process.cmdline()
                process.exe()
            except (psutil.AccessDenied, psutil.ZombieProcess, OSError, SystemError):
                pass
            except psutil.NoSuchProcess:
                continue
            if name in name_ and process.pid == pid:
                processes.append(process)
        if processes:
            processes[0].kill()


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
        self.rpyc = None
        self.popen = None
        self.logger.info(f'EP {self.name} thread Initiated')

    def stop(self):
        self.logger.info(f'Stopping {self.name} thread')
        self.finished.set()
        # self.join()
        if self.popen:
            self.popen.terminate()

    def run(self):
        self.logger.info(f'Starting {self.name} thread')
        self.rpyc = rpyc.classic.connect(self.ip)
        ep_cmd = [self.ep_clt, self.meetingpoint]
        self.logger.debug(f'EP {self.name} command: {ep_cmd}')
        self.popen = self.rpyc.modules.subprocess.Popen(ep_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while not self.finished.isSet():
            self.finished.wait(self.interval)
            raw_status = self.popen.stdout.readline().strip()
            self.logger.debug(f'EP {self.name} raw: {raw_status}')
            status = raw_status if raw_status.startswith('Status:') else None
            if status:
                new_status = [status.split()[1]] + re.findall('\d+\.\d+', status)
                self.counters.append(new_status)
                self.logger.info(f'EP {self.name} status: {new_status}')


class EpCmd(object):

    def __init__(self, logger, ip, name):
        self.logger = logger
        self.ip = ip
        self.name = name
        self.conn = None
        self._get_connection()

    def _get_connection(self):
        self.conn = rpyc.classic.connect(self.ip)
        self.logger.info(f'EP {self.name} Command Connection Initiated')

    def run_command(self, ep_cmd):
        """
        send command to endpoint as list of of strings ex. ['ping', 'google.com']
        :param ep_cmd:
        :return:
        """
        self.logger.debug(f'EP {self.name} command: {ep_cmd}')
        outp = self.conn.modules.subprocess.check_output(ep_cmd)
        self.logger.debug(f'EP {self.name} command: {ep_cmd}, returned with output: {outp}')
        return outp
