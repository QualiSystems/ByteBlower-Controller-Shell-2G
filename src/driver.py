from cloudshell.traffic.driver import TrafficControllerDriver

from byteblower_handler import ByteBlowerHandler


class ByteBlowerControllerShell2GDriver(TrafficControllerDriver):

    def __init__(self):
        super(self.__class__, self).__init__()
        self.handler = ByteBlowerHandler()

    def load_config(self, context, config_file_location):
        """ Create ByteBlower configuration with the requested ports.

        :param config_file_location: Full path to byteblower configuration file name - bbl
        """
        super(self.__class__, self).load_config(context)
        self.handler.load_config(context, config_file_location)

    def start_traffic(self, context, blocking):
        """ Start traffic on all ports.

        :param blocking: True - return after traffic finish to run, False - return immediately.
        """
        self.handler.start_traffic(blocking)
        return 'traffic started in {} mode'.format(blocking)

    def stop_traffic(self, context):
        """ Stop traffic on all ports. """
        self.handler.stop_traffic()

    def get_rt_statistics(self, context):
        """ Get real time statistics for all ports and endpoints. """
        pass

    def get_statistics(self, context, output_type):
        """ Get statistics.

        :param output_type: CSV or JSON.
        """
        return self.handler.get_statistics(context, output_type)

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
