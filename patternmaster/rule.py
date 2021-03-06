import csv
import os
import inspect

from patternmaster.event import EventSpeed, SpeedEventTypes, Quantifiers, \
    EventDirection, DirectionEventTypes, EventAgglomeration
from patternmaster.config import read_conf


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


def load_system_rules(config=None):

    if not config:
        config = read_conf()

    rules = []

    conf_file_path = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe())))
    with open(conf_file_path + config.get('PATTERNS_DEFINITION_FILE_PATH'),
              newline='') as data_csv:
        pattern_definitions = \
            csv.reader(data_csv, delimiter=',', quotechar='"')

        for line, pattern_def in enumerate(pattern_definitions):
            try:
                rule_name = pattern_def[0]

                # Events
                events = []
                for event_type, event_info_type, event_quantifier, \
                    event_value \
                    in zip(pattern_def[1::4], pattern_def[2::4],
                           pattern_def[3::4], pattern_def[4::4]):

                    if event_type == 'SPEED':
                        # Check for valid info_type and quantifier
                        if event_info_type not in \
                                [s.name for s in SpeedEventTypes] or \
                                event_quantifier not in \
                                [q.name for q in Quantifiers]:
                            raise Exception(
                                'Rule loader fails in line %s. ' +
                                'Info type or/and quantifier is/are not valid.'
                                % str(line))
                        event_class = EventSpeed
                        type_enum = SpeedEventTypes
                    elif event_type == 'DIRECTION':
                        event_class = EventDirection
                        type_enum = DirectionEventTypes
                    elif event_type == 'AGGLOMERATION':
                        events.append(
                            EventAgglomeration(
                                type_=int(event_info_type),
                                quantifier=Quantifiers[event_quantifier],
                                value=float(event_value))
                        )
                        continue
                    else:
                        raise Exception(
                            'Rule loader fails in line ' + str(line) + '. ' +
                            'Event type is not valid.')

                    events.append(event_class(type_enum[event_info_type],
                                              Quantifiers[event_quantifier],
                                              float(event_value)))
                rules.append(Rule(line, rule_name, events=events))
            except IndexError:
                raise Exception('Rule loader fails in line %s. '
                                'Min. amount of attributes is 5.' % str(line))
            except Exception as e:
                raise Exception('Rule loader fails in line %s. %s' %
                                (str(line), e.args[0]))

    return rules
