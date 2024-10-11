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
from hextools.germ.ophyd import HEXGeRMDetectorHDF5
from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, Kind, Signal
from ophyd.sim import new_uid
from ophyd.status import SubscriptionStatus
from PIL import Image


# Intialize the GeRM detector ophyd object
germ_detector = HEXGeRMDetectorHDF5(
    "XF:27ID1-ES{GeRM-Det:1}",
    name="germ",
    root_dir="/nsls2/data/hex/proposals",
    md=RE.md,
    date_template="%Y"
)

germ_detector.frame_shape.kind = Kind.omitted

file_loading_timer.stop_timer(__file__)
