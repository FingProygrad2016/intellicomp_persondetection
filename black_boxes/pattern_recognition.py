import numpy as np


__author__ = 'juan_andres'


class PatternRecognition:

    MIN_DIRECTION_ANGLE_CHANGE_TO_FIRE_ALARM = 120
    MIN_SPEED_FOR_WALKING = 2
    MIN_SPEED_FOR_RUNNING = 12
    QUANTIFIER_APPROXIMATION = 2


    speed_change_events = ('running', 'walking', 'stopped', 'rotation')

    event_info_type = ('time', 'angle')

    quantifier = ('less_or_equal_than', 'more_or_equal_than', 'approximately', 'exactly', 'no_matters')

    speed_change_rules = (
        {
            'id': 1,
            'name': 'walk_run',
            'steps': (
                {
                    'id': 1,
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
                    'event_id': 1,
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
                    'event_id': 3,
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
                    'event_id': 1,
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
                     'event_id': 1,
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
                     'event_id': 4,
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
                     'event_id': 1,
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
    #         'active_event': {
    #             'event_id': 1
    #             'amount_of_time': 10
    #         },
    #         'potential_speed_change_rules_to_reach': [
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


    def apply(self, tracklet_id, last_position, last_position_time, new_position, new_position_time):
        time = self.calc_time_difference(last_position_time, new_position_time)
        current_event = self.calc_event_with_two_points(last_position, new_position, time)
        self.add_event_description(tracklet_id, current_event, time)

        #TODO: verify rules and fire alarms




    def calc_event_with_two_points(self, last_position, new_position, time):
        #TODO: calculate distance between lastPosition and newPosition; if it is larger than a given threshold, trackletId is with event 'running'; else, it is with event 'walking'.
        distance = self.calc_distance_between_points(last_position, new_position)

        # TODO
        current_event = self.speed_change_events[0] # TODO
        return current_event


    def calc_distance_between_points(self, point1, point2):
        #TODO: calculate distance between point1 and point2
        distance = 0
        return distance

    def calc_time_difference(self, time1, time2):
        #TODO: calculate time between time1 and time2
        difference = 0
        return difference

    #def add_event_description(self, tracklet_id, event, time):
    #TODO: if last saved event is the same as the new one, sum 'time' to the one of the last saved event description object; else, add a new event description, with the new event and time.

