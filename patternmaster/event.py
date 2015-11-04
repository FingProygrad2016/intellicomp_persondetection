from datetime import timedelta
import numpy as np

from utils.tools import diff_in_milliseconds, enum

SpeedEventTypes = enum(STOPPED="STOPPED", WALKING="WALKING", RUNNING="RUNNING")
DirectionEventTypes = enum(ROTATION="ROTATION")


EVENT_INFO_TYPE = enum(TIME="TIME", ANGLE="ANGLE")


"""
LE = Lower or equal
GE = Greater or equal
AX = Approximate
EQ = Equal
NM = No matter
"""
Quantifiers = enum(LE="LE", GE="GE", AX="AX", EQ="EQ", NM="NM")


class Event(object):

    def __init__(self, quantifier, value, time_end, duration):
        self.quantifier = quantifier
        self.value = value
        if time_end:
            self.time_start = time_end - timedelta(milliseconds=duration)
        else:
            self.time_start = None
        if time_end:
            self.last_update = time_end
        else:
            self.last_update = None

    def __repr__(self):
        return "%s TO %s TIME_START: %s DURATION: %s" % \
               (self.quantifier, str(self.value), self.time_start,
                diff_in_milliseconds(self.time_start, self.last_update))

    @property
    def duration(self):
        return diff_in_milliseconds(self.time_start, self.last_update)

    def satisfies(self, event_rule):
        if self.type == event_rule.type and \
                self.info_type == event_rule.info_type:
            if event_rule.quantifier == Quantifiers.LE:
                return self.value <= event_rule.value
            elif event_rule.quantifier == Quantifiers.GE:
                return self.value >= event_rule.value
            elif event_rule.quantifier == Quantifiers.AX:
                from patternmaster.pattern_recognition import AP_TOLERANCE
                return np.isclose(self.value, event_rule.value,
                                  atol=AP_TOLERANCE)
            elif event_rule.quantifier == Quantifiers.EQ:
                return self.value == event_rule.value
            elif event_rule.quantifier == Quantifiers.NM:
                return True

        return False


class EventSpeed(Event):
    def __init__(self, type, quantifier, value, time_end=None, duration=0):
        self.type = type
        self.info_type = EVENT_INFO_TYPE.TIME
        super(EventSpeed, self).__init__(quantifier, value, time_end, duration)

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type, self.info_type, super(EventSpeed, self).__repr__())


class EventDirection(Event):
    def __init__(self, type, quantifier, value, time_end=None, duration=0):
        self.type = DirectionEventTypes.ROTATION
        self.info_type = EVENT_INFO_TYPE.ANGLE
        super(EventDirection, self).__init__(quantifier, value, time_end,
                                             duration)

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type, self.info_type, super(EventDirection, self).__repr__())
