file_loading_timer.start_timer(__file__)

"""
Ophyd objects for motors

"""

from ophyd import Component as Cpt
from ophyd import Device, EpicsMotor, EpicsSignalRO, Kind


class EpicsMotorWithDescription(EpicsMotor):
    """Based on the Misc. chapter at https://epics.anl.gov/EpicsDocumentation/AppDevManuals/RecordRef/Recordref-6.html."""

    desc = Cpt(EpicsSignalRO, ".DESC", kind=Kind.config)


class SampleTower(Device):
    """
    Ophyd objects for the sample-tower motors (<-> CSS names):
    """

    # Define a list of objects corresponding to motors of the sample tower

    axis_x1 = Cpt(EpicsMotorWithDescription, "X1}Mtr")
    axis_z1 = Cpt(EpicsMotorWithDescription, "Z1}Mtr")
    pitch = Cpt(EpicsMotorWithDescription, "Rx}Mtr")
    vertical_y = Cpt(EpicsMotorWithDescription, "Y}Mtr")
    roll = Cpt(EpicsMotorWithDescription, "Rz}Mtr")

    x2 = Cpt(EpicsMotorWithDescription, "X2}Mtr")
    z2 = Cpt(EpicsMotorWithDescription, "Z2}Mtr")

    rx1 = Cpt(EpicsMotorWithDescription, "Rx1}Mtr")
    ry1 = Cpt(EpicsMotorWithDescription, "Ry1}Mtr")
    rz1 = Cpt(EpicsMotorWithDescription, "Rz1}Mtr")

    def get_motor_list(self):
        motor_list = []
        for name in self.read_attrs:
            if "." not in name:
                motor_list.append(name)
        return motor_list

    def get_position(self, motor_name):
        try:
            motor = getattr(self, motor_name)
            return motor.read()[motor.name]["value"]
        except AttributeError:
            return "No such motor name: {}!".format(motor_name)

    def get_velocity(self, motor_name):
        try:
            motor = getattr(self, motor_name)
            return motor.velocity.value
        except AttributeError:
            return "No such motor name: {}!".format(motor_name)

    def get_acceleration(self, motor_name):
        try:
            motor = getattr(self, motor_name)
            return motor.acceleration.value
        except AttributeError:
            return "No such motor name: {}!".format(motor_name)

    def get_css_name(self, motor_name):
        try:
            motor = getattr(self, motor_name)
            css_name = motor.desc.get()
            return css_name
        except AttributeError:
            return "No such motor name: {}!".format(motor_name)


class HEXMonochromator(Device):
    xtal2_z = Cpt(EpicsMotor, "Z2}Mtr")


mono = HEXMonochromator("XF:27IDA-OP:1{Mono:DCLM-Ax:", name="mono")
sample_tower = SampleTower("XF:27IDF-OP:1{SMPL:1-Ax:", name="sample_tower")


class TomoRotaryStageHoming(Device):

    home_cmd = Cpt(EpicsSignal, "Start:Home-Cmd")
    home_status = Cpt(EpicsSignal, "Sts:HomeCmplt-Sts")

    def set(self, value):
        def wait_for_home_done(value, old_value, **kwargs):
            print(f"Current homing status: {value}, last homing status: {old_value}")
            if old_value != 1 and value == 1:
                return True
            else:
                return False
        
        status = SubscriptionStatus(self.home_status, run=False, callback=wait_for_home_done)
        self.home_cmd.put(value)
        
        return status


class TomoRotaryStage(Device):
    rotary_axis = Cpt(EpicsMotorWithDescription, "Ax:4}Mtr")
    home = Cpt(TomoRotaryStageHoming, "Ax:4}")




tomo_rotary_stage = TomoRotaryStage("XF:27IDF-OP:1{MC:5-", name="tomo_rotary_stage")
tomo_rot_axis = tomo_rotary_stage.rotary_axis


