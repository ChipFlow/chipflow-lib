# SPDX-License-Identifier: BSD-2-Clause
"""
Base classes for package definitions.

This module provides the abstract base classes that all package
definitions inherit from, defining the common interface for
pin allocation and package description.
"""

import abc
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Generic, List, Set, TypeVar

import pydantic
from amaranth.lib import wiring, io
from typing_extensions import Self

from ..platform.io import IOModel
from .pins import Pins, PinList, BringupPins
from .port_desc import PortDesc, Component, Interface
from .lockfile import Package, LockFile
from .allocation import _linear_allocate_components

if TYPE_CHECKING:
    from ..config_models import Config, Process

# Type variable for pin types (int for linear allocation, GAPin for grid arrays, etc.)
PinType = TypeVar('PinType')


class BasePackageDef(pydantic.BaseModel, Generic[PinType], abc.ABC):
    """
    Abstract base class for the definition of a package.

    Serializing this or any derived classes results in the
    description of the package (not serializable directly).

    All package definitions must inherit from this class and
    implement the required abstract methods.

    Attributes:
        name: The name of the package
    """

    name: str

    def model_post_init(self, __context):
        """Initialize internal tracking structures"""
        self._interfaces: Dict[str, dict] = {}
        self._components: Dict[str, wiring.Component] = {}
        if not hasattr(self, '_ordered_pins'):
            self._ordered_pins = None  # stop pyright complaining..
            assert True, "Subclass must set self._ordered_pins in model_post_init"
        return super().model_post_init(__context)

    def register_component(self, name: str, component: wiring.Component) -> None:
        """
        Register a component to be allocated to the pad ring and pins.

        Args:
            name: Component name
            component: Amaranth wiring.Component to allocate
        """
        self._components[name] = component
        self._interfaces[name] = component.metadata.as_json()

    def _get_package(self) -> Package:
        """Get Package model for this definition"""
        assert self is not Self
        return Package(package_type=self)  # type: ignore

    def _allocate_bringup(self, config: 'Config') -> Component:
        """
        Allocate bringup pins (clock, reset, power, debug).

        Args:
            config: ChipFlow configuration

        Returns:
            Component dictionary with bringup interface
        """
        cds = set(config.chipflow.clock_domains) if config.chipflow.clock_domains else set()
        cds.discard('sync')

        d: Interface = {
            'clk': PortDesc(
                type='clock',
                pins=[self.bringup_pins.core_clock],
                port_name='clk',
                iomodel=IOModel(width=1, direction=io.Direction.Input, clock_domain="sync")
            ),
            'rst_n': PortDesc(
                type='reset',
                pins=[self.bringup_pins.core_reset],
                port_name='rst_n',
                iomodel=IOModel(
                    width=1,
                    direction=io.Direction.Input,
                    clock_domain="sync",
                    invert=True
                )
            ),
        }

        # Group power pins by name
        powerpins = defaultdict(list)
        for pp in self.bringup_pins.core_power:
            vss = "vss"
            vdd = "vdd"
            if pp.name:
                vss = f"{pp.name}vss"
                vdd = f"{pp.name}vdd"
            powerpins[vss].append(pp.power)
            powerpins[vdd].append(pp.ground)

        for domain, pins in powerpins.items():
            d[domain] = PortDesc(
                type='power',
                pins=pins,
                port_name=domain,
                iomodel=IOModel(width=len(pins), direction=io.Direction.Input)
            )

        # Add heartbeat if enabled
        assert config.chipflow.silicon
        if config.chipflow.silicon.debug and \
           config.chipflow.silicon.debug['heartbeat']:
            d['heartbeat'] = PortDesc(
                type='heartbeat',
                pins=[self.bringup_pins.core_heartbeat],
                port_name='heartbeat',
                iomodel=IOModel(width=1, direction=io.Direction.Output, clock_domain="sync")
            )

        # TODO: JTAG support

        return {'bringup_pins': d}

    def allocate_pins(self, config: 'Config', process: 'Process', lockfile: LockFile | None) -> LockFile:
        """
        Allocate package pins to the registered components.

        Pins should be allocated in the most usable way for users
        of the packaged IC.

        This default implementation uses _linear_allocate_components with
        self._allocate for the allocation strategy. Subclasses can override
        if they need completely different allocation logic.

        Args:
            config: ChipFlow configuration
            process: Semiconductor process
            lockfile: Optional existing lockfile to preserve allocations

        Returns:
            LockFile representing the pin allocation

        Raises:
            UnableToAllocate: If the ports cannot be allocated
        """
        assert self._ordered_pins is not None, "Subclass must set self._ordered_pins in model_post_init"
        portmap = _linear_allocate_components(
            self._interfaces,
            lockfile,
            self._allocate,
            set(self._ordered_pins)
        )
        bringup_pins = self._allocate_bringup(config)
        portmap.ports['_core'] = bringup_pins
        package = self._get_package()
        return LockFile(package=package, process=process, metadata=self._interfaces, port_map=portmap)

    @abc.abstractmethod
    def _allocate(self, available: Set[PinType], width: int) -> List[PinType]:
        """
        Allocate pins from available set.

        Subclasses must implement this to define their allocation strategy.

        Args:
            available: Set of available pins (type depends on package)
            width: Number of pins needed

        Returns:
            List of allocated pins

        Raises:
            UnableToAllocate: If allocation fails
        """
        ...

    @property
    @abc.abstractmethod
    def bringup_pins(self) -> BringupPins:
        """
        Get the bringup pins for this package.

        To aid bringup, these are always in the same place for each
        package type. Should include core power, clock and reset.

        Power, clocks and resets needed for non-core are allocated
        with the port.

        Returns:
            BringupPins configuration
        """
        ...

    def _sortpins(self, pins: Pins) -> PinList:
        """Sort pins into canonical ordering"""
        return sorted(list(pins))


class LinearAllocPackageDef(BasePackageDef[int]):
    """
    Base class for package types with linear pin/pad allocation.

    This is used for packages where pins are allocated from a
    simple linear ordering (e.g., numbered pins around a perimeter).

    Subclasses should populate self._ordered_pins in model_post_init
    before calling super().model_post_init(__context).

    Not directly serializable - use concrete subclasses.
    """

    def _allocate(self, available: Set[int], width: int) -> List[int]:
        """
        Allocate pins from available set.

        Args:
            available: Set of available pins
            width: Number of pins needed

        Returns:
            List of allocated pins (as contiguous as possible)
        """
        from .allocation import _find_contiguous_sequence
        assert self._ordered_pins
        avail_n = sorted(available)
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        assert len(ret) == width
        return ret
