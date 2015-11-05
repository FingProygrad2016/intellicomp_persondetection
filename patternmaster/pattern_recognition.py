from datetime import datetime
import json

import numpy as np

from patternmaster.event import EventDirection, EventSpeed, EVENT_INFO_TYPE, \
    Quantifiers, SpeedEventTypes
from patternmaster.rule import load_system_rules
from patternmaster.tracklet import Tracklet
from utils.communicator import Communicator
from utils.tools import euclidean_distance, diff_in_milliseconds


AP_TOLERANCE = 1500


class PatternRecognition(object):

    MIN_ANGLE_CHANGE_CONSIDER_AS_ROTATION = 15
    WEIGHT_FOR_NEW_DIRECTION_ANGLE = 0.2
    MIN_DIRECTION_ANGLE_CHANGE_TO_FIRE_ALARM = 120
    MIN_SPEED_FOR_WALKING = 2
    MIN_SPEED_FOR_RUNNING = 12
    QUANTIFIER_APPROXIMATION = 2

    movement_change_rules = load_system_rules()

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
            # It's a new tracklet ;) we need to create a Tracklet instance

            self.tracklets_info[trackled_id] = Tracklet(trackled_id)
            self.tracklets_info[trackled_id].last_position = \
                tracklet_raw_info['last_position']
            last_update_datetime = \
                datetime.strptime(tracklet_raw_info['last_update_timestamp'],
                                  "%Y-%m-%dT%H:%M:%S.%f")
            self.tracklets_info[trackled_id].last_position_time = \
                last_update_datetime

        else:
            # It's new data to an existent Tracklet info

            last_update_datetime = \
                datetime.strptime(tracklet_raw_info['last_update_timestamp'],
                                  "%Y-%m-%dT%H:%M:%S.%f")
            time_lapse, distance, angle = self.calc_movements_info(
                tracklet_info, tracklet_raw_info['last_position'],
                last_update_datetime)

            if time_lapse > 0:
                # If there a time lapse to process

                # Look for new events
                current_events = \
                    self.calc_events(tracklet_info, last_update_datetime,
                                     time_lapse, distance, angle)

                # Add found events to the current tracklet
                tracklet_info.add_new_events(current_events)

                # Update the last_updated_time for the current tracklet
                tracklet_info.last_position_time = last_update_datetime

                # Considering the new events and the recent events' history,
                # check if any rule matches
                found_rules = self.calc_rules(tracklet_info)

                # If Rules were matched, warn about it
                if found_rules:
                    self.fire_alarms(tracklet_info, found_rules)

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
        """

        :param tracklet_info:
        :return: a list of tuples with the distance and the rule that was
        satisfied
        """
        found_rules = []

        MIN_EVENTS_SPEED_AMOUNT = 6
        MIN_EVENTS_SPEED_TIME = 30000  # In milliseconds
        MIN_EVENTS_DIR_AMOUNT = 2
        MIN_EVENTS_DIR_TIME = 30000  # In milliseconds

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

        print("last_speed_events", last_speed_events, "last_dir_events",
              last_dir_events)

        # if any matches, then the rule is added to found_rules
        for rule in self.movement_change_rules:
            satisfies_speed_events, dist1 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, last_speed_events)
            satisfies_dir_events, dist2 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, last_dir_events)

            if satisfies_speed_events and satisfies_dir_events:
                found_rules.append((dist1 + dist2, rule))

        return found_rules

    @staticmethod
    def check_ruleevents_in_activeevents(rule_events, last_events):
        """
        Checks if the sequence of rule's events are contained in last_events,
        in the same order as defined in the rule.
        BE CAREFUL: Same order doesn't mean contiguously. Non contiguously
        rule's events will have a distance greater than zero.
        :param rule_events:
        :param last_events:
        :return:
        """
        if not last_events:
            return True, 0
        firsts = True
        last_events_iter = iter(reversed(last_events))
        try:
            distance = 0
            for pos, rule_event in enumerate(reversed(rule_events)):
                if pos > 0:
                    firsts = False
                last_event = next(last_events_iter)
                while not last_event.satisfies(rule_event):
                    if not firsts:
                        distance += last_event.duration
                    last_event = next(last_events_iter)
            else:
                return True, distance
        except StopIteration:
            pass

        return False, None

    def fire_alarms(self, tracklet_info, found_rules):

        self.communicator.apply(
            json.dumps({'rules': [(r[0], r[1].name) for r in found_rules],
                        'position':
                            tracklet_info.last_position,
                        'id': tracklet_info.id}))

        for rule in found_rules:
            print ("::" + str(rule), "TRACKLET ID:", tracklet_info.id)
