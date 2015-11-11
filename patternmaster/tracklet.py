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

    def add_new_events(self, new_events):
        """
        Add new events to the events collections. Zip themes if is necessary.
        :param new_events:
        :return:
        """
        for event in new_events:
            if isinstance(event, EventSpeed):
                if self.active_speed_events and \
                        self.active_speed_events[-1].type == event.type and \
                        self.active_speed_events[-1].info_type == \
                        event.info_type:
                    self.active_speed_events[-1].value += event.value
                    self.active_speed_events[-1].last_update = event.last_update
                else:
                    self.active_speed_events.append(event)
            elif isinstance(event, EventDirection):
                self.active_direction_events.append(event)
