import csv

from patternmaster.event import EventSpeed, SpeedEventTypes, Quantifiers, \
    EventDirection


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


def load_system_rules():

    rules = []

    with open('patterns_definition.dat', newline='') as data_csv:
        pattern_definitions = csv.reader(data_csv, delimiter=',', quotechar='"')

        for line, pattern_def in enumerate(pattern_definitions):
            try:
                rule_name = pattern_def[0]

                # Events
                events = []
                for event_type, event_info_type, event_quantifier, event_value \
                    in zip(pattern_def[1::4], pattern_def[2::4],
                           pattern_def[3::4], pattern_def[4::4]):

                    if event_type == 'SPEED':
                        # Check for valid info_type and quantifier
                        if event_info_type not in \
                                [s.name for s in SpeedEventTypes] or \
                                event_quantifier not in \
                                [q.name for q in Quantifiers]:
                            raise Exception(
                                'Rule loader fails in line ' + str(line) + '. ' +
                                'Info type or/and quantifier is/are not valid.')
                        event_class = EventSpeed
                    elif event_type == 'DIRECTION':
                        event_class = EventDirection
                    else:
                        raise Exception(
                            'Rule loader fails in line ' + str(line) + '. ' +
                            'Event type is not valid.')

                    events.append(event_class(event_info_type, event_quantifier,
                                              event_value))
                rules.append(Rule(line, rule_name, events=events))
            except IndexError:
                Exception('Rule loader fails in line ' + str(line) + '. ' +
                          'Min. amount of attributes is 5.')
            except Exception as e:
                Exception('Rule loader fails in line ' + str(line) + '. ' + e)

    return rules
