from datetime import datetime
import json

import numpy as np

from patternmaster.event import EventDirection, EventSpeed, EventInfoType, \
    Quantifiers, SpeedEventTypes
from patternmaster.rule import load_system_rules
from patternmaster.tracklet import Tracklet
from utils.communicator import Communicator
from utils.tools import euclidean_distance, diff_in_milliseconds
from patternmaster.config import CustomConfig, read_conf


class PatternRecognition(object):

    def __init__(self, identifier, custom_config=None):
        self.tracklets_info = {}  # Collection of Tracklets
        self.identifier = identifier
        self.config = CustomConfig(custom_config) if custom_config \
            else read_conf()

        self.movement_change_rules = load_system_rules(self.config)

        self.min_angle_rotation = self.config.getint('MIN_ANGLE_ROTATION')
        self.min_walking_speed = self.config.getint('MIN_WALKING_SPEED')
        self.min_running_speed = self.config.getint('MIN_RUNNING_SPEED')
        self.WEIGHT_FOR_NEW_DIRECTION_ANGLE = \
            self.config.getfloat('WEIGHT_NEW_DIRECTION_ANGLE')
        self.MIN_EVENTS_SPEED_AMOUNT = \
            self.config.getint('MIN_EVENTS_SPEED_AMOUNT')
        self.MIN_EVENTS_SPEED_TIME = self.config.getint('MIN_EVENTS_SPEED_TIME')
        self.MIN_EVENTS_DIR_AMOUNT = self.config.getint('MIN_EVENTS_DIR_AMOUNT')
        self.MIN_EVENTS_DIR_TIME = self.config.getint('MIN_EVENTS_DIR_TIME')

        self.communicator = \
            Communicator(
                expiration_time=self.config.getint('WARNINGS_EXPIRATION_TIME'),
                host_address=self.config.get('WARNINGS_QUEUE_HOSTADDRESS'),
                exchange='to_master', exchange_type='topic')

    def set_config(self, data):
        self.config = CustomConfig(data) if data \
            else read_conf()

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
                tracklet_info.last_position = tracklet_raw_info['last_position']

                # Considering the new events and the recent events' history,
                # check if any rule matches
                found_rules = self.calc_rules(tracklet_info)

                # If Rules were matched, warn about it
                if [x[1] for x in tracklet_info.last_found_rules] != \
                        [x[1] for x in found_rules]:
                    if found_rules:
                        found_rules.sort(key=lambda x: x[2], reverse=True)
                        tracklet_info.last_found_rules = found_rules
                        tracklet_info.last_time_found_rules = last_update_datetime
                        tracklet_info.img = tracklet_raw_info['img']
                        self.fire_alarms(tracklet_info)

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
        current_events.extend(
            self.calc_speed_events(distance, last_update, time_lapse))

        return current_events

    def calc_direction_events(self, tracklet_info, angle, last_update,
                              time_lapse):
        current_events = []

        if not tracklet_info.average_direction:
            tracklet_info.average_direction = angle
        else:
            # calculate the difference between actual direction angle and new
            # direction angle
            if angle:
                min_diff_signed = tracklet_info.average_direction - angle
            else:
                min_diff_signed = 0
            min_diff_signed = (min_diff_signed + 180) % 360 - 180
            min_diff = abs(min_diff_signed)

            if min_diff > self.min_angle_rotation:
                # Append ROTATION event
                current_events.append(EventDirection(EventInfoType.ANGLE,
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

        speed = distance / (time_lapse / 1000.0)  # Measure in Pixels/Second

        if speed < self.min_walking_speed:
            # Append 'STOPPED' event
            current_events.append(EventSpeed(SpeedEventTypes.STOPPED,
                                             Quantifiers.EQ, time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))
        elif speed < self.min_running_speed:
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
        :return: a list of tuples with:
             0- The distance (trust measurement)
             1- The rule that was satisfied
             2- The time that the rule has taken
        satisfied
        """
        found_rules = []

        last_speed_events = []
        last_dir_events = []

        for event in reversed(tracklet_info.active_speed_events):
            if diff_in_milliseconds(
                    event.last_update, tracklet_info.last_position_time) < \
                    self.MIN_EVENTS_SPEED_TIME or \
                    len(last_speed_events) < self.MIN_EVENTS_SPEED_AMOUNT:
                last_speed_events.insert(0, event)
            else:
                break

        for event in reversed(tracklet_info.active_direction_events):
            if diff_in_milliseconds(
                    event.last_update, tracklet_info.last_position_time) < \
                    self.MIN_EVENTS_DIR_TIME or \
                    len(last_dir_events) < self.MIN_EVENTS_DIR_AMOUNT:
                last_dir_events.insert(0, event)
            else:
                break

        # if any matches, then the rule is added to found_rules
        for rule in self.movement_change_rules:
            satisfies_speed_events, dist1, time_from_start1= \
                self.check_ruleevents_in_activeevents(
                    rule.events, last_speed_events)
            satisfies_dir_events, dist2, time_from_start2 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, last_dir_events)

            if satisfies_speed_events or satisfies_dir_events:
                found_rules.append((dist1 + dist2, rule,
                                    min(time_from_start1, time_from_start2)))

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
            return False, 0, 9999999999
        firsts = True
        last_events_iter = iter(reversed(last_events))
        try:
            distance = 0
            time_from_start = 0
            for pos, rule_event in enumerate(reversed(rule_events)):
                if pos > 0:
                    firsts = False
                last_event = next(last_events_iter)
                while not last_event.satisfies(rule_event):
                    if not firsts:
                        distance += last_event.duration
                    else:
                        time_from_start += last_event.duration
                    last_event = next(last_events_iter)
            else:
                return True, distance, time_from_start
        except StopIteration:
            pass

        # FIXME: si no hay eventos de tal tipo en la rule, la distancia no
        # deberia ser cero ya que del otro tipo puede cuplir
        return False, 0, 9999999999

    def fire_alarms(self, tracklet_info):

        self.communicator.apply(
            json.dumps({'tracker_id': self.identifier,
                        'rules': [(r[0], r[1].name) for r in
                                  tracklet_info.last_found_rules],
                        'position':
                            tracklet_info.last_position,
                        'id': tracklet_info.id,
                        'img': tracklet_info.img,
                        'timestamp': str(tracklet_info.last_time_found_rules)}),
            routing_key='warnings')
