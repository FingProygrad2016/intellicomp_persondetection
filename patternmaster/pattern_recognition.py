from datetime import datetime, timedelta
import json

import numpy as np

from utils.communicator import Communicator
from utils.tools import enum, euclidean_distance, diff_in_milliseconds

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
AP_TOLERANCE = 1500


class Rule(object):
    def __init__(self, id, name, events):
        self.id = id
        self.name = name
        self.events = events  # Collection of events

    def __repr__(self):
        return "RULE: %s" % self.name

    def to_json(self):
        return {
            'name': self.name
        }


class Event(object):
    def __init__(self, quantifier, value, time_end, duration):
        self.quantifier = quantifier
        self.value = value
        if time_end:
            self.time_start = time_end - timedelta(microseconds=duration*1000)
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

    def satisfies(self, event_rule):
        if self.type == event_rule.type and \
                self.info_type == event_rule.info_type:
            if event_rule.quantifier == Quantifiers.LE:
                return self.value <= event_rule.value
            elif event_rule.quantifier == Quantifiers.GE:
                return self.value >= event_rule.value
            elif event_rule.quantifier == Quantifiers.AX:
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


class Tracklet(object):
    def __init__(self, identifier):
        self.id = identifier
        self.active_speed_events = []
        self.active_direction_events = []
        self.potential_movement_change_rules_to_reach = []
        self.last_position = None
        self.last_position_time = 0
        self.average_direction = None

    def add_new_events(self, new_events):
        """
        Add new events to the events collections. Zip themes if is necessary.
        :param new_events:
        :return:
        """
        for event in new_events:
            if isinstance(event, EventSpeed):
                if self.active_speed_events and \
                        self.active_speed_events[-1].type == event.type and \
                        self.active_speed_events[-1].info_type == \
                        event.info_type:
                    self.active_speed_events[-1].value += event.value
                    self.active_speed_events[-1].last_update = event.last_update
                else:
                    self.active_speed_events.append(event)
            elif isinstance(event, EventDirection):
                self.active_direction_events.append(event)


