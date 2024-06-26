file_loading_timer.start_timer(__file__)


print(f"Loading file {__file__!r} ...")


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
    HardwareTriggeredFlyable,
    ShapeProvider,
    SignalRW,
    TriggerInfo,
    TriggerLogic,
)
from ophyd_async.core.async_status import AsyncStatus
from ophyd_async.core.detector import StandardDetector
from ophyd_async.core.device import DeviceCollector
from ophyd_async.epics.areadetector.controllers.kinetix_controller import (
    KinetixController,
)
from ophyd_async.epics.areadetector.drivers.kinetix_driver import (
    KinetixDriver,
    KinetixReadoutMode,
)
from ophyd_async.epics.areadetector.writers.hdf_writer import HDFWriter
from ophyd_async.epics.areadetector.writers.nd_file_hdf import NDFileHDF

KINETIX_PV_PREFIX = "XF:27ID1-BI{Kinetix-Det:1}"


class KinetixTriggerState(str, Enum):
    null = "null"
    preparing = "preparing"
    starting = "starting"
    stopping = "stopping"


@dataclass
class KinetixTriggerSetup:
    num_images: int
    exposure_time: float
    software_trigger: bool


class KinetixTriggerLogic(TriggerLogic[int]):
    def __init__(self):
        self.state = KinetixTriggerState.null

    def trigger_info(self, setup) -> TriggerInfo:
        trigger = DetectorTrigger.internal
        if not setup.software_trigger:
            trigger = DetectorTrigger.edge_trigger
        return TriggerInfo(
            num=setup.num_images,
            trigger=trigger,
            deadtime=0.1,
            livetime=setup.exposure_time,
        )

    async def prepare(self, value: int):
        self.state = KinetixTriggerState.preparing
        return value

    async def start(self):
        self.state = KinetixTriggerState.starting

    async def stop(self):
        self.state = KinetixTriggerState.stopping


kinetix_trigger_logic = KinetixTriggerLogic()


class KinetixShapeProvider(ShapeProvider):
    def __init__(self) -> None:
        pass

    async def __call__(self):
        return (3200, 3200)  # y, x


def instantiate_kinetix_async():
    with DeviceCollector():
        kinetix_async = KinetixDriver(KINETIX_PV_PREFIX + "cam1:")
        hdf_plugin_kinetix = NDFileHDF(
            KINETIX_PV_PREFIX + "HDF1:", name="kinetix_hdf_plugin"
        )

    with DeviceCollector():
        # dir_prov = UUIDDirectoryProvider("/nsls2/data/hex/proposals/commissioning/pass-315051/tomography/bluesky_test/kinetix")
        dir_prov = ScanIDDirectoryProvider(PROPOSAL_DIR)
        kinetix_writer = HDFWriter(
            hdf_plugin_kinetix,
            dir_prov,
            lambda: "hex-kinetix1",
            KinetixShapeProvider(),
        )
        print_children(kinetix_async)

    return kinetix_async, kinetix_writer


kinetix_async, kinetix_writer = instantiate_kinetix_async()
kinetix_controller = KinetixController(kinetix_async)

kinetix_exposure_time = EpicsSignalRO(
    "XF:27ID1-BI{Kinetix-Det:1}cam1:AcquireTime_RBV", name="kinetix_exposure_time"
)
sd.baseline.append(kinetix_exposure_time)
RE.preprocessors.append(sd)


# TODO: add as a new component into ophyd-async.
kinetix_hdf_status = EpicsSignalRO(
    "XF:27ID1-BI{Kinetix-Det:1}HDF1:WriteFile_RBV",
    name="kinetix_hdf_status",
    string=True,
)


# Create Kinetix standard detector with long writer timeout to account for filewriting delay
kinetix_standard_det = StandardDetector(
    kinetix_controller,
    kinetix_writer,
    name="kinetix_standard_det",
    writer_timeout=600.0,
)


kinetix_flyer = HardwareTriggeredFlyable(
    kinetix_trigger_logic, [], name="kinetix_flyer"
)


def kinetix_stage():
    yield from bps.stage(kinetix_standard_det)
    yield from bps.sleep(5)


def inner_kinetix_collect():

    yield from bps.kickoff(kinetix_flyer)
    yield from bps.kickoff(kinetix_standard_det)

    yield from bps.complete(kinetix_flyer, wait=True, group="complete")
    yield from bps.complete(kinetix_standard_det, wait=True, group="complete")

    # Manually incremenet the index as if a frame was taken
    # detector.writer.index += 1

    done = False
    while not done:
        try:
            yield from bps.wait(group="complete", timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            kinetix_standard_det,
            stream=True,
            return_payload=False,
            name=f"{kinetix_standard_det.name}_stream",
        )
        yield from bps.sleep(0.01)

    yield from bps.wait(group="complete")
    val = yield from bps.rd(kinetix_writer.hdf.num_captured)
    print(f"{val = }")


def kinetix_collect(num=10, exposure_time=0.1, software_trigger=True):

    kinetix_exp_setup = KinetixTriggerSetup(
        num_images=num, exposure_time=exposure_time, software_trigger=software_trigger
    )

    yield from bps.open_run()

    yield from bps.stage_all(kinetix_standard_det, kinetix_flyer)

    yield from bps.prepare(kinetix_flyer, kinetix_exp_setup, wait=True)
    yield from bps.prepare(kinetix_standard_det, kinetix_flyer.trigger_info, wait=True)

    yield from inner_kinetix_collect()

    yield from bps.unstage_all(kinetix_flyer, kinetix_standard_det)

    yield from bps.close_run()


def _kinetix_collect_dark_flat(num=10, exposure_time=0.1, software_trigger=True):

    kinetix_exp_setup = KinetixTriggerSetup(
        num_images=num, exposure_time=exposure_time, software_trigger=software_trigger
    )

    yield from bps.open_run()

    yield from bps.stage_all(kinetix_standard_det, kinetix_flyer)

    yield from bps.prepare(kinetix_flyer, kinetix_exp_setup, wait=True)
    yield from bps.prepare(kinetix_standard_det, kinetix_flyer.trigger_info, wait=True)

    yield from inner_kinetix_collect()

    yield from bps.unstage_all(kinetix_flyer, kinetix_standard_det)

    yield from bps.close_run()


file_loading_timer.stop_timer(__file__)
