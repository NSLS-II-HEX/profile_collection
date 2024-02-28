

# Begin loading HEX Profile Collection

print('Loading NSLS-II HEX profile collection...')

import time

from nslsii import configure_base
from ophyd.signal import EpicsSignalBase

import logging
import os
from pathlib import Path

from bluesky.utils import PersistentDict
from IPython import get_ipython

import matplotlib.pyplot as plt
plt.ion()


class FileLoadingTimer:

    def __init__(self):
        self.start_time = 0
        self.loading = False


    def start_timer(self, filename):
        if self.loading:
            raise Exception('File already loading!')

        print(f'Loading {filename}...')
        self.start_time = time.time()
        self.loading = True


    def stop_timer(self, filename):

        elapsed = time.time() - self.start_time
        print(f'Done loading {filename} in {elapsed} seconds.')
        self.loading = False


EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)

# The call below creates 'RE' and 'db' objects in the IPython user namespace.
configure_base(get_ipython().user_ns,
               "hex",
               publish_documents_with_kafka=True,
               pbar=True)

runengine_metadata_dir = Path("/nsls2/data/hex/shared/config/runengine-metadata")

# PersistentDict will create the directory if it does not exist
RE.md = PersistentDict(runengine_metadata_dir)


# Optional: set any metadata that rarely changes.
RE.md["beamline_id"] = "HEX"


def warmup_hdf5_plugins(detectors):
    """
    Warm-up the hdf5 plugins.
    This is necessary for when the corresponding IOC restarts we have to trigger one image
    for the hdf5 plugin to work correctly, else we get file writing errors.
    Parameter:
    ----------
    detectors: list
    """
    for det in detectors:
        _array_size = det.hdf5.array_size.get()
        if 0 in [_array_size.height, _array_size.width] and hasattr(det, "hdf5"):
            print(f"\n  Warming up HDF5 plugin for {det.name} as the array_size={_array_size}...")
            det.hdf5.warmup()
            print(f"  Warming up HDF5 plugin for {det.name} is done. array_size={det.hdf5.array_size.get()}\n")
        else:
            print(f"\n  Warming up of the HDF5 plugin is not needed for {det.name} as the array_size={_array_size}.")



file_loading_timer = FileLoadingTimer()
