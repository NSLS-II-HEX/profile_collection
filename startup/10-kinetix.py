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
    SignalRW,
    TriggerInfo,
    TriggerLogic,
)
from ophyd_async.core import DeviceCollector
from ophyd_async.epics.adkinetix import KinetixDetector

kinetix_trigger_logic = StandardTriggerLogic()


def connect_to_kinetix(kinetix_id):

    print(f"Connecting to kinetix {kinetix_id}...")
    with DeviceCollector():
        kinetix_path_provider = ProposalNumYMDPathProvider(default_filename_provider)
        kinetix = KinetixDetector(
            f"XF:27ID1-BI{{Kinetix-Det:{kinetix_id}}}",
            kinetix_path_provider,
            name=f"kinetix-det{kinetix_id}",
        )

    print("Done.")

    return kinetix

try:
    kinetix1 = connect_to_kinetix(1)
except Exception as e:
    print(f"Kinetix 1 is unavailable...")

try:
    kinetix3 = connect_to_kinetix(3)
except Exception as e:
    print(f"Kinetix 3 is unavailable...")

#sd.baseline.append(kinetix1.drv.acquire_time)
#RE.preprocessors.append(sd)


# TODO: add as a new component into ophyd-async.
# kinetix_hdf_status = EpicsSignalRO(
#     "XF:27ID1-BI{Kinetix-Det:1}HDF1:WriteFile_RBV",
#     name="kinetix_hdf_status",
#     string=True,
# )


kinetix_flyer = StandardFlyer(
    kinetix_trigger_logic, [], name="kinetix_flyer"
)


def kinetix_stage(kinetix_detector):
    yield from bps.stage(kinetix_detector)
    yield from bps.sleep(5)


def inner_kinetix_collect(kinetix_detector):

    yield from bps.kickoff(kinetix_flyer)
    yield from bps.kickoff(kinetix_detector)

    yield from bps.complete(kinetix_flyer, wait=True, group="complete")
    yield from bps.complete(kinetix_detector, wait=True, group="complete")

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

        detector_stream_name = f"{kinetix_detector.name}_{kinetix_detector._writer._path_provider._filename_provider._frame_type.value}_stream"
        yield from bps.declare_stream(kinetix_detector, name=detector_stream_name)

        yield from bps.collect(
            kinetix_detector,
            # stream=True,
            # return_payload=False,
            name=detector_stream_name,
        )
        yield from bps.sleep(0.01)

    yield from bps.wait(group="complete")
    val = yield from bps.rd(kinetix_detector._writer.hdf.num_captured)
    print(f"{val = }")


def kinetix_collect(kinetix_detector, num=10, exposure_time=0.1, software_trigger=True):

    kinetix_exp_setup = StandardTriggerSetup(
        num_frames=num, exposure_time=exposure_time, software_trigger=software_trigger
    )

    yield from bps.open_run()

    yield from bps.stage_all(kinetix_detector, kinetix_flyer)

    yield from bps.prepare(kinetix_flyer, kinetix_exp_setup, wait=True)
    yield from bps.prepare(kinetix_detector, kinetix_flyer.trigger_logic.trigger_info(kinetix_exp_setup), wait=True)

    yield from inner_kinetix_collect(kinetix_detector)

    yield from bps.unstage_all(kinetix_flyer, kinetix_detector)

    yield from bps.close_run()


def _kinetix_collect_dark_flat(
    kinetix_detector, num=10, exposure_time=0.1, software_trigger=True
):

    kinetix_exp_setup = StandardTriggerSetup(
        num_frames=num, exposure_time=exposure_time, software_trigger=software_trigger
    )

    yield from bps.open_run()

    yield from bps.stage_all(kinetix_detector, kinetix_flyer)

    yield from bps.prepare(kinetix_flyer, kinetix_exp_setup, wait=True)
    yield from bps.prepare(kinetix_detector, kinetix_flyer.trigger_logic.trigger_info(kinetix_exp_setup), wait=True)

    yield from inner_kinetix_collect(kinetix_detector)

    yield from bps.unstage_all(kinetix_flyer, kinetix_detector)

    yield from bps.close_run()


file_loading_timer.stop_timer(__file__)
