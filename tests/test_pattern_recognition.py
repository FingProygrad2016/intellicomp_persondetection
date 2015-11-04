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


if __name__ == '__main__':
    unittest.main()
