
from os import path
import time
import json

from cloudshell.api.cloudshell_api import AttributeNameValue, InputNameValue
from cloudshell.traffic.tg_helper import get_reservation_resources, set_family_attribute

from shellfoundry.releasetools.test_helper import (get_namespace_from_cloudshell_config,
                                                   create_session_from_deployment, create_command_context_2g)


namespace = get_namespace_from_cloudshell_config()
server = '10.113.137.22'
meeting_point = '192.168.0.3'
client_install_path = 'C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe'

ports = ['bb1/Module1/Port1', 'bb1/Module2/Port45', 'bb1/Module3/PC1X2G']

attributes = [AttributeNameValue(namespace + '.Address', server),
              AttributeNameValue(namespace + '.Meeting Point', meeting_point),
              AttributeNameValue(namespace + '.Client Install Path', client_install_path)]


class TestByteBlowerControllerShell(object):

    def setup(self):
        self.session = create_session_from_deployment()
        self.context = create_command_context_2g(self.session, ports, namespace, attributes)

    def teardown(self):
        reservation_id = self.context.reservation.reservation_id
        self.session.EndReservation(reservation_id)
        while self.session.GetReservationDetails(reservation_id).ReservationDescription.Status != 'Completed':
            time.sleep(1)
        self.session.DeleteReservation(reservation_id)

    def test_load_config(self):
        self._load_config('test_config', 'CloudShellPoC')

    def test_run_traffic(self):
        self._load_config('test_config', 'CloudShellPoC')
        self.session.ExecuteCommand(self.context.reservation.reservation_id, namespace, 'Service',
                                    'start_traffic', [InputNameValue('blocking', 'True')])
        res = self.session.ExecuteCommand(self.context.reservation.reservation_id, namespace, 'Service',
                                          'get_rt_statistics')
        rt_stats = json.loads(res.Output)[0]
        while rt_stats[0] != 'Finished':
            print(rt_stats)
            res = self.session.ExecuteCommand(self.context.reservation.reservation_id, namespace, 'Service',
                                              'get_rt_statistics')
            rt_stats = json.loads(res.Output)[0]
        self.session.ExecuteCommand(self.context.reservation.reservation_id, namespace, 'Service',
                                    'stop_traffic')

    def _load_config(self, config_name, scenario):
        config_file = path.join(path.dirname(__file__), '{}.bbp'.format(config_name))
        reservation_ports = get_reservation_resources(self.session, self.context.reservation.reservation_id,
                                                      'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort',
                                                      'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint')
        set_family_attribute(self.session, reservation_ports[0], 'Logical Name', 'WAN_PORT')
        set_family_attribute(self.session, reservation_ports[1], 'Logical Name', 'PORT_45')
        set_family_attribute(self.session, reservation_ports[2], 'Logical Name', 'PC1x2G')
        self.session.ExecuteCommand(self.context.reservation.reservation_id, namespace, 'Service',
                                    'load_config', [InputNameValue('config_file_location', config_file),
                                                    InputNameValue('scenario', scenario)])