class MotorValuesMCA1(Device):
    fltr1u = Cpt(EpicsSignalRO, "1{Fltr:1-Ax:Yu}Mtr.RBV", kind=Kind.normal)
    fltr1d = Cpt(EpicsSignalRO, "1{Fltr:1-Ax:Yd}Mtr.RBV", kind=Kind.normal)
    fltr2 = Cpt(EpicsSignalRO, "1{Fltr:2-Ax:Y}Mtr.RBV", kind=Kind.normal)
    fltr3 = Cpt(EpicsSignalRO, "3{Fltr:3-Ax:Y}Mtr.RBV", kind=Kind.normal)
    sliti = Cpt(EpicsSignalRO, "1{Slt:1-Ax:I}Mtr.RBV", kind=Kind.normal)
    slito = Cpt(EpicsSignalRO, "1{Slt:1-Ax:O}Mtr.RBV", kind=Kind.normal)
    slitb = Cpt(EpicsSignalRO, "1{Slt:1-Ax:B}Mtr.RBV", kind=Kind.normal)
    slitt = Cpt(EpicsSignalRO, "1{Slt:1-Ax:T}Mtr.RBV", kind=Kind.normal)


"""
MCA1_MOTORS = [
    "XF:27IDA-OP:1{Slt:1-Ax:HG}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:HC}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:VG}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:VC}Mtr.RBV",
    "XF:27IDA-OP:1{Fltr:1-Ax:Yu}Mtr.RBV",
    "XF:27IDA-OP:1{Fltr:1-Ax:Yd}Mtr.RBV",
    "XF:27IDA-OP:1{Fltr:2-Ax:Y}Mtr.RBV",
    "XF:27IDA-OP:3{Fltr:3-Ax:Y}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:I}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:O}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:B}Mtr.RBV",
    "XF:27IDA-OP:1{Slt:1-Ax:T}Mtr.RBV"]

MCA2_MOTORS = [
    "XF:27IDA-OP:2{Fltr:4-Ax:Y}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:Z2}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:Z2RBK}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:ZC}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:P}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1A}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1B}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2A}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2B}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1Bend}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1Twist}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2Bend}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2Twist}Mtr.RBV"]


MCA3_MOTORS = [
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2R}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1Y}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C1P}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:C2P}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:BS}Mtr.RBV",
    "XF:27IDA-OP:1{Mono:DCLM-Ax:FS}Mtr.RBV"
    ]


MCF1_MOTORS = [
    "XF:27IDF-OP:1{Slt:2-Ax:HG}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:HC}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:VG}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:VC}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:I}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:O}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:B}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:2-Ax:T}Mtr.RBV",
    "XF:27IDF-OP:1{MC:1-Ax:7}Mtr.RBV",
    "XF:27IDF-OP:1{MC:1-Ax:8}Mtr.RBV"]

MCF2_MOTORS = [
    "XF:27IDF-OP:1{OPT:1-Ax:X2}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Y2}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Rx3}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Ry3}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:X3}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Y3}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Ry4}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:X4}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:A1}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Z0}Mtr.RBV",
    "XF:27IDF-OP:1{MC:1-Ax:7}Mtr.RBV",
    "XF:27IDF-OP:1{MC:1-Ax:8}Mtr.RBV"]

MCF3_MOTORS = [
    "XF:27IDF-OP:1{SHLD:1-Ax:X}Mtr.RBV",
    "XF:27IDF-OP:1{SHLD:1-Ax:Vx}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:A1}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Z0}Mtr.RBV"]

MCF4_MOTORS = [
    "XF:27IDF-OP:1{SMPL:1-Ax:Rx}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:Y}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:Rz}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:X1}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:Z1}Mtr.RBV",    
    "XF:27IDF-OP:1{SMPL:1-Ax:Y1}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:Y2}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:Y3}Mtr.RBV"]

MCF5_MOTORS = [
    "XF:27IDF-OP:1{SMPL:1-Ax:Z2}Mtr.RBV",
    "XF:27IDF-OP:1{SMPL:1-Ax:X2}Mtr.RBV",
    "XF:27IDF-OP:1{MC:5-Ax:4}Mtr.RBV",    
    "XF:27IDF-OP:1{EDXD:1-Ax:X}Mtr.RBV",
    "XF:27IDF-OP:1{EDXD:1-Ax:Y}Mtr.RBV",
    "XF:27IDF-OP:1{EDXD:1-Ax:Z}Mtr.RBV",
    "XF:27IDF-OP:1{EDXD:1-Ax:Rx}Mtr.RBV"]

MCF6_MOTORS = [
    "XF:27IDF-OP:1{Slt:CMT-Ax:I}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:CMT-Ax:O}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:CMT-Ax:B}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:CMT-Ax:T}Mtr.RBV",
    "XF:27IDF-OP:1{CMT:1-Ax:X}Mtr.RBV",
    "XF:27IDF-OP:1{CMT:1-Ax:Yc}Mtr.RBV",
    "XF:27IDF-OP:1{CMT:1-Ax:Yf}Mtr.RBV",
    "XF:27IDF-OP:1{Slt:CMT-Ax:Pitch}Mtr.RBV"]

MCF7_MOTORS = [
    "XF:27IDF-OP:1{IMG:1-Ax:X}Mtr.RBV",
    "XF:27IDF-OP:1{IMG:1-Ax:Y}Mtr.RBV",
    "XF:27IDF-OP:1{IMG:1-Ax:Z}Mtr.RBV",
    "XF:27IDF-OP:1{DIFF:1-Ax:X}Mtr.RBV",
    "XF:27IDF-OP:1{DIFF:1-Ax:Y}Mtr.RBV",
    "XF:27IDF-OP:1{DIFF:1-Ax:Z}Mtr.RBV",
    "XF:27IDF-OP:1{SHLD:1-Ax:PHx}Mtr.RBV",
    "XF:27IDF-OP:1{SHLD:1-Ax:PHy}Mtr.RBV"
    ]


MCF8_MOTORS = [
    "XF:27IDF-OP:1{OPT:1-Ax:CamRot}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:ObjSel}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Focus2}Mtr.RBV",
    "XF:27IDF-OP:1{OPT:1-Ax:Focus1}Mtr.VAL",
    "XF:27IDF-OP:1{OPT:2-Ax:Focus}Mtr.VAL",    
    "XF:27IDF-OP:1{OPT:2-Ax:CamRot}Mtr.VAL",
    "XF:27IDF-OP:1{SMPL:1-Ax:Ry1}Mtr.RBV"]


GERM_DETECTOR = {
    "count_time": "XF:27ID1-ES{GeRM-Det:1}.TP",
    "gain": "XF:27ID1-ES{GeRM-Det:1}.GAIN",
    "shaping_time": "XF:27ID1-ES{GeRM-Det:1}.SHPT",
    "hv_bias": "XF:27ID1-ES{GeRM-Det:1}:HV",
    "voltage": "XF:27ID1-ES{GeRM-Det:1}:HV_RBV"}
"""


