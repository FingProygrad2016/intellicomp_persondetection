import numpy as np


__author__ = 'juan_andres'


class PatternRecognition:

    #TODO: description of events through time. For each trackletId, it is like:
    #TODO: [(event-1, amount_of_time-1), ... , (event-n, amount_of_time-n)]

    def apply(self, trackletId, lastPosition, lastPositionTime, newPosition, newPositionTime):
        time = self.calc_time_difference(lastPositionTime, newPositionTime)
        event = self.calc_event_with_two_points(lastPosition, newPosition, time)
        self.add_event_description(trackletId, event, time)



    def calc_event_with_two_points(self, lastPosition, newPosition, time):
        #TODO: calculate distance between lastPosition and newPosition; if it is larger than a given threshold, trackletId is with event 'running'; else, it is with event 'walking'.
        distance = self.calc_distance_between_points(lastPosition, newPosition)

        # TODO
        event = 'running' # TODO
        return event


    def calc_distance_between_points(self, point1, point2):
        #TODO: calculate distance between point1 and point2
        distance = 0
        return distance

    def calc_time_difference(self, time1, time2):
        #TODO: calculate time between time1 and time2
        difference = 0
        return difference

    def add_event_description(self, trackletId, event, time):
        #TODO: if last saved event is the same as the new one, sum 'time' to the one of the last saved event description object; else, add a new event description, with the new event and time.