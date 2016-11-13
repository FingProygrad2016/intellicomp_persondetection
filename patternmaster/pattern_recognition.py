from datetime import datetime
from sys import maxsize
import json
from itertools import dropwhile, takewhile

import numpy as np

from patternmaster.event import EventDirection, EventSpeed, EventInfoType, \
    Quantifiers, SpeedEventTypes, EventAgglomeration
from patternmaster.rule import load_system_rules
from patternmaster.tracklet import Tracklet
from utils.communicator import Communicator
from utils.tools import euclidean_distance, diff_in_milliseconds
from patternmaster.config import CustomConfig, read_conf


class PatternRecognition(object):

    def __init__(self, identifier, custom_config=None):
        self.globals_last_notification_datetime = datetime.now()
        self.globals_last_notification_number = 0
        self.tracklets_info = {}  # Collection of Tracklets
        self.identifier = identifier
        self.resolution_multiplier = 1
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
        self.MIN_EVENTS_SPEED_TIME = \
            self.config.getint('MIN_EVENTS_SPEED_TIME')
        self.MIN_EVENTS_DIR_AMOUNT = \
            self.config.getint('MIN_EVENTS_DIR_AMOUNT')
        self.MIN_EVENTS_DIR_TIME = self.config.getint('MIN_EVENTS_DIR_TIME')
        self.AGGLOMERATION_MIN_DISTANCE = \
            self.config.getint('AGGLOMERATION_MIN_DISTANCE')
        self.GLOBAL_EVENTS_LIVES_TIME = \
            self.config.getint('GLOBAL_EVENTS_LIVES_TIME')
        self.TRACKLETS_LIVES_TIME = self.config.getint('TRACKLETS_LIVES_TIME')

        self.communicator = \
            Communicator(
                expiration_time=self.config.getint('WARNINGS_EXPIRATION_TIME'),
                host_address=self.config.get('WARNINGS_COMM_HOSTADDRESS'),
                exchange=self.config.get('WARNINGS_EXCHANGE_NAME'),
                exchange_type='topic')

        self.global_events = []

    def set_config(self, data, resolution_mult):
        self.resolution_multiplier = resolution_mult
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

                last_position = tracklet_raw_info['last_position']

                # Look for new events
                current_local_events, current_global_events = \
                    self.calc_events(tracklet_info, last_update_datetime,
                                     time_lapse, distance, angle,
                                     last_position)

                # print("TRACKLET ID:: %s" % trackled_id)
                # print("LAST POSITION:: %s" % last_position)
                # print("LAST UPDATED DATETIME:: %s " % last_update_datetime)
                # print("DISTANCE/TIMELAPSE:: %s / %s" % (distance, time_lapse))
                # print("CURRENT EVENTS:: %s" % current_local_events)

                # Add found local events to the current tracklet
                tracklet_info.add_new_events(current_local_events)

                # Add found global events to the global information
                self.add_global_events(current_global_events)

                # Update the last_updated_time for the current tracklet
                tracklet_info.last_position_time = last_update_datetime
                tracklet_info.last_position = last_position

                # Considering the new events and the recent events' history,
                # check if any rule matches
                found_local_rules, found_global_rules = \
                    self.calc_rules(tracklet_info)

                for r in found_local_rules:
                    r[1].tracklet_owner = trackled_id

                # Update the last tracklet's image
                tracklet_info.img = tracklet_raw_info['img']

                # If Rules were matched, warn about it
                # TODO: Revisar validez de esta comparacion
                if [x[1] for x in tracklet_info.last_found_rules] != \
                        [x[1] for x in found_local_rules]:
                    if found_local_rules:
                        found_local_rules.sort(key=lambda x: x[2],
                                               reverse=True)
                        tracklet_info.last_found_rules = found_local_rules
                        tracklet_info.last_time_found_rules = \
                            last_update_datetime
                        self.fire_alarms(tracklet_info)

                if found_global_rules and self.global_events and \
                        not self.global_events[-1].notified and (
                        (last_update_datetime -
                         self.globals_last_notification_datetime).seconds >
                        5 or self.globals_last_notification_number <
                        self.global_events[-1].type_):
                    self.fire_global_alarms(found_global_rules, tracklet_info)

                # Remove abandoned tracklets from lists
                self.remove_abandoned_tracklets(last_update_datetime)
                # Remove old global events from list
                self.remove_old_global_events(last_update_datetime)

    def remove_abandoned_tracklets(self, last_update):
        tracklet_to_delete = \
            [t.id for t in self.tracklets_info.values()
             if diff_in_milliseconds(t.last_position_time, last_update) >
             self.TRACKLETS_LIVES_TIME]
        for id_ in tracklet_to_delete:
            del self.tracklets_info[id_]

    def remove_old_global_events(self, last_update):
        self.global_events = list(dropwhile(
            lambda e: diff_in_milliseconds(e.last_update, last_update) >
            self.GLOBAL_EVENTS_LIVES_TIME, self.global_events))

    def add_global_events(self, current_global_events):
        for event in current_global_events:
            if self.global_events and \
                    event.is_glueable(self.global_events[-1]):
                self.global_events[-1].glue(event)
            else:
                self.global_events.append(event)

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
        if distance:
            sin_of_angle = abs(point2[1] - point1[1]) / distance

            angle = np.degrees(np.arcsin(sin_of_angle))
        else:
            angle = None

        return distance, angle

    def calc_events(self, tracklet_info, last_update, time_lapse,
                    distance, angle, last_position):

        current_local_events = \
            self.calc_direction_events(tracklet_info, angle,
                                       last_update, time_lapse)
        current_local_events.extend(
            self.calc_speed_events(distance, last_update, time_lapse))

        current_global_event = \
            self.calc_global_events(last_update, last_position, time_lapse)

        return current_local_events, current_global_event

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
                                             Quantifiers.EQ, value=time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))
        elif speed < self.min_running_speed:
            # Append 'WALKING' event
            current_events.append(EventSpeed(SpeedEventTypes.WALKING,
                                             Quantifiers.EQ, value=time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))
        else:
            # Append 'RUNNING' event
            current_events.append(EventSpeed(SpeedEventTypes.RUNNING,
                                             Quantifiers.EQ, value=time_lapse,
                                             time_end=last_update,
                                             duration=time_lapse))

        return current_events

    def calc_global_events(self, last_update, last_position, time_lapse):
        counter = 0
        current_global_events = []

        # ## Look for AGGLOMERATION events ## #
        # Calculate distance to each tracklet and check if it is close enough
        for tracklet in self.tracklets_info.values():
            if diff_in_milliseconds(
                    tracklet.last_position_time, last_update) < 1250 and \
                euclidean_distance(last_position, tracklet.last_position) < \
                    self.AGGLOMERATION_MIN_DISTANCE:
                counter += 1
        else:
            if counter > 1:
                current_global_events.append(
                    EventAgglomeration(type_=counter, value=time_lapse,
                                       time_end=last_update,
                                       duration=time_lapse))

        # ## Place to verify future global events ## #
        # ... ... ...

        return current_global_events

    def calc_rules(self, tracklet_info):
        """

        :param tracklet_info:
        :return: a list of tuples with:
             0- The distance (trust measurement)
             1- The rule that was satisfied
             2- The time that the rule has taken
        satisfied
        """
        found_local_rules = []
        found_global_rules = []
        last_update = tracklet_info.last_position_time

        # Take the latest events or a minimum
        last_speed_events = \
            list(map(lambda x: x[1], takewhile(
                lambda i_e:
                diff_in_milliseconds(i_e[1].last_update, last_update) <
                self.MIN_EVENTS_SPEED_TIME or
                i_e[0] < self.MIN_EVENTS_SPEED_AMOUNT,
                enumerate(reversed(tracklet_info.active_speed_events))
            )))
        last_dir_events = \
            list(map(lambda x: x[1], takewhile(
                lambda i_e:
                diff_in_milliseconds(i_e[1].last_update, last_update) <
                self.MIN_EVENTS_DIR_TIME or i_e[0] <
                self.MIN_EVENTS_DIR_AMOUNT,
                enumerate(reversed(tracklet_info.active_direction_events))
            )))

        # if any rule matches, the rule is added to found_rules
        for rule in self.movement_change_rules:
            satisfies_speed_events, dist1, time_from_start1 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, reversed(last_speed_events))
            satisfies_dir_events, dist2, time_from_start2 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, reversed(last_dir_events))

            satisfies_global_events, dist3, time_from_start3 = \
                self.check_ruleevents_in_activeevents(
                    rule.events, [self.global_events[-1]]) if \
                self.global_events else (None, None, None)

            if satisfies_global_events:
                found_global_rules.append((dist3, rule, time_from_start3))
            if satisfies_speed_events or satisfies_dir_events:
                found_local_rules.append(
                    (dist1 + dist2, rule,
                     min(time_from_start1, time_from_start2)))

        return found_local_rules, found_global_rules

    @staticmethod
    def check_ruleevents_in_activeevents(rule_events, last_events):
        """
        Checks if the sequence of rule's events are contained in last_events,
        in the same order as defined in the rule.
        BE CAREFUL: Same order doesn't mean contiguously. Non contiguous
        rule's events will have a distance greater than zero.
        :param rule_events: List of events that shapes a Rule.
        :param last_events: List of last occurred events

        :return: (True/False if satisfy the rule,
                 distance (measure of confidence),
                 time from first event to the last)
        """
        if not last_events:
            return False, 0, maxsize

        firsts = True
        last_events_iter = reversed(list(last_events))

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
                # print("CON EVENTOS0:: %s" % list(last_events))
                return True, distance, time_from_start
        except StopIteration:
            pass

        # FIXME: si no hay eventos de tal tipo en la rule, la distancia no
        # deberia ser cero ya que del otro tipo puede cumplir
        return False, 0, maxsize

    def fire_alarms(self, tracklet_info):
        return_data = {'tracker_id': self.identifier,
                       'rules': [(r[0], r[1].name) for r in
                                 tracklet_info.last_found_rules],
                       'position': tracklet_info.last_position,
                       'id': tracklet_info.id,
                       'img': tracklet_info.img,
                       'timestamp': str(tracklet_info.last_time_found_rules)}

        print("INDIVIDUAL:: %s" % str(tracklet_info.last_found_rules))
        # print("CON EVENTOS:: %s" % str(tracklet_info.active_speed_events[-10:-1]))
        self.communicator.apply(json.dumps(return_data),
                                routing_key='warnings')

    def fire_global_alarms(self, global_rules, current_tracklet):
        return_data = {'tracker_id': 'GLOBAL: Cantidad: ' +
                                     str(self.global_events[-1].type_) +
                                     " por tiempo(ms): " +
                                     str(self.global_events[-1].value),
                       'rules': [(r[0], r[1].name) for r in global_rules],
                       'position': (0, 0),
                       'id': current_tracklet.id,
                       'img': current_tracklet.img,
                       'timestamp': str(
                           global_rules[0][1].events[0].last_update)}
        self.global_events[-1].notified = True
        self.globals_last_notification_datetime = \
            self.global_events[-1].last_update
        self.globals_last_notification_number = self.global_events[-1].type_
        # print("GLOBAL:: %s" % [x for x in return_data.items()
        #                        if x[0] != 'img'])
        print("GLOBAL TOTAL:: %s" % self.global_events[-1])
        self.communicator.apply(json.dumps(return_data),
                                routing_key='warnings')
