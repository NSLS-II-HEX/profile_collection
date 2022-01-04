file_loading_timer.start_timer(__file__)


# Some of the code below is from
# https://github.com/NSLS-II-HXN/hxntools/blob/master/hxntools/detectors
# and
# https://github.com/NSLS-II-XPD/profile_collection



from ophyd import (AreaDetector, 
                                ImagePlugin,
                                TIFFPlugin, 
                                StatsPlugin, 
                                ProcessPlugin, 
                                ROIPlugin, 
                                TransformPlugin,
                                OverlayPlugin,
                                CamBase,
                                SimDetector,
                                PvcamDetector,
                                PvcamDetectorCam,
                                Device,
                                HDF5Plugin,
                                Component as Cpt,
                                EpicsSignalWithRBV)

from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite,
                                                 FileStoreTIFFSquashing,
                                                 FileStoreIterativeWrite, new_short_uid,
                                                 FileStoreTIFF,
                                                 FileStoreBase)


from ophyd import Component

from ophyd import Signal, EpicsSignal, EpicsSignalRO
from nslsii.ad33 import SingleTriggerV33, StatsPluginV33
from ophyd.areadetector import (EpicsSignalWithRBV as SignalWithRBV)

from ophyd.device import BlueskyInterface
from ophyd.device import DeviceStatus


from enum import Enum

class HEXDetectorMode(Enum):
    step = 1
    fly = 2


class HEXTIFFPlugin(TIFFPlugin,FileStoreIterativeWrite, Device):
    pass


class ContinuousAcquisitionTrigger(BlueskyInterface):
    """
    This trigger mixin class records images when it is triggered.
    It expects the detector to *already* be acquiring, continously.
    """
    def __init__(self, *args, plugin_name=None, image_name=None, **kwargs):
        if plugin_name is None:
            raise ValueError("plugin name is a required keyword argument")
        super().__init__(*args, **kwargs)
        self._plugin = getattr(self, plugin_name)
        if image_name is None:
            image_name = '_'.join([self.name, 'image'])
        self._plugin.stage_sigs[self._plugin.auto_save] = 'No'
        
        #self.cam.stage_sigs[self.cam.image_mode] = 'Continuous'
        # MT: For Emergent to work
        self.cam.stage_sigs['image_mode'] = 'Continuous'
        self.cam.stage_sigs['acquire'] = 1        
        
        self._plugin.stage_sigs[self._plugin.file_write_mode] = 'Capture'
        self._image_name = image_name
        self._status = None
        self._num_captured_signal = self._plugin.num_captured
        self._num_captured_signal.subscribe(self._num_captured_changed)
        self._save_started = False

    def stage(self):
        
        if self.cam.acquire.get() != 1:
            raise RuntimeError("The ContinuousAcuqisitionTrigger expects "
                               "the detector to already be acquiring.")   
        return super().stage()


    def trigger(self):
        "Trigger one acquisition."
        if not self._staged:
            raise RuntimeError("This detector is not ready to trigger."
                               "Call the stage() method before triggering.")
        self._save_started = False
        self._status = DeviceStatus(self)
        self._desired_number_of_sets = self.number_of_sets.get()
        self._plugin.num_capture.put(self._desired_number_of_sets)
        self.dispatch(self._image_name, ttime.time())
        # reset the proc buffer, this needs to be generalized
        self.proc.reset_filter.put(1)
        self._plugin.capture.put(1)  # Now the TIFF plugin is capturing.
        return self._status

    def _num_captured_changed(self, value=None, old_value=None, **kwargs):
        "This is called when the 'acquire' signal changes."
        if self._status is None:
            return
        if value == self._desired_number_of_sets:
            # This is run on a thread, so exceptions might pass silently.
            # Print and reraise so they are at least noticed.
            try:
                self.tiff.write_file.put(1)
            except Exception as e:
                print(e)
                raise
            self._save_started = True
        if value == 0 and self._save_started:
            self._status._finished()
            self._status = None
            self._save_started = False


class HEXSimDetector(SingleTriggerV33, SimDetector):

    tiff = Cpt(HEXTIFFPlugin, 'TIFF1:',
             write_path_template='/a/b/c/',
             read_path_template='/a/b/c',
             read_attrs=[],
             root=DATA_ROOT)


