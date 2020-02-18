
from os import path
import time
import pytest


from cloudshell.api.cloudshell_api import AttributeNameValue, InputNameValue
from cloudshell.traffic.tg_helper import set_family_attribute
from cloudshell.traffic.tg import BYTEBLOWER_CONTROLLER_MODEL
from cloudshell.traffic.common import add_resources_to_reservation, get_reservation_id, get_resources_from_reservation
from shellfoundry.releasetools.test_helper import (create_session_from_deployment, create_init_command_context,
                                                   create_service_command_context, end_reservation)

from src.byteblower_driver import ByteBlowerControllerShell2GDriver

ports = ['BB/Module1/Port1', 'BB/Module2/Port45', 'BB/Module3/PC1X2G', 'BB/Module3/PC2X5G', 'BB/Module3/PC3X2G', 'BB/Module3/PC4X5G']
ports = ['BB/Module1/Port1', 'BB/Module2/Port45', 'BB/Module3/PC1X2G']


@pytest.fixture()
def model():
    yield BYTEBLOWER_CONTROLLER_MODEL


@pytest.fixture()
def alias():
    yield 'ByteBlower Controller'


@pytest.fixture()
def server():
    yield ['10.113.137.22', '192.168.0.3']


@pytest.fixture()
def client_install_path():
    yield 'C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe'


@pytest.fixture()
def session():
    yield create_session_from_deployment()


@pytest.fixture()
def driver(session, model, server, client_install_path):
    address, meeting_point = server
    attributes = {model + '.Address': address,
                  model + '.Meeting Point': meeting_point,
                  model + '.Client Install Path': client_install_path}
    init_context = create_init_command_context(session, 'CS_TrafficGeneratorController', model, 'na', attributes,
                                               'Service')
    driver = ByteBlowerControllerShell2GDriver()
    driver.initialize(init_context)
    print(driver.logger.handlers[0].baseFilename)
    yield driver
    driver.cleanup()


@pytest.fixture()
def context(session, model, alias, server, client_install_path):
    address, meeting_point = server
    attributes = [AttributeNameValue(model + '.Address', address),
                  AttributeNameValue(model + '.Meeting Point', meeting_point),
                  AttributeNameValue(model + '.Client Install Path', client_install_path)]
    context = create_service_command_context(session, model, alias, attributes)
    add_resources_to_reservation(context, *ports)
    reservation_ports = get_resources_from_reservation(context,
                                                       'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort')
    set_family_attribute(context, reservation_ports[0], 'Logical Name', 'WAN PORT')
    set_family_attribute(context, reservation_ports[1], 'Logical Name', 'PORT_A')
    reservation_eps = get_resources_from_reservation(context,
                                                       'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint')
    set_family_attribute(context, reservation_eps[0], 'Logical Name', 'EP01_2G')
    yield context
    end_reservation(session, get_reservation_id(context))


class TestByteBlowerControllerDriver(object):

    def test_load_config(self, driver, context):
        config_file = path.join(path.dirname(__file__), 'test_config.bbp')
        driver.load_config(context, config_file, 'CloudShellPoC')
        # self._load_config('Mv2-HW11-Portloading', 'Mv2-HW11-Automation')

    def test_run_traffic(self, driver, context):
        config_file = path.join(path.dirname(__file__), 'test_config.bbp')
        driver.load_config(context, config_file, 'CloudShellPoC')

        driver.start_traffic(context, 'False')
        status = driver.get_test_status(context)
        while status.lower() != 'finished':
            time.sleep(1)
            print(driver.get_rt_statistics(context))
            status = driver.get_test_status(context)
        driver.stop_traffic(context)
        output = driver.get_statistics(context, None, None)
        print('output folder = {}'.format(output))


class TestByteBlowerControllerShell(object):

    def test_load_config(self, session, context, alias):
        config_file = path.join(path.dirname(__file__), 'test_config.bbp')
        session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                               'load_config',
                               [InputNameValue('config_file_location', config_file),
                                InputNameValue('scenario', 'CloudShellPoC')])

    def test_run_traffic(self, session, context, alias):
        config_file = path.join(path.dirname(__file__), 'test_config.bbp')
        session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                               'load_config',
                               [InputNameValue('config_file_location', config_file),
                                InputNameValue('scenario', 'CloudShellPoC')])

        session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                               'start_traffic',
                               [InputNameValue('blocking', 'False')])
        status = session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                                        'get_test_status')
        while status.Output.lower() != 'finished':
            time.sleep(1)
            rt_stats = session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                                              'get_rt_statistics')
            print(rt_stats.Output)
            status = session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                                            'get_test_status')
        session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                               'stop_traffic')
        stats = session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                                       'get_statistics',
                                       [InputNameValue('view_name', None),
                                        InputNameValue('output_type', None)])
        print(stats.Output)
