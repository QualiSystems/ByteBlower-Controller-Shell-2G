
from cloudshell.traffic.tg import TgControllerDriver, enqueue_keep_alive

from byteblower_handler import ByteBlowerHandler


class ByteBlowerControllerShell2GDriver(TgControllerDriver):

    def __init__(self):
        self.handler = ByteBlowerHandler()

    def load_config(self, context, config_file_location, scenario):
        enqueue_keep_alive(context)
        self.handler.load_config(context, config_file_location, scenario)

    def start_traffic(self, context, blocking):
        """ Start traffic on all ports.

        :param blocking: True - return after traffic finish to run, False - return immediately.
        """
        return super(self.__class__, self).start_traffic(context, blocking)

    def stop_traffic(self, context):
        """ Stop traffic on all ports. """
        return super(self.__class__, self).stop_traffic(context)

    def get_test_status(self, context):
        """ Get test status - not started, running, finished. """
        return self.handler.get_test_status()

    def get_rt_statistics(self, context):
        """ Get real time statistics for all ports and endpoints. """
        return self.handler.get_rt_statistics()

    def get_statistics(self, context, view_name, output_type):
        """ Get view statistics.

        :param view_name: port, traffic item, flow group etc.
        :param output_type: CSV or JSON.
        """
        return super(self.__class__, self).get_statistics(context, view_name, output_type)

    #
    # Parent commands are not visible so we re define them in child.
    #

    def initialize(self, context):
        super(self.__class__, self).initialize(context)

    def cleanup(self):
        super(self.__class__, self).cleanup()

    def cleanup_reservation(self, context):
        pass

    def keep_alive(self, context, cancellation_context):
        super(self.__class__, self).keep_alive(context, cancellation_context)
