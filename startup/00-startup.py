# Begin loading HEX Profile Collection

print("Loading NSLS-II HEX profile collection...")

import asyncio
import datetime
import logging
import os
import subprocess
import time as ttime
import warnings
from pathlib import Path

import epicscorelibs.path.pyepics
import matplotlib.pyplot as plt
import nslsii
import ophyd.signal
import redis
from bluesky.callbacks.broker import post_run, verify_files_saved
from bluesky.callbacks.tiled_writer import TiledWriter
from bluesky.run_engine import RunEngine, call_in_bluesky_event_loop
from databroker.v0 import Broker
from IPython import get_ipython
from IPython.terminal.prompts import Prompts, Token
from nslsii import configure_base, configure_kafka_publisher
from ophyd.signal import EpicsSignalBase
from redis_json_dict import RedisJSONDict
from tiled.client import from_uri

# warnings.filterwarnings("ignore")

plt.ion()


class ProposalIDPrompt(Prompts):
    def in_prompt_tokens(self, cli=None):
        return [
            (
                Token.Prompt,
                f"{RE.md.get('data_session', 'N/A')} [",
            ),
            (Token.PromptNum, str(self.shell.execution_count)),
            (Token.Prompt, "]: "),
        ]


ip = get_ipython()
ip.prompts = ProposalIDPrompt(ip)


class FileLoadingTimer:

    def __init__(self):
        self.start_time = 0
        self.loading = False

    def start_timer(self, filename):
        if self.loading:
            raise Exception("File already loading!")

        print(f"Loading {filename}...")
        self.start_time = ttime.time()
        self.loading = True

    def stop_timer(self, filename):

        elapsed = ttime.time() - self.start_time
        print(f"Done loading {filename} in {elapsed:.6f} seconds.")
        self.loading = False


EpicsSignalBase.set_defaults(timeout=10, connection_timeout=10)

# The call below creates 'RE' and 'db' objects in the IPython user namespace.
# configure_base(get_ipython().user_ns,
#                "hex",
#                publish_documents_with_kafka=True,
#                pbar=True)

configure_base(
    get_ipython().user_ns,
    Broker.named("temp"),
    pbar=True,
    bec=True,
    magics=True,
    mpl=True,
    epics_context=False,
    publish_documents_with_kafka=False,
)

# event_loop = asyncio.get_event_loop()
# RE = RunEngine(loop=event_loop)
RE = RunEngine()
RE.subscribe(bec)
RE.preprocessors.append(sd)

tiled_writing_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/hex/raw",
    api_key=os.environ["TILED_BLUESKY_WRITING_API_KEY_HEX"],
)
tw = TiledWriter(tiled_writing_client)
RE.subscribe(tw)

c = tiled_reading_client = from_uri(
    "https://tiled.nsls2.bnl.gov/api/v1/metadata/hex/raw",
    include_data_sources=True,
)

def logout():
    """
    Logout of tiled and reset the default username.
    This is needed to switch between different users.
    """

    c.logout()

    from tiled.client.context import clear_default_identity
    clear_default_identity(c.context.api_uri)

# db = Broker(c)

import json


class JSONWriter:
    """Writer for a JSON array"""

    def __init__(self, filepath):
        self.file = open(filepath, "w")
        self.file.write("[\n")

    def __call__(self, name, doc):
        json.dump({"name": name, "doc": doc}, self.file, default=str)
        if name == "stop":
            self.file.write("\n]")
            self.file.close()
        else:
            self.file.write(",\n")


def now():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


jlw = JSONWriter(f"/tmp/export-docs-{now()}.json")


# wr = JSONWriter('/tmp/test.json')
# RE.subscribe(wr)

# RE.subscribe(print)

configure_kafka_publisher(RE, beamline_name="hex")

# This is needed for ophyd-async to enable 'await <>' instead of 'asyncio.run(<>)':
get_ipython().run_line_magic("autoawait", "call_in_bluesky_event_loop")

# PandA does not produce any data for plots for now.
bec.disable_plots()
bec.disable_table()
bec.disable_baseline()

runengine_metadata_dir = Path("/nsls2/data/hex/shared/config/runengine-metadata")

RE.md = RedisJSONDict(redis.Redis("info.hex.nsls2.bnl.gov", 6379), prefix="")


# Optional: set any metadata that rarely changes.
RE.md["facility"] = "NSLS-II"
RE.md["group"] = "HEX"
RE.md["beamline_id"] = "27-ID-1"


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
            print(
                f"\n  Warming up HDF5 plugin for {det.name} as the array_size={_array_size}..."
            )
            det.hdf5.warmup()
            print(
                f"  Warming up HDF5 plugin for {det.name} is done. array_size={det.hdf5.array_size.get()}\n"
            )
        else:
            print(
                f"\n  Warming up of the HDF5 plugin is not needed for {det.name} as the array_size={_array_size}."
            )


def show_env():
    # this is not guaranteed to work as you can start IPython without hacking
    # the path via activate
    proc = subprocess.Popen(["conda", "list"], stdout=subprocess.PIPE)
    out, err = proc.communicate()
    a = out.decode("utf-8")
    b = a.split("\n")
    print(b[0].split("/")[-1][:-1])

from ophyd_async.core import config_ophyd_async_logging
config_ophyd_async_logging()

def print_docs(name, doc):
    print("============================")
    print(f"{name = }")
    print(f"{doc = }")
    print("============================")


#RE.subscribe(print_docs)

def reset_scan_id(scan_id=0):
    """A fake plan to reset the scan_id via qserver."""
    yield from bps.null()
    print(f"Scan_id before: {RE.md['scan_id']}")
    RE.md["scan_id"] = scan_id
    print(f"Scan_id after: {RE.md['scan_id']}")


file_loading_timer = FileLoadingTimer()
