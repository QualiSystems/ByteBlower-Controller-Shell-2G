
from os import path
import sys
import logging
import time

from cloudshell.traffic.tg_helper import get_reservation_resources, set_family_attribute
from shellfoundry.releasetools.test_helper import (get_namespace_from_cloudshell_config,
                                                   create_session_from_deployment, create_command_context_2g)

from src.driver import ByteBlowerControllerShell2GDriver

namespace = get_namespace_from_cloudshell_config()

server = '10.113.137.22'
meeting_point = '192.168.0.3'
client_install_path = 'C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe'

ports = ['bb2/Module1/Port1', 'bb2/Module2/Port45', 'bb2/Module3/PC1X2G', 'bb2/Module3/PC2X5G', 'bb2/Module3/PC3X2G', 'bb2/Module3/PC4X5G']

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
        # self._load_config('test_config', 'CloudShellPoC')
        self._load_config('Mv2-HW11-Portloading', 'Mv2-HW11-Automation')

    def test_run_traffic(self):
        # self._load_config('test_config', 'CloudShellPoC')
        self._load_config('Mv2-HW11-Portloading', 'Mv2-HW11-Automation')

        self.driver.start_traffic(self.context, 'False')
        status = self.driver.get_test_status(self.context)
        while status.lower() != 'finished':
            time.sleep(1)
            print(self.driver.get_rt_statistics(self.context))
            status = self.driver.get_test_status(self.context)
        self.driver.stop_traffic(self.context)
        output = self.driver.get_statistics(self.context, 'csv')
        print('output folder = {}'.format(output))

    def _load_config(self, config_name, scenario):
        config_file = path.join(path.dirname(__file__), '{}.bbp'.format(config_name))
        phy_reservation_ports = get_reservation_resources(self.session, self.context.reservation.reservation_id,
                                                          'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort')
        set_family_attribute(self.session, phy_reservation_ports[0], 'Logical Name', 'WAN_PORT')
        set_family_attribute(self.session, phy_reservation_ports[1], 'Logical Name', 'PORT_45')
        ep_reservation_ports = get_reservation_resources(self.session, self.context.reservation.reservation_id,
                                                         'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint')
        set_family_attribute(self.session, ep_reservation_ports[0], 'Logical Name', 'EP01_2G')
        set_family_attribute(self.session, ep_reservation_ports[1], 'Logical Name', 'EP02_5G')
        set_family_attribute(self.session, ep_reservation_ports[2], 'Logical Name', 'EP03_2G')
        set_family_attribute(self.session, ep_reservation_ports[3], 'Logical Name', 'EP04_5G')
        self.driver.load_config(self.context, config_file, scenario)
