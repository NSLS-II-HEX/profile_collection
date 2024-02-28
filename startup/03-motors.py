"""
Ophyd objects for motors

"""

from ophyd import EpicsMotor, Device
from ophyd import Component as Cpt, EpicsSignalRO
from ophyd import Kind


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
            return motor.read()[motor.name]['value']
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


class MotorValuesMCA1(Device):
    fltr1u = Cpt(EpicsSignalRO, "1{Fltr:1-Ax:Yu}Mtr.RBV", kind=Kind.normal)
    fltr1d = Cpt(EpicsSignalRO, "1{Fltr:1-Ax:Yd}Mtr.RBV", kind=Kind.normal)
    fltr2 = Cpt(EpicsSignalRO, "1{Fltr:2-Ax:Y}Mtr.RBV", kind=Kind.normal)
    fltr3 = Cpt(EpicsSignalRO, "3{Fltr:3-Ax:Y}Mtr.RBV", kind=Kind.normal)
    sliti = Cpt(EpicsSignalRO, "1{Slt:1-Ax:I}Mtr.RBV", kind=Kind.normal)
    slito = Cpt(EpicsSignalRO, "1{Slt:1-Ax:O}Mtr.RBV", kind=Kind.normal)
    slitb = Cpt(EpicsSignalRO, "1{Slt:1-Ax:B}Mtr.RBV", kind=Kind.normal)
    slitt = Cpt(EpicsSignalRO, "1{Slt:1-Ax:T}Mtr.RBV", kind=Kind.normal)


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
