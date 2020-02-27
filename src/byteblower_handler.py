
from __future__ import print_function  # Only Python 2.x

import os
import time
import tempfile
import xml.etree.ElementTree as ET

from cloudshell.traffic.common import TrafficHandler, get_resources_from_reservation
from cloudshell.traffic.tg import BYTEBLOWER_CHASSIS_MODEL
from cloudshell.traffic.tg_helper import (get_address, is_blocking, get_family_attribute)

from byteblower.byteblowerll import byteblower
from byteblower_threads import ServerThread, EpThread
from byteblower_data_model import ByteBlower_Controller_Shell_2G

BYTEBLOWER_PORT_MODEL = BYTEBLOWER_CHASSIS_MODEL + '.GenericTrafficGeneratorPort'
BYTEBLOWER_ENDPOINT_MODEL = BYTEBLOWER_CHASSIS_MODEL + '.ByteBlowerEndPoint'


class ByteBlowerHandler(TrafficHandler):

    def __init__(self):
        super(self.__class__, self).__init__()

        self.server_thread = None
        self.eps_threads = None
        self.reservation_ports = {}
        self.reservation_eps = {}
        self.bb_ports = {}
        self.project = None
        self.scenario = None

    def initialize(self, context, logger):

        service = ByteBlower_Controller_Shell_2G.create_from_context(context)
        super(self.__class__, self).initialize(service, logger)

    def cleanup(self):
        self.stop_traffic()
        if self.project:
            if os.path.exists(self.project):
                os.remove(self.project)

    def load_config(self, context, bbl_config_file_name, scenario):

        project = bbl_config_file_name.replace('\\', '/')
        if not os.path.exists(project):
            raise EnvironmentError('Configuration file {} not found'.format(self.project))
        self.project = tempfile.mktemp().replace('\\', '/')
        self.scenario = scenario

        xml = ET.parse(project)
        xml_root = xml.getroot()
        xml_gui_ports = xml_root.findall('ByteBlowerGuiPort')

        bb = byteblower.ByteBlower.InstanceGet()
        server = bb.ServerAdd(self.service.address)

        self.reservation_eps = {}
        for ep in get_resources_from_reservation(context, BYTEBLOWER_ENDPOINT_MODEL):
            logical_name = get_family_attribute(context, ep.Name, 'Logical Name')
            self.reservation_eps[logical_name] = ep
            xml_gui_port = self._find_xml_gui_port(xml_gui_ports, logical_name)
            identifier = get_family_attribute(context, ep.Name, 'Identifier')
            xml_gui_port.find('ByteBlowerGuiPortConfiguration').attrib['physicalInterfaceId'] = identifier

        self.reservation_ports = {}
        self.bb_ports = {}
        for port in get_resources_from_reservation(context, BYTEBLOWER_PORT_MODEL):
            logical_name = get_family_attribute(context, port.Name, 'Logical Name')
            self.reservation_ports[logical_name] = port
            xml_gui_port = self._find_xml_gui_port(xml_gui_ports, logical_name)
            bb_port_name = port.Name.split('/')[-1]
            if xml_gui_port.find('ByteBlowerGuiPortConfiguration').attrib['physicalPortId'] != '-1':
                identifier = int(bb_port_name.split('-')[-1]) - 1
                xml_gui_port.find('ByteBlowerGuiPortConfiguration').attrib['physicalPortId'] = str(identifier)
            trigger = server.PortCreate(bb_port_name).RxTriggerBasicAdd()
            if xml_gui_port.find('ByteBlowerGuiPortConfiguration').attrib['physicalPortId'] == '-1':
                ip = ''
                xml_wan_ip = xml_gui_port.find('ipv4Configuration').find('IpAddress')
                for xml_byte in xml_wan_ip.findall('bytes'):
                    byte = xml_byte.text
                    if int(byte) < 0:
                        byte = str(int(byte) + 256)
                    ip += byte
                    ip += '.'
                ip = ip.rstrip('.')
                trigger.FilterSet('ip and host {}'.format(ip))
            self.bb_ports[logical_name] = trigger.ResultHistoryGet()

        xml.write(self.project)
        # When we write the new xml, the root element is written in different style then the original one, probably
        # due to multiple namespaces. BB-CLT can't load the changed configuration. The code bellow replaces the root
        # element with the original one.
        # todo: is there any standard way to manipulate the xml so the result will be valid?
        with open(project, 'r') as p_f:
            project_lines = p_f.readlines()
            with open(self.project, 'r+') as np_f:
                new_project_lines = np_f.readlines()
                new_project_lines[0] = project_lines[1]
                new_project_lines[-1] = project_lines[-1]
                np_f.seek(0)
                np_f.writelines(new_project_lines)

    def start_traffic(self, context, blocking):

        log_file_name = self.logger.handlers[0].baseFilename
        self.output = (os.path.splitext(log_file_name)[0] + '--output').replace('\\', '/')

        self.eps_threads = {}
        for name, ep in self.reservation_eps.items():
            ep_ip = get_family_attribute(context, ep.Name, 'Address')
            self.eps_threads[name] = EpThread(self.logger, ep_ip, self.service.meeting_point,
                                              self.service.endpoint_install_path, name)
            self.eps_threads[name].start()
            time.sleep(1)
            if not self.eps_threads[name].popen:
                self.stop_traffic()
                raise Exception('Failed to start thread on EP {}, IP {}'.format(name, ep_ip))

        # add delay to ensure clients are registered before starting traffic
        time.sleep(8)
        self.server_thread = ServerThread(self.logger, self.service.client_install_path, self.project, self.scenario,
                                          self.output)
        self.server_thread.start()
        time.sleep(1)
        if not self.server_thread.popen:
            self.stop_traffic()
            raise Exception('Failed to start thread on server')
        while not self.server_thread.traffic_running:
            time.sleep(1)
            if self.server_thread.failed:
                self.stop_traffic()
                raise Exception('Failed to start traffic - {}'.format(self.server_thread.failed))

        if is_blocking(blocking):
            # todo: implement wait test.
            pass

    def stop_traffic(self):
        if self.eps_threads:
            for ep_thread in self.eps_threads.values():
                ep_thread.stop()
        if self.server_thread:
            self.server_thread.stop()

    def get_test_status(self):
        if not self.server_thread:
            return 'Not started'
        else:
            if self.server_thread.failed:
                raise Exception('Server Failed: ' + self.server_thread.failed)
            if self.server_thread.traffic_running:
                return 'Running'
            else:
                return 'Finished'

    def get_rt_statistics(self, num_samples=1):
        """

        :return: {'name': [[str, int,int]]}
        """
        rt_stats = {}
        for name, thread in self.eps_threads.items():
            rt_stats[name] = thread.counters[-num_samples:]
        for name, bb_port in self.bb_ports.items():
            bb_port.Refresh()
            cumulative = bb_port.CumulativeLatestGet()
            interval = bb_port.IntervalLatestGet()
            cumulative_bytes = cumulative.ByteCountGet()
            cumulative_mb = '{0:.2f}'.format(cumulative_bytes * 8 / 1000000.0)
            interval_bytes = interval.ByteCountGet()
            interval_mb = '{0:.2f}'.format(interval_bytes * 8 / 1000000.0)
            rt_stats[name] = [cumulative_mb, interval_mb]
            self.logger.debug('Port {} stats: {}'.format(name, rt_stats[name]))
        return rt_stats

    def get_statistics(self, context, view_name, output_type):
        # todo: attach requested output file to reservation.
        return self.output

    def _find_xml_gui_port(self, xml_gui_ports, logical_name):
        requested_xml_gui_ports = [p for p in xml_gui_ports if p.attrib['name'] == logical_name]
        if not requested_xml_gui_ports:
            raise Exception('Logical name {} not found in configuration ports {}'.
                            format(logical_name, [p.attrib['name'] for p in xml_gui_ports]))
        return requested_xml_gui_ports[0]
