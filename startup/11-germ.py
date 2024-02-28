file_loading_timer.start_timer(__file__)

import datetime
import os
import uuid
from collections import deque
from enum import Enum
from pathlib import Path

import h5py
import numpy as np
from event_model import compose_resource
from hextools.germ.ophyd import GeRMDetectorHDF5
from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, Kind, Signal
from ophyd.sim import new_uid
from ophyd.status import SubscriptionStatus
from PIL import Image

# TODO: add Tiff support in Caproto IOC.

class HEXGeRMDetectorHDF5(GeRMDetectorHDF5):
    """HEX-specific ophyd class for GeRM detector producing HDF5 files."""

    def stop(self, *, success=False):
        # TODO: see why it's not called by RE on RE.stop()
        ret = super().stop(success=success)
        print("\n!!! Should stop now !!!\n")
        self.count.put("Done")
        return ret


# Intialize the GeRM detector ophyd object
# germ_detector = HEXGeRMDetectorHDF5("XF:27ID1-ES{GeRM-Det:1}", name="GeRM", root_dir="/nsls2/data/hex/assets/germ/")
germ_detector = HEXGeRMDetectorHDF5("XF:27ID1-ES{GeRM-Det:1}", name="GeRM", root_dir="/nsls2/data/hex/proposals/commissioning/pass-315258/raw_data/")




# TODO: rework the exporter based on Tiled.
# TODO 2: add motor positions.
def nx_export_callback(name, doc):
    print(f"Exporting the nx file at {datetime.datetime.now().isoformat()}")
    if name == "stop":
        run_start = doc["run_start"]
        # TODO: rewrite with SingleRunCache.
        hdr = db[run_start]
        for nn, dd in hdr.documents():
            if nn == "resource" and dd["spec"] == "AD_HDF5_GERM":
                resource_root = dd["root"]
                resource_path = dd["resource_path"]
                h5_filepath = os.path.join(resource_root, resource_path)
                # nx_filepath = f"{os.path.splitext(h5_filepath)[0]}.nxs"
                nx_filepath = os.path.join(
                    "/tmp",
                    f"{os.path.basename(os.path.splitext(h5_filepath)[0])}.nxs",
                )
                print(f"{nx_filepath = }")
                # TODO 1: prepare metadata
                # TODO 2: save .nxs file

                def get_dtype(value):
                    if isinstance(value, str):
                        return h5py.special_dtype(vlen=str)
                    elif isinstance(value, float):
                        return np.float32
                    elif isinstance(value, int):
                        return np.int32
                    else:
                        return type(value)

                with h5py.File(nx_filepath, 'w') as h5_file:
                    entry_grp = h5_file.require_group("entry")
                    data_grp = entry_grp.require_group("data")

                    meta_dict = get_detector_parameters()
                    for k, v in meta_dict.items():
                        meta = v
                        break
                    current_metadata_grp = h5_file.require_group("entry/instrument/detector")  # TODO: fix the location later.
                    for key, value in meta.items():
                        if key not in current_metadata_grp:
                            dtype = get_dtype(value)
                            current_metadata_grp.create_dataset(key, data=value, dtype=dtype)

                    # External link
                    data_grp["data"] = h5py.ExternalLink(h5_filepath, "entry/data/data")


# TODO: add detector params into exported .h5 via caproto IOC.
GERM_DETECTOR_KEYS = [
    "count_time",
    "gain",
    "shaping_time",
    "hv_bias",
    "voltage",
]

def get_detector_parameters(det=germ_detector, keys=GERM_DETECTOR_KEYS):
    group_key = f"{det.name.lower()}_detector"
    detector_metadata = {group_key : {}}
    for key in keys:
        obj = getattr(det, key)
        as_string = True if obj.enum_strs else False
        detector_metadata[group_key][key] = obj.get(as_string=as_string)
    return detector_metadata


# RE.subscribe(nx_export_callback, name="stop")


file_loading_timer.stop_timer(__file__)
