
from __future__ import print_function  # Only Python 2.x

import os
import time

from cloudshell.traffic.common import TrafficHandler, get_resources_from_reservation
from cloudshell.traffic.tg import BYTEBLOWER_CHASSIS_MODEL
from cloudshell.traffic.tg_helper import (get_address, is_blocking, get_family_attribute)

from byteblower.byteblowerll import byteblower
from byteblower_threads import ServerThread, EpThread
from byteblower_data_model import ByteBlower_Controller_Shell_2G

BYTEBLOWER_ENDPOINT_MODEL = BYTEBLOWER_CHASSIS_MODEL + '.ByteBlowerEndPoint'


class ByteBlowerHandler(TrafficHandler):

    def __init__(self):
        super(self.__class__, self).__init__()

        self.server_thread = None
        self.eps_threads = None
        self.reservation_eps = {}

    def initialize(self, context, logger):

        service = ByteBlower_Controller_Shell_2G.create_from_context(context)
        super(self.__class__, self).initialize(service, logger)

    def cleanup(self):
        pass

    def load_config(self, context, bbl_config_file_name, scenario):

        self.project = bbl_config_file_name.replace('\\', '/')
        if not os.path.exists(self.project):
            raise EnvironmentError('Configuration file {} not found'.format(self.project))
        self.scenario = scenario

        bb = byteblower.ByteBlower.InstanceGet()
        server = bb.ServerAdd(self.service.address)
        self.port_45 = server.PortCreate('trunk-1-45')

        self.reservation_eps = {}
        for port in get_resources_from_reservation(context, BYTEBLOWER_ENDPOINT_MODEL):
            self.reservation_eps[get_family_attribute(context, port.Name, 'Logical Name')] = port

        return

        # todo: get ports from bbl.
        config_ports = ['WAN_PORT', 'PORT_45', 'PC1x2G']

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

    def start_traffic(self, context, blocking):

        log_file_name = self.logger.handlers[0].baseFilename
        self.output = (os.path.splitext(log_file_name)[0] + '--output').replace('\\', '/')

        self.eps_threads = {}
        for name, ep in self.reservation_eps.items():
            ep_ip = get_family_attribute(context, ep.Name, 'Address')
            self.eps_threads[name] = EpThread(self.logger, ep_ip, self.service.meeting_point, name)
            self.eps_threads[name].start()
            time.sleep(1)
            if not self.eps_threads[name].popen:
                raise Exception('Failed ro start thread on EP {}, IP {}'.format(name, ep_ip))

        # add delay to ensure clients are registered before starting traffic
        time.sleep(8)
        self.server_thread = ServerThread(self.logger, self.service.client_install_path, self.project, self.scenario,
                                          self.output)
        self.server_thread.start()
        time.sleep(1)

        if is_blocking(blocking):
            # todo: implement wait test.
            pass

    def stop_traffic(self):
        for ep_thread in self.eps_threads.values():
            ep_thread.stop()
        if self.server_thread:
            self.server_thread.stop()

    def get_test_status(self):
        if not self.server_thread:
            return 'Not started'
        if self.server_thread.is_alive():
            return 'Running'
        else:
            if self.server_thread.failed:
                return 'Server Failed: ' + self.server_thread.failed
            else:
                return 'Finished'

    def get_rt_statistics(self, num_samples=1):
        """

        :return: {'name': [[str, int,int]]}
        """
        rt_stats = {}
        for name, thread in self.eps_threads.items():
            rt_stats[name] = thread.counters[-num_samples:]
        return rt_stats

    def get_statistics(self, context, view_name, output_type):
        # todo: attach requested output file to reservation.
        return self.output
