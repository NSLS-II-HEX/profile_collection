def display_run_angles(scan_num = -1):
    angles = c.values()[-1]['panda1_stream']['external']['Angle'].read()
    print(f"{angles = }")
    