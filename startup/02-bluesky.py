file_loading_timer.start_timer(__file__)

import os
import nslsii
from bluesky.plans import count

from bluesky.utils import PersistentDict
from bluesky import RunEngine

# See docstring for nslsii.configure_base() for more details
#nslsii.configure_base(get_ipython().user_ns,'xpdd', pbar=False, bec=True,
#                      magics=True, mpl=True, epics_context=False)

# db.reg.set_root_map({'/direct/XF28ID1':'/direct/XF28ID2'})

# At the end of every run, verify that files were saved and
# print a confirmation message.
# from bluesky.callbacks.broker import verify_files_saved, post_run
# RE.subscribe(post_run(verify_files_saved, db),'stop')

# Uncomment the following lines to turn on verbose messages for
# debugging.
# import logging
# ophyd.logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


directory = os.path.expanduser("~/.config/bluesky/md")
os.makedirs(directory, exist_ok=True)
md = PersistentDict(directory)

RE = RunEngine(md)
RE.md['facility'] = 'NSLS-II'
RE.md['group'] = 'HEX'
RE.md['beamline_id'] = '27-ID'


file_loading_timer.stop_timer(__file__)