file_loading_timer.start_timer(__file__)

# Number of encoder counts for an entire revolution
COUNTS_PER_REVOLUTION = 72000
DEG_PER_REVOLUTION = 360
COUNTS_PER_DEG = COUNTS_PER_REVOLUTION / DEG_PER_REVOLUTION
ZERO_OFFSET = 39660

from ophyd_async.epics.adkinetix._kinetix_io import KinetixReadoutMode

DETECTOR_MAX_FRAMERATES = {
    KinetixReadoutMode.sensitivity: 80,
    KinetixReadoutMode.speed: 250,
    KinetixReadoutMode.dynamic_range: 75,
}


TOMO_ROTARY_STAGE_VELO_RESET_MAX = 30
TOMO_ROTARY_STAGE_VELO_SCAN_MAX = 60


def close_shutter():
    """Close the shutter after the scan."""
    yield from bps.mv(ph_shutter, "Close")


@bpp.finalize_decorator(close_shutter)
def take_dark_flat(
    exposure_time,
    offset,
    detector=None,
    dark_images=20,
    flat_images=50,
    use_shutter=True,
):

    if detector is None:
        detector = kinetix1

    if use_shutter:
        if (yield from bps.rd(fe_shutter_status)) != 1:
            raise RuntimeError(f"Front-end shutter is closed. Reopen it!")

    dark_flat_start_uuid = yield from bps.open_run()

    #### DARKS ####

    # Collect dark frames:
    if use_shutter:
        yield from bps.mv(ph_shutter, "Close")

    detector._writer._path_provider._filename_provider.set_frame_type(
        TomoFrameType.dark
    )

    yield from bps.stage_all(detector, kinetix_flyer)
    dark_setup  =        StandardTriggerSetup(
            num_frames=dark_images,
            exposure_time=exposure_time,
            software_trigger=True,
        )
    yield from bps.prepare(
        kinetix_flyer,
        dark_setup,
        wait=True,
    )
    yield from bps.prepare(detector, kinetix_flyer.trigger_logic.trigger_info(dark_setup), wait=True)

    yield from inner_kinetix_collect(detector)

    yield from bps.unstage_all(kinetix_flyer, detector)

    #### FLATS ####

    # Move sample out of the way:
    yield from bps.movr(sample_tower.axis_x1, offset)

    # Collect flat images:
    if use_shutter:
        yield from bps.mv(ph_shutter, "Open")
    yield from bps.sleep(2)

    detector._writer._path_provider._filename_provider.set_frame_type(
        TomoFrameType.flat
    )

    yield from bps.stage_all(detector, kinetix_flyer)

    flat_setup =         StandardTriggerSetup(
            num_frames=flat_images,
            exposure_time=exposure_time,
            software_trigger=True,
        )

    yield from bps.prepare(
        kinetix_flyer,
        flat_setup,
        wait=True,
    )
    yield from bps.prepare(detector, kinetix_flyer.trigger_logic.trigger_info(flat_setup), wait=True)

    yield from inner_kinetix_collect(detector)

    yield from bps.unstage_all(kinetix_flyer, detector)

    yield from bps.close_run()

    # Move sample back:
    yield from bps.movr(sample_tower.axis_x1, -offset)

    # Keep track of current dark/flat scan id here
    RE.md['current_dark_flat_scan_num'] = RE.md['scan_id']
    RE.md['current_dark_flat_scan_uid'] = dark_flat_start_uuid


