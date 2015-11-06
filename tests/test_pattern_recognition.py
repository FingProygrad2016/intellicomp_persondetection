from datetime import datetime, timedelta
import unittest
from patternmaster.event import Quantifiers, SpeedEventTypes, EventSpeed

from patternmaster.pattern_recognition import PatternRecognition


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
            min_angle_to_consider_rotation=45, min_walking_speed=10,
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


def null_function(*null_args1, **null_args2):
    """
    Used to remove the logic of a method
    :return:
    """
    pass


if __name__ == '__main__':
    unittest.main()
