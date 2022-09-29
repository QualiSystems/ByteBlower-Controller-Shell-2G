"""
Tests for ByteBlowerControllerShell2GDriver.
"""
import time
from pathlib import Path
from typing import Iterable

import pytest
from cloudshell.api.cloudshell_api import AttributeNameValue, CloudShellAPISession, InputNameValue
from cloudshell.shell.core.driver_context import ResourceCommandContext
from cloudshell.traffic.helpers import get_reservation_id, get_resources_from_reservation, set_family_attribute
from cloudshell.traffic.tg import BYTEBLOWER_CHASSIS_MODEL, BYTEBLOWER_CONTROLLER_MODEL
from shellfoundry_traffic.test_helpers import TgTestHelpers, session, test_helpers

from src.byteblower_driver import ByteBlowerControllerShell2GDriver

eps_logical_names = ["EP01_2G", "EP02_5G", "EP03_2G", "EP04_5G"]
eps_ssids = ["Mv2Automation2G", "Mv2Automation5G", "Mv2Automation2G", "Mv2Automation5G"]
ports_logical_names = ["PORT_A", "PORT_B", "PORT_C", "PORT_D"]

ports = [
    "nl-srk03d-bb-st01.upclabs.com/Module1/trunk-1-1",
    "nl-srk03d-bb-st01.upclabs.com/Module1/trunk-1-2",
]

client_install_path = "C:/Program Files (x86)/Excentis/ByteBlower-CLT-v2/ByteBlower-CLT.exe"

ALIAS = "ByteBlower Controller"


@pytest.fixture
def server() -> list:
    """Yield server information."""
    return ["172.30.127.200", "172.30.127.200"]


@pytest.fixture
def driver(test_helpers: TgTestHelpers, server: list) -> Iterable[ByteBlowerControllerShell2GDriver]:
    """Yield initialized ByteBlowerControllerShell2GDriver."""
    address, meeting_point = server
    attributes = {
        f"{BYTEBLOWER_CONTROLLER_MODEL}.Address": address,
        f"{BYTEBLOWER_CONTROLLER_MODEL}.Meeting Point": meeting_point,
        f"{BYTEBLOWER_CONTROLLER_MODEL}.Client Install Path": client_install_path,
    }
    init_context = test_helpers.service_init_command_context(BYTEBLOWER_CONTROLLER_MODEL, attributes)
    driver = ByteBlowerControllerShell2GDriver()
    driver.initialize(init_context)
    yield driver
    driver.cleanup()


@pytest.fixture()
def context(session: CloudShellAPISession, test_helpers: TgTestHelpers, server: list) -> ResourceCommandContext:
    """Yield ResourceCommandContext for shell command testing."""
    address, meeting_point = server
    attributes = [
        AttributeNameValue(f"{BYTEBLOWER_CONTROLLER_MODEL}.Address", address),
        AttributeNameValue(f"{BYTEBLOWER_CONTROLLER_MODEL}.Meeting Point", meeting_point),
        AttributeNameValue(f"{BYTEBLOWER_CONTROLLER_MODEL}.Client Install Path", client_install_path),
    ]
    session.AddServiceToReservation(test_helpers.reservation_id, BYTEBLOWER_CONTROLLER_MODEL, ALIAS, attributes)
    context = test_helpers.resource_command_context(service_name=ALIAS)
    session.AddResourcesToReservation(test_helpers.reservation_id, ports)
    reservation_ports = get_resources_from_reservation(context, f"{BYTEBLOWER_CHASSIS_MODEL}.GenericTrafficGeneratorPort")
    set_family_attribute(context, reservation_ports[0].Name, "Logical Name", "Port 1")
    set_family_attribute(context, reservation_ports[0].Name, "Address", "10.0.0.22")
    set_family_attribute(context, reservation_ports[0].Name, "Mac Address", "00:00:00:00:00:11")
    set_family_attribute(context, reservation_ports[1].Name, "Logical Name", "Port 2")
    set_family_attribute(context, reservation_ports[0].Name, "Address", "10.0.0.33")
    set_family_attribute(context, reservation_ports[1].Name, "Mac Address", "00:00:00:00:00:22")
    return context


class TestByteBlowerControllerDriver:
    """Test direct driver calls."""

    def test_load_config(self, driver: ByteBlowerControllerShell2GDriver, context: ResourceCommandContext) -> None:
        """Test load configuration command."""
        config_file_path = Path(__file__).parent.joinpath("test_config.bbp").as_posix()
        driver.load_config(context, config_file_path, scenario="Frame Size Scenario 1")

    def test_load_invalid_config(self, driver: ByteBlowerControllerShell2GDriver, context: ResourceCommandContext) -> None:
        """Negative tests for load config."""
        with pytest.raises(Exception):
            driver.load_config(context, "invalid_config_name", "")
        config_file_path = Path(__file__).parent.joinpath("test_config.bbp").as_posix()
        with pytest.raises(Exception) as _:
            driver.load_config(context, config_file_path, scenario="invalid_scenario_name")

    def test_run_traffic(self, driver: ByteBlowerControllerShell2GDriver, context: ResourceCommandContext) -> None:
        """Test run traffic and get statistics."""
        config_file_path = Path(__file__).parent.joinpath("test_config.bbp").as_posix()
        for _ in range(0, 1):
            driver.load_config(context, config_file_path, scenario="Frame Size Scenario 1")
            driver.start_traffic(context, "False")
            status = driver.get_test_status(context)
            while status.lower() != "finished":
                time.sleep(1)
                print(driver.get_rt_statistics(context))
                status = driver.get_test_status(context)
            driver.stop_traffic(context)
            output = driver.get_statistics(context, None, None)
            print(f"output folder = {output}")


class TestByteBlowerControllerShell:
    """Test indirect Shell calls."""

    def test_load_config(self, session: CloudShellAPISession, context: ResourceCommandContext) -> None:
        """Test load configuration command."""
        command_inputs = [
            InputNameValue("config_file_location", "C:/temp/test_config.bbp"),
            InputNameValue("scenario", "Frame Size Scenario 1"),
        ]
        session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "load_config", command_inputs)

    def test_run_traffic(self, session: CloudShellAPISession, context: ResourceCommandContext) -> None:
        """Test run traffic and get statistics."""
        command_inputs = [
            InputNameValue("config_file_location", "C:/temp/test_config.bbp"),
            InputNameValue("scenario", "Frame Size Scenario 1"),
        ]
        for _ in range(0, 1):
            session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "load_config", command_inputs)

            session.ExecuteCommand(
                get_reservation_id(context),
                ALIAS,
                "Service",
                "start_traffic",
                [InputNameValue("blocking", "False")],
            )
            status = session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "get_test_status")
            while status.Output.lower() != "finished":
                time.sleep(1)
                rt_stats = session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "get_rt_statistics")
                print(rt_stats.Output)
                status = session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "get_test_status")
            session.ExecuteCommand(get_reservation_id(context), ALIAS, "Service", "stop_traffic")
            stats = session.ExecuteCommand(
                get_reservation_id(context),
                ALIAS,
                "Service",
                "get_statistics",
                [
                    InputNameValue("view_name", None),
                    InputNameValue("output_type", None),
                ],
            )
            print(stats.Output)
