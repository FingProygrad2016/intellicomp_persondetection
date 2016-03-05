from datetime import timedelta
import numpy as np
from enum import Enum

from utils.tools import diff_in_milliseconds


class SpeedEventTypes(Enum):
    STOPPED = "STOPPED"
    WALKING = "WALKING"
    RUNNING = "RUNNING"


class DirectionEventTypes(Enum):
    ROTATION = "ROTATION"


class EventInfoType(Enum):
    TIME = "TIME"
    ANGLE = "ANGLE"


class Quantifiers(Enum):
    LE = "LE"  # LE = Lower or equal
    GE = "GE"  # GE = Greater or equal
    AX = "AX"  # AX = Approximate
    EQ = "EQ"  # EQ = Equal
    NM = "NM"  # NM = No matter


class Event(object):

    def __init__(self, quantifier, value, time_end, duration,
                 aprox_tolerance=1500):
        self.AP_TOLERANCE = aprox_tolerance
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
                return np.isclose(self.value, event_rule.value,
                                  atol=self.AP_TOLERANCE)
            elif event_rule.quantifier == Quantifiers.EQ:
                return self.value == event_rule.value
            elif event_rule.quantifier == Quantifiers.NM:
                return True

        return False


class EventSpeed(Event):
    def __init__(self, type, quantifier, value, time_end=None, duration=0,
                 aprox_tolerance=1500):
        self.type = type
        self.info_type = EventInfoType.TIME
        super(EventSpeed, self).__init__(quantifier, value, time_end, duration)

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type, self.info_type, super(EventSpeed, self).__repr__())


class EventDirection(Event):
    def __init__(self, type, quantifier, value, time_end=None, duration=0,
                 aprox_tolerance=1500):
        self.type = DirectionEventTypes.ROTATION
        self.info_type = EventInfoType.ANGLE
        super(EventDirection, self).__init__(quantifier, value, time_end,
                                             duration)

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type, self.info_type, super(EventDirection, self).__repr__())
