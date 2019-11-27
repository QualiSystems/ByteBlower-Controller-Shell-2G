
from __future__ import print_function  # Only Python 2.x

import os
import time

from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.traffic.tg_helper import (get_reservation_resources, get_address, is_blocking, attach_stats_csv,
                                          get_family_attribute)

from byteblower.byteblowerll import byteblower
from byteblower_threads import ServerThread, EpThread


def _get_target_attr_obj(api, resource_name, target_attr_name):
    """
    get attribute "object" {Name, Value} on resource
    Includes validation for 2nd gen shell namespace by pre-fixing family/model namespace
    :param CloudShellAPISession api:
    :param str resource_name:
    :param str target_attr_name: the name of target attribute. Do not include the prefixed-namespace
    :return attribute object or None:
    """
    res_details = api.GetResourceDetails(resource_name)
    res_model = res_details.ResourceModelName
    res_family = res_details.ResourceFamilyName

    # Attribute names with 2nd gen name space (using family or model)
    target_model_attr = "{model}.{attr}".format(model=res_model, attr=target_attr_name)
    target_family_attr = "{family}.{attr}".format(family=res_family, attr=target_attr_name)

    # check against all 3 possibilities
    target_res_attr_filter = [attr for attr in res_details.ResourceAttributes if attr.Name == target_attr_name
                              or attr.Name == target_model_attr
                              or attr.Name == target_family_attr]
    if target_res_attr_filter:
        return target_res_attr_filter[0]
    else:
        return None


def get_resource_attr_val(api, resource_name, target_attr_name):
    """
    Get value of attribute if it exists
    :param CloudShellAPISession api:
    :param str resource_name:
    :param str target_attr_name:
    :return:
    """
    target_attr_obj = _get_target_attr_obj(api, resource_name, target_attr_name)
    if target_attr_obj:
        return target_attr_obj.Value
    else:
        return None


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

        my_api = CloudShellSessionContext(context).get_api()

        self.project = bbl_config_file_name.replace('\\', '/')
        self.scenario = scenario

        bb = byteblower.ByteBlower.InstanceGet()
        server = bb.ServerAdd(self.server_address)
        self.port_45 = server.PortCreate('trunk-1-45')

        reservation_ports = {}
        self.reservation_eps = {}
        for port in get_reservation_resources(my_api, context.reservation.reservation_id,
                                              'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint'):
            reservation_ports[get_family_attribute(my_api, port, 'Logical Name').Value.strip()] = port
            if port.ResourceModelName == 'ByteBlower Chassis Shell 2G.ByteBlowerEndPoint':
                self.reservation_eps[get_family_attribute(my_api, port, 'Logical Name').Value.strip()] = port

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

        my_api = CloudShellSessionContext(context).get_api()

        log_file_name = self.logger.handlers[0].baseFilename
        self.output = (os.path.splitext(log_file_name)[0] + '--output').replace('\\', '/')

        self.eps_threads = {}
        for name, resource in self.reservation_eps.items():
            address = get_resource_attr_val(my_api, resource.Name, 'Address')
            self.eps_threads[name] = EpThread(self.logger, address, self.meeting_point, name)
            self.eps_threads[name].start()

        # add delay to ensure clients are registered before starting traffic
        time.sleep(8)
        self.server_thread = ServerThread(self.logger, self.client_install_path, self.project, self.scenario,
                                          self.output)
        self.server_thread.start()
        time.sleep(1)

        if is_blocking(blocking):
            # todo: implement wait test.
            pass

    def stop_traffic(self):
        if self.ep_thread:
            self.ep_thread.stop()
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

    def get_statistics(self, context, output_type):
        # todo: attach requested output file to reservation.
        return self.output
