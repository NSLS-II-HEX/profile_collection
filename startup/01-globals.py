file_loading_timer.start_timer(__file__)


import asyncio
from dataclasses import dataclass
from enum import Enum

from ophyd import EpicsSignalRO
from ophyd_async.core import (
    DEFAULT_TIMEOUT,
    DetectorControl,
    DetectorTrigger,
    DetectorWriter,
    DeviceCollector,
    StandardFlyer,
    SignalRW,
    TriggerInfo,
    TriggerLogic,
)
from ophyd_async.core import AsyncStatus
from ophyd_async.core import StandardDetector
from ophyd_async.core import DeviceCollector

HEX_PROPOSAL_DIR_ROOT = "/nsls2/data/hex/proposals"


class ScanType(Enum):
    tomo_dark_flat = "tomo_dark_flat"
    tomo_flyscan = "tomo_flyscan"
    edxd = "edxd"


class TomoFrameType(Enum):
    dark = "dark"
    flat = "flat"
    proj = "proj"


class StandardTriggerState(str, Enum):
    null = "null"
    preparing = "preparing"
    starting = "starting"
    completing = "completing"
    stopping = "stopping"


@dataclass
class StandardTriggerSetup:
    num_frames: int
    exposure_time: float
    software_trigger: bool


class StandardTriggerLogic(TriggerLogic[int]):
    def __init__(self, trigger_mode=DetectorTrigger.internal):
        self.state = StandardTriggerState.null
        self.trigger_mode = trigger_mode

    def trigger_info(self, setup) -> TriggerInfo:
        exposure = 0.1
        trigger = self.trigger_mode
        num_images = setup
        if isinstance(setup, StandardTriggerSetup):
            if (
                not setup.software_trigger
                and self.trigger_mode == DetectorTrigger.internal
            ):
                trigger = DetectorTrigger.edge_trigger
            exposure = setup.exposure_time
            num_images = setup.num_frames
        return TriggerInfo(
            number=num_images,
            trigger=trigger,
            deadtime=0.1,
            livetime=exposure,
            multiplier=1,
        )

    async def prepare(self, value: int):
        self.state = StandardTriggerState.preparing
        return value

    async def kickoff(self):
        self.state = StandardTriggerState.starting

    async def complete(self):
        self.state = StandardTriggerState.completing

    async def stop(self):
        self.state = StandardTriggerState.stopping


async def print_children(device):
    for name, obj in dict(device.children()).items():
        print(f"{name}: {await obj.read()}")


file_loading_timer.stop_timer(__file__)
