file_loading_timer.start_timer(__file__)


def example_plan(motor, list_of_positions):

#    for pos in list_of_positions:
#        yield from mv(motor, pos)
#        yield from count([germanium_detector])
    yield from bp.list_scan([germ_detector], motor, list_of_positions)

def example_plan_2():
    yield from example_plan()


def acquire_germ_detector(count_time, detector=None, num=1):
    if detector is None:
        detector = germ_detector
    yield from bps.mv(detector.count_time, count_time)
    uid = yield from bp.count([detector], num=num)
    return uid


def count_germ(count_time, num=1, detector=None, md=None):
    if detector is None:
        detector = germ_detector
    yield from bps.mv(detector.count_time, count_time)
    _md = md or {}
    _md.update({"tomo_scanning_mode": ScanType.edxd.value})
    uid = yield from bp.count([detector], num=num, md=_md)
    return uid


def sweep_motion(detector, count_time, motor, start, stop, max_moves=1000, md=None):
    # TODO: update the metadata to record motor/detector information.
    """
    From "RE(bp.scan([germ_detector], sample_tower.axis_z1, 7, 7.5, 5))":
    {'uid': 'ec41ecd1-1357-42e9-8959-6180fecf8375',
    'time': 1703101850.4261565,
    'beamline_id': 'HEX',
    'scan_id': 50,
    'plan_type': 'generator',
    'plan_name': 'scan',
    'detectors': ['GeRM'],
    'motors': ['sample_tower_axis_z1'],
    'num_points': 5,
    'num_intervals': 4,
    'plan_args': {'detectors': ["GeRMDetectorHDF5(prefix='XF:27ID1-ES{GeRM-Det:1}', name='GeRM', read_attrs=['image'], configuration_attrs=['number_of_channels', 'gain', 'shaping_time', 'count_time', 'auto_time', 'fast_data_filename', 'voltage', 'hv_bias'])"],
    'num': 5,
    'args': ["EpicsMotorWithDescription(prefix='XF:27IDF-OP:1{SMPL:1-Ax:Z1}Mtr', name='sample_tower_axis_z1', parent='sample_tower', settle_time=0.0, timeout=None, read_attrs=['user_readback', 'user_setpoint'], configuration_attrs=['user_offset', 'user_offset_dir', 'velocity', 'acceleration', 'motor_egu', 'desc'])",
    7,
    7.5],
    'per_step': 'None'},
    'hints': {'dimensions': [[['sample_tower_axis_z1'], 'primary']]},
    'plan_pattern': 'inner_product',
    'plan_pattern_module': 'bluesky.plan_patterns',
    'plan_pattern_args': {'num': 5,
    'args': ["EpicsMotorWithDescription(prefix='XF:27IDF-OP:1{SMPL:1-Ax:Z1}Mtr', name='sample_tower_axis_z1', parent='sample_tower', settle_time=0.0, timeout=None, read_attrs=['user_readback', 'user_setpoint'], configuration_attrs=['user_offset', 'user_offset_dir', 'velocity', 'acceleration', 'motor_egu', 'desc'])",
    7,
    7.5]}}
    """
    md = md or {}
    if "calibrant" not in md:
        raise KeyError("Please specify calibrant as a string")
    # if "export_dir" not in md:
    #     md["export_dir"] = (
    #         "/nsls2/data/hex/proposals/commissioning/pass-315258/exported_data"
    #     )
    init_pos = yield from bps.rd(motor)
    print(f"{init_pos = }")
    yield from bps.mv(motor, start)

    def check_if_done():
        status = detector.count.get(as_string=True)
        if status == "Done":
            return True
        else:
            return False

    _md = {
        "plan_args": {
            "count_time": count_time,
            "motor": motor.name,
            "start": start,
            "stop": stop,
            "max_moves": max_moves,
        },
        "theta": round(theta.user_readback.get(), 3),
        "tomo_scanning_mode": ScanType.edxd.value,

    }
    _md.update(md)

    @bpp.stage_decorator([detector])
    @bpp.run_decorator(md=_md)
    def inner():
        yield from bps.mv(detector.count_time, count_time)
        yield from bps.trigger(detector, wait=False, group="germ")

        counter = 0
        while True:
            if counter % 2 == 0:
                target = stop
            else:
                target = start

            yield from bps.mv(motor, target)
            if check_if_done():
                break

            counter += 1
            if counter >= max_moves:
                break

        # TODO: fix the interrupt
        yield from bps.wait(group="germ")
        yield from bps.create(name="primary")
        reading = yield from bps.read(detector)
        yield from bps.save()

        return reading

    def final_plan():
        yield from bps.mv(motor, init_pos)

    return (yield from bpp.finalize_wrapper(inner(), final_plan()))

file_loading_timer.stop_timer(__file__)
