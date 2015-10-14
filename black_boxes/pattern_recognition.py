from datetime import datetime, timedelta
import numpy as np

from tools import enum, euclidean_distance

SpeedEventTypes = enum(STOPPED="STOPPED", WALKING="WALKING", RUNNING="RUNNING")
DirectionEventTypes = enum(ROTATION="ROTATION")

# FIXME: Borrarme, soy lo mismo que se define arriba como enumerado
movement_events = [{'type': 1, 'events': ['stopped', 'walking', 'running']},
                   {'type': 2, 'events': ['rotation']}]

EVENT_INFO_TYPE = enum(TIME="TIME", ANGLE="ANGLE")

# FIXME: Borrarme, soy lo mismo que se define arriba como enumerado
event_info_type = ('time', 'angle')

"""
LE = Lower or equal
GE = Greater or equal
AX = Approximate
EQ = Equal
NM = No matter
"""
Quantifiers = enum(LE="LE", GE="GE", AX="AX", EQ="EQ", NM="NM")


class Rule(object):
    def __init__(self, id, name, events):
        self.id = id
        self.name = name
        self.events = events  # Collection of events


class Event(object):
    def __init__(self, quantifier, value):
        self.quantifier = quantifier
        self.value = value

    def __repr__(self):
        return "QUANTIFIER: %s VALUE: %s" % (str(self.value), self.quantifier)


class EventSpeed(Event):
    def __init__(self, type, quantifier, value):
        self.type = type
        self.info_type = EVENT_INFO_TYPE.TIME
        super(EventSpeed, self).__init__(quantifier, value)

    def __repr__(self):
        return \
            "TYPE: %s INFO_TYPE: %s %s" % \
            (self.type, self.info_type, super(EventSpeed, self).__repr__())


class EventDirection(Event):
    def __init__(self, type, quantifier, value):
        self.type = DirectionEventTypes.ROTATION
        self.info_type = EVENT_INFO_TYPE.ANGLE
        super(EventDirection, self).__init__(quantifier, value)

    def __repr__(self):
        return \
            "TYPE: %s INFO_TYPE: %s %s" % \
            (self.type, self.info_type, super(EventDirection, self).__repr__())


class Tracklet(object):
    def __init__(self, id):
        self.id = id
        self.active_events = []
        self.potential_movement_change_rules_to_reach = []
        self.last_position = None
        self.last_position_time = 0
        self.average_direction = None


