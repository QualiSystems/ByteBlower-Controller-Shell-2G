
from __future__ import print_function  # Only Python 2.x

import os
import time

from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.traffic.tg_helper import (get_reservation_resources, get_address, is_blocking, attach_stats_csv,
                                          get_family_attribute)

from byteblower_threads import ServerThread, EpThread


class ByteBlowerHandler():

    def initialize(self, context, logger):

        self.logger = logger

        self.server_address = context.resource.attributes['ByteBlower Controller Shell 2G.Address']
        self.meeting_point = context.resource.attributes['ByteBlower Controller Shell 2G.Meeting Point']
        self.client_install_path = context.resource.attributes['ByteBlower Controller Shell 2G.Client Install Path']

        self.server_thread = None
        self.ep_thread = None

    def tearDown(self):
        pass

    def load_config(self, context, bbl_config_file_name, scenario):

        self.project = bbl_config_file_name.replace('\\', '/')
        self.scenario = scenario

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

        log_file_name = self.logger.handlers[0].baseFilename
        output = (os.path.splitext(log_file_name)[0] + '--output').replace('\\', '/')

        self.ep_thread = EpThread(self.logger, '10.113.137.13', self.meeting_point)
        self.ep_thread.start()
        self.server_thread = ServerThread(self.logger, self.client_install_path, self.project, self.scenario, output)
        self.server_thread.start()
        time.sleep(1)

        if blocking:
            # todo: implement wait test.
            pass

    def stop_traffic(self):
        if self.ep_thread:
            self.ep_thread.stop()
        if self.server_thread:
            self.server_thread.stop()

    def get_rt_statistics(self, num_samples=1):
        if self.server_thread.is_alive():
            stats = self.ep_thread.counters[-num_samples:]
            return stats
        else:
            return [['Finished', '0.00', '0.00']]

    def get_statistics(self, context, output_type):
        pass
