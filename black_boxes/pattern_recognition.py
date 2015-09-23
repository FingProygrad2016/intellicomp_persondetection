import numpy as np


__author__ = 'juan_andres'


class PatternRecognition:

    MIN_DIRECTION_ANGLE_CHANGE_TO_CONSIDER_AS_ROTATION_EVENT = 15
    WEIGHT_FOR_NEW_DIRECTION_ANGLE = 0.2
    MIN_DIRECTION_ANGLE_CHANGE_TO_FIRE_ALARM = 120
    MIN_SPEED_FOR_WALKING = 2
    MIN_SPEED_FOR_RUNNING = 12
    QUANTIFIER_APPROXIMATION = 2


    movement_events = [{'type': 1, 'events': ('stopped', 'walking', 'running')}, {'type': 2, 'events': ('rotation')}] # events within each type are mutually exclusive

    event_info_type = ('time', 'angle')

    quantifier = ('less_or_equal_than', 'more_or_equal_than', 'approximately', 'exactly', 'no_matters')

    movement_change_rules = (
        {
            'id': 1,
            'name': 'walk_run',
            'steps': (
                {
                    'id': 1,
                    'event_type': 1,
                    'event_id': 2,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                    ]
                },
                {
                    'id': 2,
                    'event_type': 1,
                    'event_id': 3,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                    ]
                }
            )
        },
        {
            'id': 2,
            'name': 'walk_stop_run',
            'steps': (
                {
                    'id': 1,
                    'event_type': 1,
                    'event_id': 2,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                    ]
                },
                {
                    'id': 2,
                    'event_type': 1,
                    'event_id': 1,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 2
                        }
                    ]
                },
                {
                    'id': 3,
                    'event_type': 1,
                    'event_id': 3,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                    ]
                }
            )
        },
        {
            'id': 3,
            'name': 'run_rotate_run',
            'steps': (
                {
                    'id': 1,
                    'event_type': 1,
                    'event_id': 3,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                     ]
                },
                {
                    'id': 2,
                    'event_type': 2,
                    'event_id': 1,
                    'event_info': [
                        {
                            'type_id': 2,
                            'quantifier_id': 2,
                            'value': 120
                        }
                    ]
                },
                {
                    'id': 3,
                    'event_type': 1,
                    'event_id': 3,
                    'event_info': [
                        {
                            'type_id': 1,
                            'quantifier_id': 2,
                            'value': 5
                        }
                    ]
                }
            )
        }
    )


    # EXAMPLE OF tracklets_info
    # tracklets_info = [
    #     {
    #         'id': 1,
    #         'active_events': [{
    #             'event_type': 1
    #             'event_id': 1
    #             'amount_of_time': 10
    #         }],
    #         'potential_movement_change_rules_to_reach': [
    #             {
    #                 'rule_id': 2,
    #                 'step_id': 1
    #             },
    #             {
    #                 'rule_id': 5,
    #                 'step_id': 3
    #             }
    #         ],
    #         'last_position': {
    #             'x': 2,
    #             'y': 5
    #         },
    #         'last_position_time': 125,
    #         'average_direction': 20 #in grades (ie: 0 -> right; 180 -> left; 90 -> up; 270 -> down)
    #     }
    # ]

    tracklets_info = []


    def apply(self, tracklet_id, new_position, new_position_time):

        (tracklet_info, is_new) = self.get_tracklet_info(tracklet_id)

        if is_new:
            tracklet_info.last_position = new_position
            tracklet_info.last_position_time = new_position_time
        else:

            (time, distance, angle) = self.calc_movements_info(tracklet_info, new_position, new_position_time)

            if time > 0:
                current_events = self.calc_events(tracklet_info, time, distance, angle)
                fired_rules = self.calc_rules(tracklet_info, time, current_events)

                if len(fired_rules) > 0:
                    self.fire_alarms(tracklet_info, fired_rules)

                # TODO!! FROM THIS POINT
                # self.add_event_description(tracklet_id, current_events)

        # TODO: verify rules and fire alarms

    # 1) search for and return the tracklet info with "id = tracklet_id" in the collection
    # 2) if there is not a tracklet info with that id:
    # it creates the info, appends it to the collection, and returns the created info
    def get_tracklet_info(self, tracklet_id):
        tracklet_info = {}

        tracklet_exists = False

        for item in self.tracklets_info:
            if item.id == tracklet_id:
                tracklet_info = item
                tracklet_exists = True

        if not tracklet_exists:
            tracklet_info.id = tracklet_id
            tracklet_info.active_events = [
                {'event_type': 1, 'event_id': -1, 'amount_of_time': 0},
                {'event_type': 2, 'event_id': -1, 'amount_of_time': 0}
            ]
            tracklet_info.potential_movement_change_rules_to_reach = []
            tracklet_info.last_position = {'x': -1, 'y': -1}
            tracklet_info.last_position_time = -1
            tracklet_info.average_direction = -1
            self.tracklets_info.append(tracklet_info)

        return tracklet_info, tracklet_exists

    def calc_movements_info(self, tracklet_info, new_position, new_position_time):
        time = new_position_time - tracklet_info.last_position_time

        (distance, angle) = self.calc_distance_and_angle_between_points(tracklet_info.last_position, new_position)

        return time, distance, angle

    def calc_distance_and_angle_between_points(self, point1, point2):
        # TODO: calculate distance between point1 and point2

        distance = (point2.x - point1.x)*(point2.x - point1.x) + (point2.y - point1.y)*(point2.y - point1.y)

        # sin(angle) = opposite / hypotenuse
        sin_of_angle = abs(point2.y - point1.y) / distance

        angle = np.arcsin(sin_of_angle)

        return distance, angle

    def calc_events(self, tracklet_info, time, distance, angle):

        current_events = []
        current_events.extend(self.calc_direction_events(tracklet_info, angle))
        current_events.extend(self.calc_speed_events(tracklet_info, distance, time))
        return current_events

    def calc_direction_events(self, tracklet_info, angle):
        current_events = []

        if tracklet_info.average_direction == -1:
            tracklet_info.average_direction = angle
        else:
            # calculate the difference between actual direction angle and new direction angle
            min_diff_signed = tracklet_info.average_direction - angle
            min_diff_signed = (min_diff_signed + 180) % 360 - 180
            min_diff = abs(min_diff_signed)

            if min_diff > self.MIN_DIRECTION_ANGLE_CHANGE_TO_CONSIDER_AS_ROTATION_EVENT:
                current_events.append(
                    {'event_type': 2, 'event_id': 1, 'event_info': [{'type_id': 2, 'value': min_diff}]}
                ) # append 'rotation' event

            # new direction is added to average_direction, but with less weight to reduce noise
            tracklet_info.average_direction = tracklet_info.average_direction + min_diff_signed * self.WEIGHT_FOR_NEW_DIRECTION_ANGLE

        return current_events

    def calc_speed_events(self, tracklet_info, distance, time):
        current_events = []

        speed = distance / time

        if speed < self.MIN_SPEED_FOR_WALKING:
            current_events.append(
                {'event_type': 1, 'event_id': 1, 'event_info': []}
            ) # append 'stopped' event
        elif speed < self.MIN_SPEED_FOR_RUNNING:
            current_events.append(
                {'event_type': 1, 'event_id': 2, 'event_info': []}
            ) # append 'walking' event
        else:
            current_events.append(
                {'event_type': 1, 'event_id': 3, 'event_info': []}
            ) # append 'running' event

        return current_events

    def calc_rules(self, tracklet_info, time, current_events):
        fired_rules = []

        for event in current_events:
            active_event = tracklet_info.active_events[event.event_type - 1]

            if active_event.event_id <> event.event_id:
                if active_event.event_id <> -1:
                    # the current event is different from the active event
                    # ==> active event has finished
                    # ==> verify rules

                    # first step of rules is verified
                    for rule in self.movement_change_rules:
                        first_step = rule['steps'][0]
                        if first_step['event_type'] == active_event['event_type']:
                            if first_step['event_id'] == active_event['event_id']:
                                event_info = first_step['event_info']
                                for info in event_info:
                                    # TODO
                                    A = 0




        # TODO

        return fired_rules

    def fire_alarms(self, tracklet_info, fired_rules):
        # TODO: fire alarms
        return len(fired_rules)

    # def add_event_description(self, tracklet_id, event, time):
    # TODO: if last saved event is the same as the new one, sum 'time' to the one of the last saved event description object; else, add a new event description, with the new event and time.