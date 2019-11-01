
from os import path
import sys
import logging

from cloudshell.traffic.tg_helper import get_reservation_resources, set_family_attribute
from shellfoundry.releasetools.test_helper import (get_namespace_from_cloudshell_config,
                                                   create_session_from_deployment, create_command_context_2g)

from src.driver import ByteBlowerControllerShell2GDriver

namespace = get_namespace_from_cloudshell_config()

server = '10.113.137.22'
meeting_point = '192.168.0.3'
client_install_path = 'C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe'

ports = ['bb1/Module1/Port1', 'bb1/Module2/Port45', 'bb1/Module3/PC1X2G']

attributes = {namespace + '.Address': server,
              namespace + '.Meeting Point': meeting_point,
              namespace + '.Client Install Path': client_install_path}


class TestByteBlowerControllerDriver(object):

    def setup(self):
        self.session = create_session_from_deployment()
        self.context = create_command_context_2g(self.session, ports, 'ByteBlower Controller Shell 2G', attributes)
        self.driver = ByteBlowerControllerShell2GDriver()
        self.driver.initialize(self.context)
        self.driver.logger.addHandler(logging.StreamHandler(sys.stdout))
        self.driver.logger.info('logfile = {}'.format(self.driver.logger.handlers[0].baseFilename))

    def teardown(self):
        self.driver.cleanup()
        self.session.EndReservation(self.context.reservation.reservation_id)

    def test_init(self):
        pass

    def test_load_config(self):
        self._load_config('test_config', 'CloudShellPoC')

    def test_run_traffic(self):
        self._load_config('test_config', 'CloudShellPoC')
        self.driver.start_traffic(self.context, 'False')
        rt_stats = self.driver.get_rt_statistics(self.context)
        while rt_stats[0][0] != 'Finished':
            rt_stats = self.driver.get_rt_statistics(self.context)
        self.driver.stop_traffic(self.context)

    def _load_config(self, config_name, scenario):
        config_file = path.join(path.dirname(__file__), '{}.bbp'.format(config_name))
        reservation_ports = get_reservation_resources(self.session, self.context.reservation.reservation_id,
                                                      'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort',
                                                      'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint')
        set_family_attribute(self.session, reservation_ports[0], 'Logical Name', 'WAN_PORT')
        set_family_attribute(self.session, reservation_ports[1], 'Logical Name', 'PORT_45')
        set_family_attribute(self.session, reservation_ports[2], 'Logical Name', 'PC1x2G')
        self.driver.load_config(self.context, config_file, scenario)
