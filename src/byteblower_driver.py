"""
ByteBlower controller shell driver API. The business logic is implemented in byteblower_handler.py.
"""
# pylint: disable=unused-argument
from cloudshell.shell.core.driver_context import CancellationContext, InitCommandContext, ResourceCommandContext
from cloudshell.traffic.tg import TgControllerDriver, enqueue_keep_alive

from byteblower_handler import ByteBlowerHandler


class ByteBlowerControllerShell2GDriver(TgControllerDriver):
    """ByteBlower controller shell API, no business logic."""

    def __init__(self) -> None:
        """Initialize object variables, actual initialization is performed in initialize method."""
        super().__init__()
        self.handler = ByteBlowerHandler()

    def initialize(self, context: InitCommandContext) -> None:
        """Initialize Xena controller shell (from API)."""
        super().initialize(context)
        self.handler.initialize(context, self.logger)

    def load_config(self, context: ResourceCommandContext, config_file_location: str, scenario: str) -> None:
        """Load ByteBlower configuration file, map and reserve ports."""
        enqueue_keep_alive(context)
        self.handler.load_config(context, config_file_location, scenario)

    def start_traffic(self, context: ResourceCommandContext, blocking: str) -> None:
        """Start traffic on all ports."""
        return self.handler.start_traffic(context, blocking)

    def stop_traffic(self, context: ResourceCommandContext) -> None:
        """Stop traffic on all ports."""
        self.handler.stop_traffic()

    def get_test_status(self, context: ResourceCommandContext) -> str:
        """Get test status - not started, running, finished."""
        return self.handler.get_test_status()

    def get_rt_statistics(self, context: ResourceCommandContext) -> dict:
        """Get real time statistics for all ports and endpoints."""
        return self.handler.get_rt_statistics()

    def get_statistics(self, context: ResourceCommandContext, view_name: str, output_type: str) -> str:
        """Get statistics file.

        :param view_name: Statistics view - port, stream or tpld.
        :param output_type: CSV or JSON.
        """
        return self.handler.get_statistics()

    def endpoint_health_check(self, context: ResourceCommandContext) -> str:
        """Verify all EndPoints are up and running."""
        return self.handler.validate_endpoint_wifi(context)

    def keep_alive(self, context: ResourceCommandContext, cancellation_context: CancellationContext) -> None:
        """Keep ByteBlower controller shell sessions alive (from TG controller API).

        Parent commands are not visible so we re re-define this method in child.
        """
        super().keep_alive(context, cancellation_context)
