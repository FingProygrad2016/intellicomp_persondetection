from patternmaster.event import EventSpeed, SpeedEventTypes, Quantifiers


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
    rules = [
        # Rule(1, "walk_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.AX, 5000),
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000)
        #      ]),
        # Rule(2, "walk_stop_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 5000),
        #          EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.AX, 2000),
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 5000)
        #      ]),
        # Rule(2, "run_rotate_run",
        #      events=[
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000),
        #          EventDirection(DirectionEventTypes.ROTATION,
        #                         Quantifiers.AX, 120),
        #          # EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.AX, 5000)
        #      ]),
        Rule(3, "WALKING",
             events=[
                 EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 500)
             ]),
        Rule(3, "RUNNING",
             events=[
                 EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 1500)
             ]),
        Rule(3, "STOPPED",
             events=[
                 EventSpeed(SpeedEventTypes.STOPPED, Quantifiers.GE, 500)
             ]),
        # Rule(3, "tired_runner",
        #      events=[
        #          EventSpeed(SpeedEventTypes.RUNNING, Quantifiers.GE, 3000),
        #          EventSpeed(SpeedEventTypes.WALKING, Quantifiers.GE, 2000)
        #      ])
    ]

    return rules