
import os
import xml.etree.ElementTree as ET

# the frameInterval=60000 is a value in nanoseconds, which corresponds with the 60ms that you see in the GUI.
# dataRateUnit="Mbps" indicates that the you want to see the data rate in Mbps
#
# The actual Load in Mbps is then calculated by the GUI, based on :
#
#     Size of the used Frames (in bytes)
#     Timing modifier settings
#     Frame Size Modifier settings
#     What Frame fields are included in the calculation : FCS,Preamble, SFD, Pause bytes
#
# In your case, you have one Frame per Frame Blasting Flow Template. In that case, it's easy to convert from Mbps to nanoseconds Frame Interval, and vice versa :
# If you have, like in your FRAME_BLASTING_1 :
#
#     Frame Size : 1500 bytes
#     interval : 60000ns
#
# Then the bitrate is : 1000000000 ns/s / 60000ns * 1500byte * 8 bits/byte = 200000000 bits/s = 200Mbps


def load_config(bbl_config_file_name):

    project = bbl_config_file_name.replace('\\', '/')
    if not os.path.exists(project):
        raise EnvironmentError('Configuration file {} not found'.format(self.project))

    xml = ET.parse(project)
    xml_root = xml.getroot()
    xml_gui_ports = xml_root.findall('ByteBlowerGuiPort')
    xml_flows_templates = xml_root.findall('FlowTemplate')
    xml_frames = xml_root.findall('Frame')

    bb_ports = {}
    for xml_gui_port in xml_gui_ports:
        try:
            int(xml_gui_port.find('ByteBlowerGuiPortConfiguration').attrib['physicalInterfaceId'])
            bb_port = xml_gui_port.attrib['name']
            bb_ports[bb_port] = {}
            for bb_flow in xml_gui_port.attrib['theSourceOfFlow'].split():
                bb_ports[bb_port][bb_flow] = {}
                xml_flow = [f for f in xml_flows_templates if f.attrib['Flow'] == bb_flow][0]
                bb_ports[bb_port][bb_flow]['template'] = xml_flow
                frame_index = int(xml_flow.find('frameBlastingFrames').attrib['frame'].split('.')[-1])
                bb_ports[bb_port][bb_flow]['frame'] = xml_frames[frame_index]
        except ValueError as _:
            pass

    print('')
    bb_ports_intended_tx = {}
    for bb_port, bb_flows in bb_ports.items():
        print(bb_port, bb_flows)
        bb_ports_intended_tx[bb_port] = 0
        for bb_flow in bb_flows.values():
            frame_interval_ns = float(bb_flow['template'].attrib['frameInterval'])
            frame_length = len(bb_flow['frame'].attrib['bytesHexString']) / 2
            intended_mbps = 1000000000 / frame_interval_ns * frame_length * 8 / 1000 / 1000
            print('{} {} {}'.format(frame_interval_ns, frame_length, intended_mbps))
            bb_ports_intended_tx[bb_port] += int(intended_mbps)

    print(bb_ports_intended_tx)


def test_load_config():
    load_config('../tests/test_config.bbp')