def tomo_progress_bar(target, kinetix_detector):
    current = yield from bps.rd(kinetix_detector.writer.hdf.num_captured)

    toolbar_width = 100

    # setup toolbar
    sys.stdout.write("[%s]" % (" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

    sys.stdout.write("-" * int(toolbar_width * (target / current)))
    sys.stdout.flush()

    sys.stdout.write("]\n")


@bpp.finalize_decorator(close_shutter)
def tomo_flyscan(
    exposure_time,
    num_images,
    panda=None,
    detectors=None,
    time_trigger=True,
    scan_time=30,
    start_deg=0,
    stop_deg=180,
    lead_angle=10,
    reset_speed=TOMO_ROTARY_STAGE_VELO_RESET_MAX,
    use_shutter=True,
):
    """Simple hardware triggered flyscan tomography

    Parameters
    ----------
    exposure_time : float
        exposure time to use on the camera, in seconds
    num_images : int
        total number of camera images to collect during the scan
    scan_time : float (optional)
        time for the movement from start_deg to stop_deg degrees, in seconds.
    start_deg : float (optional)
        starting point in degrees
    stop_deg : float (optional)
        stopping point in degrees
    lead_angle : float (optional)
        the angle in degrees to be used to move motor to -lead_angle before 'start_deg' and +lead_angle after 'stop_deg'
    reset_speed : float
        speed of the rotary motor during reset movements, in deg/s
    use_shutter : bool
        whether to use/check the shutter during the scan
    """

    if panda is None:
        panda = panda1

    if detectors is None:
        detectors = [kinetix1]

    if use_shutter:
        if (yield from bps.rd(fe_shutter_status)) != 1:
            raise RuntimeError(f"\n    Front-end shutter is closed. Reopen it!\n")

        yield from bps.mv(ph_shutter, "Open")
        yield from bps.sleep(2)

    panda_detectors_and_flyers = [panda_flyer, panda]
    kinetix_detectors_and_flyers = [kinetix_flyer, *detectors]

    all_detectors = panda_detectors_and_flyers + kinetix_detectors_and_flyers

    panda_pcomp = dict(panda.pcomp.children())["1"]
    panda_pulser = dict(panda.pulse.children())["1"]

    mtr_reset_vel = reset_speed
    if mtr_reset_vel > TOMO_ROTARY_STAGE_VELO_RESET_MAX:
        mtr_reset_vel = TOMO_ROTARY_STAGE_VELO_RESET_MAX

    duration = scan_time
    rot_motor_vel = (stop_deg - start_deg) / scan_time
    if rot_motor_vel > TOMO_ROTARY_STAGE_VELO_SCAN_MAX:
        rot_motor_vel = TOMO_ROTARY_STAGE_VELO_SCAN_MAX
        duration = abs(stop_deg - start_deg) / rot_motor_vel

    step_time = duration / (num_images - 1)

    framerate = 1 / step_time

    for kinetix_det in detectors:
        det_readout_mode = yield from bps.rd(kinetix_det.drv.readout_port_idx)
        if framerate > DETECTOR_MAX_FRAMERATES[det_readout_mode]:
            step_time = 1 / DETECTOR_MAX_FRAMERATES[det_readout_mode]

    if exposure_time is not None:
        if exposure_time > step_time:
            raise RuntimeError(
                f"Your configured exposure time is longer than the time per step {step_time} seconds!"
            )

    # step_width_counts = COUNTS_PER_REVOLUTION / (
    #    (DEG_PER_REVOLUTION / (stop_deg - start_deg)) * (num_images - 1)
    # )
    # if int(step_width_counts) != round(step_width_counts, 5):
    #    raise ValueError(
    #        "The number of encoder counts per pulse is not an integer value!"
    #    )

    det_exp_setup = StandardTriggerSetup(
        num_frames=num_images,
        exposure_time=exposure_time,
        software_trigger=False,
    )

    # Make it fast to move to the start position:
    yield from bps.mv(tomo_rot_axis.velocity, reset_speed)
    yield from bps.mv(tomo_rot_axis, start_deg - lead_angle)
    # Set the velocity for the scan:
    yield from bps.mv(tomo_rot_axis.velocity, rot_motor_vel)
    start_encoder = start_deg * COUNTS_PER_DEG - ZERO_OFFSET

    # Set up the pcomp block
    yield from bps.mv(panda_pcomp.start, int(start_encoder))

    # Uncomment if using gate trigger mode on camera
    yield from bps.mv(
        panda_pcomp.width, 3  # step_width_counts - 1
    )  # Width in encoder counts that the pulse will be high
    # yield from bps.mv(panda1_pcomp_1.step, step_width_counts)
    if time_trigger:
        yield from bps.mv(panda_pcomp.pulses, 1)
        yield from bps.mv(panda_pulser.pulses, num_images)
        yield from bps.mv(panda_pulser.step, step_time)
        yield from bps.mv(panda_pulser.width, exposure_time / 5)
    else:
        yield from bps.mv(panda_pcomp.pulses, num_images)

    yield from bps.open_run()

    for kinetix_det in detectors:
        kinetix_det.writer._path_provider._filename_provider.set_frame_type(
            TomoFrameType.proj
        )

    # Stage All!
    yield from bps.stage_all(*all_detectors)

    # Set HDF plugin numcapture to num_images
    for kinetix_det in detectors:
        yield from bps.mv(kinetix_det.writer.hdf.num_capture, num_images)

    assert kinetix_flyer._trigger_logic.state == StandardTriggerState.stopping
    yield from bps.prepare(kinetix_flyer, det_exp_setup, wait=True)
    for kinetix_det in detectors:
        yield from bps.prepare(
            kinetix_det, kinetix_flyer.trigger_logic.trigger_info(det_exp_setup), wait=True
        )

    assert panda_flyer._trigger_logic.state == StandardTriggerState.stopping
    yield from bps.prepare(panda_flyer, det_exp_setup, wait=True)
    yield from bps.prepare(
        panda, panda_flyer.trigger_logic.trigger_info(num_images), wait=True
    )

    for flyer_or_det in all_detectors:
        yield from bps.kickoff(flyer_or_det)

    # Move rotation axis to the stop position + the lead angle:
    yield from bps.mv(tomo_rot_axis, stop_deg + lead_angle)

    print("Completing...")
    for flyer_or_det in all_detectors:
        yield from bps.complete(flyer_or_det, group="complete_all")

    # Wait for completion of file saving for the Kinetix detectors and the PandA
    done = False
    while not done:
        try:
            yield from bps.wait(group="complete_all", timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True

    panda_stream_name = f"{panda.name}_stream"
    yield from bps.declare_stream(panda, name=panda_stream_name)

    yield from bps.collect(
        panda,
        # stream=True,
        # return_payload=False,
        name=panda_stream_name,
    )

    yield from bps.unstage_all(*panda_detectors_and_flyers)

    if use_shutter:
        yield from close_shutter()

    for kinetix_det in detectors:
        detector_stream_name = f"{kinetix_det.name}_stream"
        yield from bps.declare_stream(kinetix_det, name=detector_stream_name)

        yield from bps.collect(
            kinetix_det,
            # stream=True,
            # return_payload=False,
            name=detector_stream_name,
        )
        yield from bps.sleep(0.01)

    yield from bps.unstage_all(*kinetix_detectors_and_flyers)

    yield from bps.close_run()


    # Print out number of points captured by each detector
    captured = {}
    captured[panda.name] = yield from bps.rd(panda.data.num_captured)
    for kinetix_det in detectors:
        captured[kinetix_det.name] = yield from bps.rd(kinetix_det.writer.hdf.num_captured)
    
    print("Number frames captured:\n")
    for cap in captured.keys():
        print(f"    {cap:15}: {captured[cap]}")

    # Reset the velocity back to high.
    yield from bps.mv(tomo_rot_axis.velocity, reset_speed)


def tomo_loop(number_of_repetitions,
    exposure_time,
    num_images,
    panda=None,
    detector=None,
    time_trigger=True,
    scan_time=30,
    start_deg=0,
    stop_deg=180,
    lead_angle=10,
    reset_speed=TOMO_ROTARY_STAGE_VELO_RESET_MAX,
    use_shutter=True,):

    for i in range(number_of_repetitions):
        print(f"Executing tomography iteration {i}...\n")
        
        yield from tomo_flyscan(
            exposure_time,
            num_images,
            panda=panda,
            detector=detector,
            time_trigger=time_trigger,
            scan_time=scan_time,
            start_deg=start_deg,
            stop_deg=stop_deg,
            lead_angle=lead_angle,
            reset_speed=reset_speed,
            use_shutter=use_shutter,
        )

        # Sleep to wait for file saving to complete
        yield from bps.sleep(50)


file_loading_timer.stop_timer(__file__)
