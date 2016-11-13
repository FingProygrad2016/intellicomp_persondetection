from patternmaster.event import EventDirection, EventSpeed


class Tracklet(object):
    def __init__(self, identifier):
        self.id = identifier
        self.active_speed_events = []
        self.active_direction_events = []
        self.potential_movement_change_rules_to_reach = []
        self.last_position = None
        self.last_position_time = 0
        self.average_direction = None
        self.last_found_rules = []

    def add_new_events(self, events):
        """
        Add new events to the events collections. Zip them if necessary.
        :param events: contains the local (to the tracklet) events found

        :return: nothing but the thanks :p
        """
        # print("NEW EVENTS:: %s" % str(events))
        for event in events:
            if isinstance(event, EventSpeed):
                if self.active_speed_events and \
                        self.active_speed_events[-1].is_glueable(event):
                    self.active_speed_events[-1].glue(event)
                else:
                    self.active_speed_events.append(event)
            if isinstance(event, EventDirection):
                if self.active_speed_events and \
                        self.active_speed_events[-1].is_glueable(event):
                    self.active_speed_events[-1].glue(event)
                else:
                    self.active_direction_events.append(event)