class PatternRecognition(object):

    MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION = 15
    WEIGHT_FOR_NEW_DIRECTION_ANGLE = 0.2
    MIN_DIRECTION_ANGLE_CHANGE_TO_FIRE_ALARM = 120
    MIN_SPEED_FOR_WALKING = 2
    MIN_SPEED_FOR_RUNNING = 12
    QUANTIFIER_APPROXIMATION = 2

    movement_change_rules = [
        Rule(1, "walk_run",
             events=[
                 EventSpeed(SpeedEventTypes.WALKING, Quantifiers.AX, 5),
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5)
             ]),
        Rule(2, "walk_stop_run",
             events=[
                 EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 5),
                 EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.AX, 2),
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 5)
             ]),
        Rule(2, "run_rotate_run",
             events=[
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5),
                 EventDirection(DirectionEventTypes.ROTATION,
                                Quantifiers.AX, 120),
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5)
             ])
    ]

    def __init__(self, min_angle_to_consider_rotation=90, min_walking_speed=2,
                 min_running_speed=12):
        self.tracklets_info = {}  # Collection of Tracklets
        self.MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION = \
            min_angle_to_consider_rotation
        self.MIN_SPEED_FOR_WALKING = min_walking_speed
        self.MIN_SPEED_FOR_RUNNING = min_running_speed

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

            (time, distance, angle) = self.calc_movements_info(
                tracklet_info, tracklet_raw_info['last_position'],
                last_update_datetime)

            # print "TIME:", time, "DISTANCE:", distance, "ANGLE:", angle

            if time > timedelta(seconds=0):
                current_events = \
                    self.calc_events(tracklet_info, time, distance, angle)
            #     fired_rules = \
            #         self.calc_rules(tracklet_info, time, current_events)
            #
            #     if len(fired_rules) > 0:
            #         self.fire_alarms(tracklet_info, fired_rules)
                for event in current_events:
                    print event

                # TODO!! FROM THIS POINT
                # self.add_event_description(tracklet_id, current_events)

        # TODO: verify rules and fire alarms

    def calc_movements_info(self, tracklet_info, new_position,
                            new_position_time):
        time = new_position_time - tracklet_info.last_position_time

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

    def calc_events(self, tracklet_info, time, distance, angle):

        current_events = []
        current_events.extend(self.calc_direction_events(tracklet_info, angle))
        # current_events.extend(self.calc_speed_events(distance, time))
        return current_events

    def calc_direction_events(self, tracklet_info, angle):
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
                                                     Quantifiers.AX, min_diff))

            # new direction is added to average_direction, but with less
            # weight to reduce noise
            tracklet_info.average_direction += \
                min_diff_signed * self.WEIGHT_FOR_NEW_DIRECTION_ANGLE

        return current_events

    def calc_speed_events(self, distance, time):
        current_events = []

        speed = distance / time

        if speed < self.MIN_SPEED_FOR_WALKING:
            current_events.append(
                {'event_type': 1, 'event_id': 1, 'event_info': [{'type_id': 1, 'value': time}]}
            )  # append 'stopped' event
        elif speed < self.MIN_SPEED_FOR_RUNNING:
            current_events.append(
                {'event_type': 1, 'event_id': 2, 'event_info': [{'type_id': 1, 'value': time}]}
            )  # append 'walking' event
        else:
            current_events.append(
                {'event_type': 1, 'event_id': 3, 'event_info': [{'type_id': 1, 'value': time}]}
            )  # append 'running' event

        return current_events

    def calc_rules(self, tracklet_info, time, current_events):
        fired_rules = []

        for event in current_events:
            active_event = tracklet_info.active_events[event.event_type - 1]

            if active_event.event_id != -1:
                if active_event.event_id != event.event_id:
                    # the current event is different from the active event
                    # ==> active event has finished
                    # ==> verify rules

                    # TODO: verify current potential rules to reach
                    # TODO: remove any rule which actual step does not match the current event
                    # TODO: cuidado: puede haber lio en las reglas con steps de velocidad y otros de angulo

                    # first step of rules is verified against the finished event
                    # if any matches, then the rule is added
                    for rule in self.movement_change_rules:
                        first_step = rule['steps'][0]

                        if self.verify_step_accomplishment(first_step, active_event):
                            # finished event matches first rule's step
                            # ==> rule is added to list

                            # TODO: add rule to the list
                            a = 0

                else:
                    # the current event is the same as the active event
                    # ==> current event's time is added to the one of the active event
                    # TODO: add time to the active event
                    a = 0

        # TODO

        return fired_rules

    def verify_step_accomplishment(self, step, event):
        verified = False

        if step['event_type'] == event['event_type']:
            if step['event_id'] == event['event_id']:
                step_info = step['event_info']
                event_info = event['event_info']
                still_valid = True
                for s_info in step_info:
                    if still_valid:
                        for e_info in event_info:
                            if s_info['type_id'] == e_info['type_id']:
                                quantifier = s_info['quantifier_id']
                                if quantifier == 1:
                                    # less or equal than
                                    if e_info['value'] > s_info['value']:
                                        still_valid = False
                                elif quantifier == 2:
                                    # more or equal than
                                    if e_info['value'] < s_info['value']:
                                        still_valid = False
                                elif quantifier == 3:
                                    # approximately
                                    condition1 = e_info['value'] > s_info['value'] + self.QUANTIFIER_APPROXIMATION
                                    condition2 = e_info['value'] < s_info['value'] - self.QUANTIFIER_APPROXIMATION
                                    if condition1 or condition2:
                                        still_valid = False
                if still_valid:
                    verified = True
        return verified

    def fire_alarms(self, tracklet_info, fired_rules):
        # TODO: fire alarms
        return len(fired_rules)

    # def add_event_description(self, tracklet_id, event, time):
    # TODO: if last saved event is the same as the new one,
    # TODO: sum 'time' to the one of the last saved event description object;
    # TODO: else, add a new event description, with the new event and time.