class KinetixDetectorCam(PvcamDetectorCam):

    wait_for_plugins = Cpt(EpicsSignal, 'WaitForPlugins',
                           string=True, kind='config')

    def __init__(self, *args, **kwargs):
        super().__init(*args, **kwargs)

        self.stage_sigs['wait_for_plugins'] = 'Yes'

    def ensure_nonblocking(self):
        self.stage_sigs['wait_for_plugins'] = 'Yes'
        for c in self.parent.component_names:
            cpt = getattr(self.parent, c)
            if cpt is self:
                continue
            if hasattr(cpt, 'ensure_nonblocking'):
#                 print(f'cpt: {cpt.name}')
                cpt.ensure_nonblocking()


class HEXKinetix(PvcamDetector):
    image = Cpt(ImagePlugin, 'image1:')

    tiff = Cpt(HEXTIFFPlugin, 'TIFF1:',
             write_path_template='/a/b/c/',
             read_path_template='/a/b/c',
             read_attrs=[],
             root=DATA_ROOT)


    proc = Cpt(ProcessPlugin, 'Proc1:')

    # These attributes together replace `num_images`. They control
    # summing images before they are stored by the detector (a.k.a. "tiff
    # squashing").
    images_per_set = Cpt(Signal, value=1, add_prefix=())
    number_of_sets = Cpt(Signal, value=1, add_prefix=())

    pixel_size = Cpt(Signal, value=.000005, kind='config') #unknown
    detector_type = Cpt(Signal, value='Emergent', kind='config')
    stats1 = Cpt(StatsPluginV33, 'Stats1:', kind = 'hinted')
    #stats2 = Cpt(StatsPluginV33, 'Stats2:')
    #stats3 = Cpt(StatsPluginV33, 'Stats3:')
    #stats4 = Cpt(StatsPluginV33, 'Stats4:')
    #stats5 = Cpt(StatsPluginV33, 'Stats5:', kind = 'hinted')

    roi1 = Cpt(ROIPlugin, 'ROI1:')
    #roi2 = Cpt(ROIPlugin, 'ROI2:')
    #roi3 = Cpt(ROIPlugin, 'ROI3:')
    #roi4 = Cpt(ROIPlugin, 'ROI4:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs.update([(self.cam.trigger_mode, 'Internal')])
        self.stage_sigs.update([(self.cam.data_type, 'UInt16')])
        self.stage_sigs.update([(self.cam.color_mode, 'Mono')])


class KinetixContinuous(ContinuousAcquisitionTrigger, HEXKinetix):
    pass



def initialize_hex_detector(detector_type, detector_name, pv_prefix, read_path_template=None, write_path_template=None):
    """General function meant to simplify initializing ophyd objects for individual detectors

    Parameters
    ----------
    detector_type : ophyd.areadetector.detectors.AreaDetector
        [description]
    detector_name : [type]
        [description]
    pv_prefix : [type]
        [description]
    read_path_template : [type], optional
        [description], by default None
    write_path_template : [type], optional
        [description], by default None

    Returns
    -------
    [type]
        [description]
    """

    #try:
    # Intialize object instance of specified detector type, along with tiff plugin
    print(f'Initializing {detector_name.upper()} detector...')
    detector_obj = detector_type(pv_prefix, name=detector_name)

    # Adjust read/write path templates for tiff plugin if specified
    if read_path_template is not None:
        detector_obj.tiff.read_path_template = read_path_template
    else:
        detector_obj.tiff.read_path_template = f'{DATA_ROOT}/{detector_obj.name}_data/%Y/%m/%d/'

    if write_path_template is not None:
        detector_obj.tiff.write_path_template = write_path_template
    else:
        detector_obj.tiff.write_path_template = f'{DATA_ROOT}/{detector_obj.name}_data/%Y/%m/%d/'

    # Make sure the detector is non-blocking
    #detector_obj.cam.ensure_nonblocking()

    return detector_obj
    #except Exception as exc:
    #    print(exc)
    #    print(f'\nUnable to initiate {detector_name.upper()} camera. Is it connected, with a running IOC?')
    #    pass


sim_detector = initialize_hex_detector(HEXSimDetector, 'cam-sim1', '13SIM1:')


file_loading_timer.stop_timer(__file__)