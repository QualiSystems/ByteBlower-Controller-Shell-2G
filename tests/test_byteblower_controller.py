
from os import path
import time
import pytest

from cloudshell.api.cloudshell_api import AttributeNameValue, InputNameValue, CloudShellAPISession
from cloudshell.shell.core.driver_context import ResourceCommandContext
from cloudshell.traffic.helpers import set_family_attribute, get_reservation_id, get_resources_from_reservation
from cloudshell.traffic.tg import BYTEBLOWER_CONTROLLER_MODEL, BYTEBLOWER_CHASSIS_MODEL
from shellfoundry_traffic.test_helpers import create_session_from_config, TestHelpers

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
client_install_path = 'C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe'
endpoint_install_path = 'C:/ByteBlowerWirelessEndpoint/$PLUGINSDIR/BBWEP/byteblower-wireless-endpoint.exe'
alias = 'ByteBlower Controller'


@pytest.fixture()
def server() -> list:
    return ['10.113.137.22', '192.168.0.3']


# @pytest.fixture(params=[('test_config', 'test_config')],
#                 ids=['test_config'])
@pytest.fixture(params=[('test_config_4_cpes', 'test_config_4_cpes')],
                ids=['test_config_4_cpes'])
def configuration(request) -> list:
    config_file = path.join(path.dirname(__file__), request.param[0]) + '.bbp'
    scenario = request.param[1]
    return [config_file.replace('\\', '/'), scenario]


@pytest.fixture(scope='session')
def session() -> CloudShellAPISession:
    yield create_session_from_config()


@pytest.fixture()
def test_helpers(session: CloudShellAPISession) -> TestHelpers:
    test_helpers = TestHelpers(session)
    test_helpers.create_reservation()
    yield test_helpers
    test_helpers.end_reservation()


@pytest.fixture()
def driver(test_helpers: TestHelpers, server: list) -> ByteBlowerControllerShell2GDriver:
    address, meeting_point = server
    attributes = {f'{BYTEBLOWER_CONTROLLER_MODEL}.Address': address,
                  f'{BYTEBLOWER_CONTROLLER_MODEL}.Meeting Point': meeting_point,
                  f'{BYTEBLOWER_CONTROLLER_MODEL}.Client Install Path': client_install_path,
                  f'{BYTEBLOWER_CONTROLLER_MODEL}.Endpoint Install Path': endpoint_install_path}
    init_context = test_helpers.service_init_command_context(BYTEBLOWER_CONTROLLER_MODEL, attributes)
    driver = ByteBlowerControllerShell2GDriver()
    driver.initialize(init_context)
    print(driver.logger.handlers[0].baseFilename)
    yield driver
    driver.cleanup()


@pytest.fixture()
def context(session: CloudShellAPISession, test_helpers: TestHelpers, server: list,
            configuration: list) -> ResourceCommandContext:
    address, meeting_point = server
    attributes = [AttributeNameValue(f'{BYTEBLOWER_CONTROLLER_MODEL}.Address', address),
                  AttributeNameValue(f'{BYTEBLOWER_CONTROLLER_MODEL}.Meeting Point', meeting_point),
                  AttributeNameValue(f'{BYTEBLOWER_CONTROLLER_MODEL}.Client Install Path', client_install_path),
                  AttributeNameValue(f'{BYTEBLOWER_CONTROLLER_MODEL}.Endpoint Install Path', endpoint_install_path)]
    session.AddServiceToReservation(test_helpers.reservation_id, BYTEBLOWER_CONTROLLER_MODEL, alias, attributes)
    context = test_helpers.resource_command_context(service_name=alias)
    session.AddResourcesToReservation(test_helpers.reservation_id, ports[configuration[1]])
    reservation_ports = get_resources_from_reservation(context,
                                                       f'{BYTEBLOWER_CHASSIS_MODEL}.GenericTrafficGeneratorPort')
    wan_port = [p for p in reservation_ports if 'nontrunk' in p.Name][0]
    set_family_attribute(context, wan_port.Name, 'Logical Name', 'WAN_PORT')
    for i, port in enumerate([p for p in reservation_ports if 'nontrunk' not in p.Name]):
        set_family_attribute(context, port.Name, 'Logical Name', ports_logical_names[i])
    reservation_eps = get_resources_from_reservation(context, f'{BYTEBLOWER_CHASSIS_MODEL}.ByteBlowerEndPoint')
    for i, ep in enumerate(reservation_eps):
        set_family_attribute(context, ep.Name, 'Logical Name', eps_logical_names[i])
        set_family_attribute(context, ep.Name, 'SSID', eps_ssids[i])
    yield context


class TestByteBlowerControllerDriver:

    def test_load_config(self, driver: ByteBlowerControllerShell2GDriver, context: ResourceCommandContext,
                         configuration: list) -> None:
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
            print(f'output folder = {output}')


class TestByteBlowerControllerShell:

    def test_load_config(self, session: CloudShellAPISession, context: ResourceCommandContext,
                         configuration: list) -> None:
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