class PatternRecognition(object):

    MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION = 15
    WEIGHT_FOR_NEW_DIRECTION_ANGLE = 0.2
    MIN_DIRECTION_ANGLE_CHANGE_TO_FIRE_ALARM = 120
    MIN_SPEED_FOR_WALKING = 2
    MIN_SPEED_FOR_RUNNING = 12
    QUANTIFIER_APPROXIMATION = 2

    movement_change_rules = [
        # Rule(1, "walk_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.AX, 5000),
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000)
        #      ]),
        # Rule(2, "walk_stop_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 5000),
        #          EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.AX, 2000),
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 5000)
        #      ]),
        # Rule(2, "run_rotate_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000),
        #          EventDirection(DirectionEventTypes.ROTATION,
        #                         Quantifiers.AX, 120),
        #          # EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000)
        #      ]),
        Rule(3, "WALKING",
             events=[
                 EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 500)
             ]),
        Rule(3, "RUNNING",
             events=[
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 1500)
             ]),
        Rule(3, "STOPPED",
             events=[
                 EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.GE, 500)
             ]),
        # Rule(3, "tired_runner",
        #      events=[
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 3000),
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 2000)
        #      ])
    ]

    def __init__(self, min_angle_to_consider_rotation=90, min_walking_speed=10,
                 min_running_speed=120):
        self.tracklets_info = {}  # Collection of Tracklets
        self.MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION = \
            min_angle_to_consider_rotation
        self.MIN_SPEED_FOR_WALKING = min_walking_speed
        self.MIN_SPEED_FOR_RUNNING = min_running_speed
        self.communicator = Communicator(queue_name='warnings',
                                         expiration_time=60)

    def apply(self, tracklet_raw_info):
        """
        This method is executed every time that data arrives from the first
        phase with new tracking information.
        :param tracklet_raw_info:
        :return:
        """
        trackled_id = tracklet_raw_info['id']
        tracklet_info = self.tracklets_info.get(trackled_id, None)

        if not tracklet_info:
            # It's a new tracklet ;)
            self.tracklets_info[trackled_id] = Tracklet(trackled_id)
            self.tracklets_info[trackled_id].last_position = \
                tracklet_raw_info['last_position']
            last_update_datetime = \
                datetime.strptime(tracklet_raw_info['last_update_timestamp'],
                                  "%Y-%m-%dT%H:%M:%S.%f")
            self.tracklets_info[trackled_id].last_position_time = \
                last_update_datetime

        else:
            last_update_datetime = \
                datetime.strptime(tracklet_raw_info['last_update_timestamp'],
                                  "%Y-%m-%dT%H:%M:%S.%f")
            time_lapse, distance, angle = self.calc_movements_info(
                tracklet_info, tracklet_raw_info['last_position'],
                last_update_datetime)

            if time_lapse > 0:

                # Process looking for new events
                current_events = \
                    self.calc_events(tracklet_info, last_update_datetime,
                                     time_lapse, distance, angle)

                # Add found events to the current tracklet
                tracklet_info.add_new_events(current_events)

                # Update the last_updated_time for the current tracklet
                tracklet_info.last_position_time = last_update_datetime

                # Considering the new events and the recent events' history,
                # check if any rule matches
                found_rules = \
                    self.calc_rules(tracklet_info)

                # if found_rules:
                #     self.fire_alarms(tracklet_info, found_rules)

                # ####    DEBUG PURPOUSE    #### #
                # for event in current_events:
                #     print "EVENT:", event, "TRACKLET ID:", trackled_id
                if found_rules:
                    self.communicator.apply(
                        json.dumps({'rules': [r.name for r in found_rules],
                                    'position':
                                        tracklet_info.last_position,
                                    'id': tracklet_info.id}))

                    for rule in found_rules:
                        print ("::" + str(rule), "TRACKLET ID:", trackled_id)

    def calc_movements_info(self, tracklet_info, new_position,
                            new_position_time):
        time = diff_in_milliseconds(
            tracklet_info.last_position_time, new_position_time)

        (distance, angle) = self.calc_distance_and_angle_between_points(
            tracklet_info.last_position, new_position)

        return time, distance, angle

    @staticmethod
    def calc_distance_and_angle_between_points(point1, point2):

        distance = euclidean_distance(point1, point2)

        # sin(angle) = opposite / hypotenuse
        # FIXME: Ver si existe alternativa en Numpy (+ eficiente)
        if distance:
            sin_of_angle = abs(point2[1] - point1[1]) / distance

            angle = np.degrees(np.arcsin(sin_of_angle))
        else:
            angle = None

        return distance, angle

    def calc_events(self, tracklet_info, last_update, time_lapse,
                    distance, angle):

        current_events = self.calc_direction_events(tracklet_info, angle,
                                                    last_update, time_lapse)
        current_events.extend(self.calc_speed_events(distance, last_update,
                                                     time_lapse))

        return current_events

    def calc_direction_events(self, tracklet_info, angle, last_update,
                              time_lapse):
        current_events = []

        if not tracklet_info.average_direction:
            tracklet_info.average_direction = angle
        else:
            # calculate the difference between actual direction angle and new
            # direction angle
            min_diff_signed = tracklet_info.average_direction - angle
            min_diff_signed = (min_diff_signed + 180) % 360 - 180
            min_diff = abs(min_diff_signed)

            if min_diff > self.MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION:
                # Append ROTATION event
                current_events.append(EventDirection(EVENT_INFO_TYPE.ANGLE,
                                                     Quantifiers.AX,
                                                     round(min_diff),
                                                     time_end=last_update,
                                                     duration=time_lapse))

            # new direction is added to average_direction, but with less
            # weight to reduce noise
            tracklet_info.average_direction += \
                min_diff_signed * self.WEIGHT_FOR_NEW_DIRECTION_ANGLE

        return current_events

    def calc_speed_events(self, distance, last_update, time_lapse):
        current_events = []

        speed = distance / (time_lapse / 1000.0)  # Pixels per milliseconds??o.O

        if speed < self.MIN_SPEED_FOR_WALKING:
            # Append 'STOPPED' event
            current_events.append(EventSpeed(SpeedEventTypes.STOPPED,
                                             Quantifiers.EQ, time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))
        elif speed < self.MIN_SPEED_FOR_RUNNING:
            # Append 'WALKING' event
            current_events.append(EventSpeed(SpeedEventTypes.WALKING,
                                             Quantifiers.EQ, time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))
        else:
            # Append 'RUNNING' event
            current_events.append(EventSpeed(SpeedEventTypes.RUNNING,
                                             Quantifiers.EQ, time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))

        return current_events

    def calc_rules(self, tracklet_info):
        found_rules = []

        # MIN_EVENTS_SPEED_AMOUNT = 6
        # MIN_EVENTS_SPEED_TIME = 30000  # In milliseconds
        # MIN_EVENTS_DIR_AMOUNT = 2
        # MIN_EVENTS_DIR_TIME = 30000  # In milliseconds
        MIN_EVENTS_SPEED_AMOUNT = 1
        MIN_EVENTS_SPEED_TIME = 0  # In milliseconds
        MIN_EVENTS_DIR_AMOUNT = 1
        MIN_EVENTS_DIR_TIME = 0  # In milliseconds

        last_speed_events = []
        last_dir_events = []

        for event in reversed(tracklet_info.active_speed_events):
            if diff_in_milliseconds(
                    event.last_update, tracklet_info.last_position_time) < \
                    MIN_EVENTS_SPEED_TIME or \
                    len(last_speed_events) < MIN_EVENTS_SPEED_AMOUNT:
                last_speed_events.insert(0, event)
            else:
                break

        for event in reversed(tracklet_info.active_direction_events):
            if diff_in_milliseconds(
                    event.last_update, tracklet_info.last_position_time) < \
                    MIN_EVENTS_DIR_TIME or \
                    len(last_dir_events) < MIN_EVENTS_DIR_AMOUNT:
                last_dir_events.insert(0, event)
            else:
                break

        print ("last_speed_events", last_speed_events, "last_dir_events", last_dir_events)

        # if any matches, then the rule is added to found_rules
        for rule in self.movement_change_rules:
            if self.check_events_in_activeevents(
                    rule.events, last_speed_events) and \
                    self.check_events_in_activeevents(
                        rule.events, last_dir_events):
                found_rules.append(rule)

        return found_rules

    @staticmethod
    def check_events_in_activeevents(rule_events, last_events):
        if not last_events:
            return True
        last_events_iter = iter(last_events)
        try:
            for rule_event in rule_events:
                while not next(last_events_iter).satisfies(rule_event):
                    pass
            else:
                return True
        except StopIteration:
            pass

        return False

    def fire_alarms(self, tracklet_info, fired_rules):
        # TODO: fire alarms
        return len(fired_rules)
