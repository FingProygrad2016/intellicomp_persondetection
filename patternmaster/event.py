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
        self.type_ = None
        self.info_type = None
        if time_end:
            self.time_start = time_end - timedelta(milliseconds=duration)
        else:
            self.time_start = None
        if time_end:
            self.last_update = time_end
        else:
            self.last_update = None

    def __repr__(self):
        return "Event %s TO %s TIME_START: %s DURATION: %s" % \
               (self.quantifier, str(self.value), self.time_start,
                diff_in_milliseconds(self.time_start, self.last_update))

    @property
    def duration(self):
        if None in (self.time_start, self.last_update):
            return 0
        return diff_in_milliseconds(self.time_start, self.last_update)

    def satisfies(self, event_rule):
        if self.type_ == event_rule.type_ and \
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

    def is_glueable(self, event2):
        """
        Compare two events partially, It means that returns True when are
            equally enough to be glued to 'self'.
        :param event2: An event instance.

        :return: True/False
        """
        raise NotImplementedError()

    def glue(self, event2):
        """
        Glue event2 to 'self'. No matters which one was first, it handle it.
        :param event2: The second event.
        :return: Nothing.
        """
        self.time_start = min(self.time_start, event2.time_start)
        self.last_update = max(self.last_update, event2.last_update)
        self.value += event2.value


class EventSpeed(Event):

    def __init__(self, type_, quantifier, value, time_end=None, duration=0,
                 aprox_tolerance=1500):
        super(EventSpeed, self).__init__(quantifier, value, time_end, duration,
                                         aprox_tolerance)
        self.type_ = type_
        self.info_type = EventInfoType.TIME

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type_, self.info_type, super(EventSpeed, self).__repr__())

    def is_glueable(self, event2):
        return isinstance(event2, EventSpeed) and \
                self.type_ == event2.type_ and \
                self.info_type == event2.info_type

    def satisfies(self, event_rule):
        return isinstance(event_rule, EventSpeed) and \
               Event.satisfies(self, event_rule)


class EventDirection(Event):
    def __init__(self, type_, quantifier, value, time_end=None, duration=0,
                 aprox_tolerance=1500):
        super(EventDirection, self).__init__(quantifier, value, time_end,
                                             duration, aprox_tolerance)
        self.type_ = DirectionEventTypes.ROTATION
        self.info_type = EventInfoType.ANGLE

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type_, self.info_type, super(EventDirection, self).__repr__())

    def is_glueable(self, event2):
        return isinstance(event2, EventDirection) and \
               self.type_ == event2.type_ and \
               self.info_type == event2.info_type and \
               (self.last_update >= event2.time_start or
                self.time_start <= event2.last_update)

    def satisfies(self, event_rule):
        return isinstance(event_rule, EventDirection) and \
               Event.satisfies(self, event_rule)


class EventAgglomeration(Event):

    def __init__(self, type_=None, quantifier=Quantifiers.EQ, value=0,
                 time_end=None, duration=0, aprox_tolerance=1500):
        super(EventAgglomeration, self).__init__(quantifier, value, time_end,
                                                 duration, aprox_tolerance)
        self.type_ = type_
        self.notified = False

    def __repr__(self):
        return \
            "%s->%s %s" % \
            (self.type_, self.info_type,
             super(EventAgglomeration, self).__repr__())

    def is_glueable(self, event2):
        return isinstance(event2, EventAgglomeration) and \
               (self.last_update >= event2.time_start - timedelta(seconds=1) or
                self.time_start - timedelta(seconds=1) <=
                event2.last_update) and \
               self.type_ == event2.type_

    def satisfies(self, event_rule):
        return isinstance(event_rule, EventAgglomeration) and \
               event_rule.quantifier == Quantifiers.GE and \
               int(self.type_) >= int(event_rule.type_) and \
               int(self.value) >= int(event_rule.value)

    def glue(self, event2):
        """
        Glue event2 to 'self'. No matters which one was first, it handle it.
        :param event2: The second event.
        :return: Nothing.
        """
        Event.glue(self, event2)
        self.type_ = max(event2.type_, self.type_)
