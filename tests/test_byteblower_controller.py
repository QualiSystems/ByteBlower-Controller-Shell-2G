
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

eps_logical_names = ['EP01_2G', 'EP02_5G', 'EP03_2G', 'EP04_5G']
eps_ssids = ['MV2-HW11-2.4GHz', 'MV2-HW11-2.4GHz', 'MV2-HW11-2.4GHz', 'MV2-HW11-2.4GHz']
ports_logical_names = ['PORT_A', 'PORT_B', 'PORT_C', 'PORT_D']

ports = {'test_config':
             ['BB/Module1/nontrunk-1', 'BB/Module2/trunk-1-45',
              'BB/Module3/PC1X2G'],
         'test_config_4_cpes':
             ['BB/Module1/nontrunk-1',
              'BB/Module2/trunk-1-45', 'BB/Module2/trunk-1-46', 'BB/Module2/trunk-1-47', 'BB/Module2/trunk-1-48',
              'BB/Module3/PC1X2G', 'BB/Module3/PC2X5G', 'BB/Module3/PC3X2G', 'BB/Module3/PC4X5G']}

ep_clt = 'C:/ByteBlowerWirelessEndpoint/$PLUGINSDIR/BBWEP/byteblower-wireless-endpoint.exe'


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
def endpoint_install_path():
    yield 'C:/ByteBlowerWirelessEndpoint/$PLUGINSDIR/BBWEP/byteblower-wireless-endpoint.exe'


# @pytest.fixture(params=[('test_config', 'test_config')],
#                 ids=['test_config'])
@pytest.fixture(params=[('test_config_4_cpes', 'test_config_4_cpes')],
                ids=['test_config_4_cpes'])
def configuration(request):
    config_file = path.join(path.dirname(__file__), request.param[0]) + '.bbp'
    scenario = request.param[1]
    yield [config_file.replace('\\', '/'), scenario]


@pytest.fixture()
def session():
    yield create_session_from_deployment()


@pytest.fixture()
def driver(session, model, server, client_install_path, endpoint_install_path):
    address, meeting_point = server
    attributes = {model + '.Address': address,
                  model + '.Meeting Point': meeting_point,
                  model + '.Client Install Path': client_install_path,
                  model + '.Endpoint Install Path': endpoint_install_path}
    init_context = create_init_command_context(session, 'CS_TrafficGeneratorController', model, 'na', attributes,
                                               'Service')
    driver = ByteBlowerControllerShell2GDriver()
    driver.initialize(init_context)
    print(driver.logger.handlers[0].baseFilename)
    yield driver
    driver.cleanup()


@pytest.fixture()
def context(session, model, alias, server, client_install_path, configuration, endpoint_install_path):
    address, meeting_point = server
    attributes = [AttributeNameValue(model + '.Address', address),
                  AttributeNameValue(model + '.Meeting Point', meeting_point),
                  AttributeNameValue(model + '.Client Install Path', client_install_path),
                  AttributeNameValue(model + '.Endpoint Install Path', endpoint_install_path)]
    context = create_service_command_context(session, model, alias, attributes)
    add_resources_to_reservation(context, *ports[configuration[0].split('/')[-1].split('.')[0]])
    reservation_ports = get_resources_from_reservation(context,
                                                       'ByteBlower Chassis Shell 2G.GenericTrafficGeneratorPort')
    wan_port = [p for p in reservation_ports if 'nontrunk' in p.Name][0]
    set_family_attribute(context, wan_port.Name, 'Logical Name', 'WAN_PORT')
    for i, port in enumerate([p for p in reservation_ports if 'nontrunk' not in p.Name]):
        set_family_attribute(context, port.Name, 'Logical Name', ports_logical_names[i])
    reservation_eps = get_resources_from_reservation(context,
                                                     'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint')
    for i, ep in enumerate(reservation_eps):
        set_family_attribute(context, ep.Name, 'Logical Name', eps_logical_names[i])
        set_family_attribute(context, ep.Name, 'SSID', eps_ssids[i])
    yield context
    end_reservation(session, get_reservation_id(context))


class TestByteBlowerControllerDriver(object):

    def test_load_config(self, driver, context, configuration):
        driver.load_config(context, *configuration)

    def test_load_invalid_config(self, driver, context, configuration):
        with pytest.raises(Exception) as _:
            driver.load_config(context, 'invalid_config_name', configuration[1])
        with pytest.raises(Exception) as _:
            driver.load_config(context, configuration[0], 'invalid_scenario_name')
            driver.start_traffic(context, 'False')

    def test_run_traffic(self, driver, context, configuration):

        for _ in range(0, 1):
            driver.load_config(context, *configuration)
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

    def test_load_config(self, session, context, alias, configuration):
        session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                               'load_config',
                               [InputNameValue('config_file_location', configuration[0]),
                                InputNameValue('scenario', configuration[1])])

    def test_run_traffic(self, session, context, alias, configuration):

        for _ in range(0, 1):
            session.ExecuteCommand(get_reservation_id(context), alias, 'Service',
                                   'load_config',
                                   [InputNameValue('config_file_location', configuration[0]),
                                    InputNameValue('scenario', configuration[1])])

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
