from datetime import datetime, timedelta
import unittest

from patternmaster.event import Quantifiers, SpeedEventTypes, EventSpeed
from patternmaster.pattern_recognition import PatternRecognition
from patternmaster.rule import Rule


class PatternRecognitionTestCase(unittest.TestCase):
    def test_rule_distance(self):
        pr = PatternRecognition()
        rule_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.AX, 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 500)
        ]

        date = datetime.now()
        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 0)

        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 5000,
                       date + timedelta(milliseconds=6000), 5000)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 0)

        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1500), 500)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 500)

        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 5000,
                       date + timedelta(milliseconds=6500), 5000)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 500)

        last_events = [
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date - timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 5000,
                       date + timedelta(milliseconds=6500), 5000)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 500)

        last_events = [
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date - timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500, date, 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1500), 500),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 5000,
                       date + timedelta(milliseconds=6500), 5000)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertFalse(satisfy)

        date = datetime.now()
        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ,
                       5000, date, 5000),
            EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.EQ, 600,
                       date + timedelta(milliseconds=500), 500),
            EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.EQ, 500,
                       date + timedelta(milliseconds=1000), 500)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertTrue(satisfy)
        self.assertEqual(rule_distance, 0)

        date = datetime.now()
        last_events = [
            EventSpeed(SpeedEventTypes.WALKING, Quantifiers.EQ,
                       5000, date, 5000)
        ]
        satisfy, rule_distance = \
            pr.check_ruleevents_in_activeevents(rule_events, last_events)
        self.assertFalse(satisfy)

    def test_primitives_recognition(self):
        pattern_recognition = PatternRecognition(
            min_angle_rotation=45, min_walking_speed=10,
            min_running_speed=50)
        # remove the fire_alarms logic
        pattern_recognition.fire_alarms = null_function

        timestamp = datetime.now()
        tracklet = {'id': '123123',
                    'last_position': (0, 0),
                    'last_update_timestamp': timestamp.isoformat()}

        self.assertDictEqual({}, pattern_recognition.tracklets_info)

        pattern_recognition.apply(tracklet)

        tcklts = pattern_recognition.tracklets_info
        self.assertEqual(1, len(tcklts))
        self.assertIn('123123', tcklts)
        self.assertEqual(0, len(tcklts[tracklet['id']].active_speed_events))
        self.assertEqual(0, len(tcklts[tracklet['id']].active_direction_events))

        # 'Send' new data
        tracklet['last_position'] = (0, 0)
        timestamp += timedelta(seconds=1)
        tracklet['last_update_timestamp'] = timestamp.isoformat()
        pattern_recognition.apply(tracklet)

        tcklts = pattern_recognition.tracklets_info
        self.assertEqual(1, len(tcklts))
        self.assertIn('123123', tcklts)
        self.assertEqual(1, len(tcklts[tracklet['id']].active_speed_events))
        self.assertEqual(0, len(tcklts[tracklet['id']].active_direction_events))
        last_speed_event = tcklts[tracklet['id']].active_speed_events[-1]
        self.assertEqual(SpeedEventTypes.STOPPED, last_speed_event.type)

        # 'Send' new data
        tracklet['last_position'] = (5, 5)
        timestamp += timedelta(seconds=1)
        tracklet['last_update_timestamp'] = timestamp.isoformat()
        pattern_recognition.apply(tracklet)

        tcklts = pattern_recognition.tracklets_info
        self.assertEqual(1, len(tcklts))
        self.assertIn('123123', tcklts)
        self.assertEqual(1, len(tcklts[tracklet['id']].active_speed_events))
        self.assertEqual(0, len(tcklts[tracklet['id']].active_direction_events))
        last_speed_event = tcklts[tracklet['id']].active_speed_events[-1]
        self.assertEqual(SpeedEventTypes.STOPPED, last_speed_event.type)

        # 'Send' new data
        tracklet['last_position'] = (10, 10)
        timestamp += timedelta(seconds=1)
        tracklet['last_update_timestamp'] = timestamp.isoformat()
        pattern_recognition.apply(tracklet)

        tcklts = pattern_recognition.tracklets_info
        self.assertEqual(1, len(tcklts))
        self.assertIn('123123', tcklts)
        self.assertEqual(1, len(tcklts[tracklet['id']].active_speed_events))
        self.assertEqual(0, len(tcklts[tracklet['id']].active_direction_events))
        last_speed_event = tcklts[tracklet['id']].active_speed_events[-1]
        self.assertEqual(SpeedEventTypes.STOPPED, last_speed_event.type)

        # 'Send' new data
        tracklet['last_position'] = (0, 0)
        timestamp += timedelta(seconds=1)
        tracklet['last_update_timestamp'] = timestamp.isoformat()
        pattern_recognition.apply(tracklet)

        tcklts = pattern_recognition.tracklets_info
        self.assertEqual(1, len(tcklts))
        self.assertIn('123123', tcklts)
        self.assertEqual(2, len(tcklts[tracklet['id']].active_speed_events))
        self.assertEqual(0, len(tcklts[tracklet['id']].active_direction_events))
        last_speed_event = tcklts[tracklet['id']].active_speed_events[-1]
        self.assertEqual(SpeedEventTypes.WALKING, last_speed_event.type)

    def test_pattern_recognition(self):

        pattern_recognition = PatternRecognition(
            min_angle_rotation=45, min_walking_speed=10,
            min_running_speed=50)
        # remove the fire_alarms logic
        pattern_recognition.rules = []

        # I want to check if the next rule is recognised
        pattern_recognition.movement_change_rules = [
            Rule(1, "walk_stop_run",
                 events=[
                     EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 500),
                     EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.AX, 500),
                     EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 1000)
                 ]),
            Rule(2, "walk_run",
                 events=[
                     EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 5000),
                     EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 1000)
                 ]),
            Rule(3, "stopped_like_an_idiot",
                 events=[
                     EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.GE, 30000)
                 ]),
            Rule(4, "usain_bolt",
                 events=[
                     EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 30000)
                 ])
        ]

        timestamp = datetime.now()

        # NOTHING - 0 sec
        tracklet = {'id': '456789',
                    'last_position': (0, 0),
                    'last_update_timestamp': timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # WALKING - 1 sec
        timestamp += timedelta(seconds=1)
        tracklet = {'id': '456789',
                    'last_position': (15, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # WALKING - 2 sec
        timestamp += timedelta(seconds=1)
        tracklet = {'id': '456789',
                    'last_position': (26, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # STOPPED - 200 msec
        timestamp += timedelta(milliseconds=200)
        tracklet = {'id': '456789',
                    'last_position': (25, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # STOPPED - 400 msec
        timestamp += timedelta(milliseconds=200)
        tracklet = {'id': '456789',
                    'last_position': (26, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # RUNNING - 500 msec
        timestamp += timedelta(milliseconds=500)
        tracklet = {'id': '456789',
                    'last_position': (100, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertListEqual(pattern_recognition.tracklets_info['456789'].
                             last_found_rules, [])

        # RUNNING - 1300 msec -> RULE SATISFIED
        timestamp += timedelta(milliseconds=800)
        tracklet = {'id': '456789',
                    'last_position': (150, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertEqual(1, len(pattern_recognition.tracklets_info['456789'].
                                last_found_rules))
        self.assertEqual('walk_stop_run',
                         pattern_recognition.tracklets_info['456789'].
                         last_found_rules[0][1].name)
        # Check distance
        self.assertEqual(0, pattern_recognition.tracklets_info['456789'].
                         last_found_rules[0][0])

        # RUNNING - 2100 msec -> RULE SATISFIED since 1000 msec ago
        timestamp += timedelta(seconds=1)
        tracklet = {'id': '456789',
                    'last_position': (250, 0),
                    'last_update_timestamp':
                        timestamp.isoformat()}
        pattern_recognition.apply(tracklet)
        self.assertEqual(1, len(pattern_recognition.tracklets_info['456789'].
                                last_found_rules))
        self.assertEqual('walk_stop_run',
                         pattern_recognition.tracklets_info['456789'].
                         last_found_rules[0][1].name)
        # Check distance
        self.assertEqual(0, pattern_recognition.tracklets_info['456789'].
                         last_found_rules[0][0])


def null_function(*null_args1, **null_args2):
    """
    Used to remove the logic of a method
    :return:
    """
    pass


if __name__ == '__main__':
    unittest.main()