mca1_motors = MotorValuesMCA1("XF:27IDA-OP:", name="mca1_motors", kind=Kind.normal)


class EDXD(Device):
    # XF:27IDF-OP:1{EDXD:1-Ax:X}Mtr.VAL
    axis_x = Cpt(EpicsMotorWithDescription, "X}Mtr")
    # XF:27IDF-OP:1{EDXD:1-Ax:Y}Mtr.VAL

    # XF:27IDF-OP:1{EDXD:1-Ax:Rx}Mtr.VAL
    axis_rx = Cpt(EpicsMotorWithDescription, "Rx}Mtr")


edxd = EDXD("XF:27IDF-OP:1{EDXD:1-Ax:", name="edxd")

theta = edxd.axis_rx

# sd (SuppelementalData) is an attribute of RE, defined in the nslsii.__init__().
sd.baseline += [getattr(mca1_motors, m) for m in mca1_motors.component_names]


fe_shutter_status = EpicsSignalRO(
    "XF:27IDA-PPS{Sh:FE}Sts:OpnCmd-Sts", name="fe_shutter_status", string=False
)
from nslsii.devices import TwoButtonShutter


class HEXTwoButtonShutter(TwoButtonShutter):

    RETRY_PERIOD = 3.0
    
    def stop(self, *, success=False):
        pass


ph_shutter = HEXTwoButtonShutter("XF:27IDA-PPS{L1-S1}", name="ph_shutter")

file_loading_timer.stop_timer(__file__)
