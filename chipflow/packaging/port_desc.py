# SPDX-License-Identifier: BSD-2-Clause
"""
Port description models for pin allocation.

This module provides models for describing port-to-pin mappings
and managing the overall port map for an IC package.
"""

from collections.abc import Iterable
from typing import Dict, Generic, List

import pydantic

from ..platform.io import IOModel
from .pins import Pin


class PortDesc(pydantic.BaseModel, Generic[Pin]):
    """
    Description of a port and its pin assignment.

    Attributes:
        type: Type of port (e.g., 'io', 'clock', 'reset', 'power', 'heartbeat')
        pins: List of pins assigned to this port, or None if not yet allocated
        port_name: Name of the port
        iomodel: IO model configuration for this port
    """
    type: str
    pins: List[Pin] | None  # None implies must be allocated at end
    port_name: str
    iomodel: IOModel

    @property
    def width(self):
        """Width of the port (number of pins)"""
        assert self.pins and 'width' in self.iomodel
        assert len(self.pins) == self.iomodel['width']
        return self.iomodel['width']

    @property
    def direction(self):
        """Direction of the port"""
        assert 'direction' in self.iomodel
        return self.iomodel['direction']

    @property
    def invert(self) -> Iterable[bool] | None:
        """Inversion settings for port wires"""
        if 'invert' in self.iomodel:
            if type(self.iomodel['invert']) is bool:
                return (self.iomodel['invert'],)
            else:
                return self.iomodel['invert']
        else:
            return None


# Type aliases for hierarchical port organization
Interface = Dict[str, PortDesc]
Component = Dict[str, Interface]


class PortMap(pydantic.BaseModel):
    """
    Mapping of components to interfaces to ports.

    This represents the complete pin allocation for an IC package,
    organized hierarchically by component and interface.
    """
    ports: Dict[str, Component] = {}

    def _add_port(self, component: str, interface: str, port_name: str, port: PortDesc):
        """
        Add a single port to the map (internally used by PackageDef).

        Args:
            component: Component name
            interface: Interface name
            port_name: Port name
            port: Port description
        """
        if component not in self.ports:
            self.ports[component] = {}
        if interface not in self.ports[component]:
            self.ports[component][interface] = {}
        self.ports[component][interface][port_name] = port

    def _add_ports(self, component: str, interface: str, ports: Interface):
        """
        Add multiple ports for an interface (internally used by PackageDef).

        Args:
            component: Component name
            interface: Interface name
            ports: Dictionary of port name to PortDesc
        """
        if component not in self.ports:
            self.ports[component] = {}
        self.ports[component][interface] = ports

    def get_ports(self, component: str, interface: str) -> Interface | None:
        """
        Get ports for a specific component and interface.

        Args:
            component: Component name
            interface: Interface name

        Returns:
            Dictionary of port names to PortDesc, or None if not found
        """
        if component not in self.ports or interface not in self.ports[component]:
            return None
        return self.ports[component][interface]

    def get_clocks(self) -> List[PortDesc]:
        """Get all clock ports in the port map"""
        ret = []
        for n, c in self.ports.items():
            for cn, i in c.items():
                for ni, p in i.items():
                    if p.type == "clock":
                        ret.append(p)
        return ret

    def get_resets(self) -> List[PortDesc]:
        """Get all reset ports in the port map"""
        ret = []
        for n, c in self.ports.items():
            for cn, i in c.items():
                for ni, p in i.items():
                    if p.type == "reset":
                        ret.append(p)
        return ret
