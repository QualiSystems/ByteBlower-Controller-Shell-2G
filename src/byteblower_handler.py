
from __future__ import print_function  # Only Python 2.x

import os
import subprocess

from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.traffic.tg_helper import (get_reservation_resources, get_address, is_blocking, attach_stats_csv,
                                          get_family_attribute)

from byteblower.byteblowerll import byteblower

from src.ep_thread import EpThread

class ByteBlowerHandler():

    namespace = 'ByteBlower Controller Shell 2G'

    def initialize(self, context, logger):

        self.logger = logger

        address = context.resource.address
        server_address = context.resource.attributes['ByteBlower Controller Shell 2G.Controller Address']
        self.client_install_path = context.resource.attributes['ByteBlower Controller Shell 2G.Client Install Path']
        meetingpoint_address = server_address

        bb = byteblower.ByteBlower.InstanceGet()
        self.server = bb.ServerAdd(server_address)
        self.meetingpoint = bb.MeetingPointAdd(meetingpoint_address)

    def tearDown(self):
        pass

    def load_config(self, context, bbl_config_file_name):

        self.project = bbl_config_file_name.replace('\\', '/')

        return

        reservation_id = context.reservation.reservation_id
        my_api = CloudShellSessionContext(context).get_api()

        # todo: geat ports from bbl.
        config_ports = ['WAN_PORT', 'PORT_45', 'PC1x2G']

        reservation_ports = {}
        for port in get_reservation_resources(my_api, reservation_id,
                                              'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort',
                                              'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint'):
            reservation_ports[get_family_attribute(my_api, port, 'Logical Name').Value.strip()] = port

        for port in config_ports:
            name = port.obj_name()
            if name in reservation_ports:
                address = get_address(reservation_ports[name])
                self.logger.debug('Logical Port {} will be reserved on Physical location {}'.format(name, address))
                port.reserve(address, wait_for_up=False)
            else:
                self.logger.error('Configuration port "{}" not found in reservation ports {}'.
                                  format(port, reservation_ports.keys()))
                raise Exception('Configuration port "{}" not found in reservation ports {}'.
                                format(port, reservation_ports.keys()))

        self.logger.info("Port Reservation Completed")

    def start_traffic(self, blocking):
        scenario = 'CloudShellPoC'

        log_file_name = self.logger.handlers[0].baseFilename
        output = (os.path.splitext(log_file_name)[0] + '--output').replace('\\', '/')
        self.bb_cmd = [self.client_install_path, '-project', self.project, '-scenario', scenario, '-output', output]

        self.ep_thread = EpThread(self.logger)
        self.ep_thread.start()

        shell = not blocking
        self.popen = subprocess.Popen(self.bb_cmd, stdout=subprocess.PIPE, shell=shell, universal_newlines=True)
        if blocking:
            self.stop_traffic()

    def stop_traffic(self):
        for stdout_line in iter(self.popen.stdout.readline, ''):
            print(stdout_line)
        self.popen.stdout.close()
        return_code = self.popen.wait()
        if return_code:
            raise subprocess.CalledProcessError(return_code, self.bb_cmd)
        self.ep_thread.stop()

    def get_rt_statistics(self):
        pass

    def get_statistics(self, context, output_type):
        pass
