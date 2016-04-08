from uuid import uuid4
from datetime import datetime
import random

import numpy as np
import cv2
from scipy.linalg import block_diag
from filterpy.common import Q_discrete_white_noise

from utils.tools import get_avg_color, euclidean_distance
from trackermaster.black_boxes.blob_assignment import HungarianAlgorithm
from trackermaster.config import config

# Ejemplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf


class Tracker:

    k_filters = []
    kfs_per_blob = []
    tracklets_short_id = 1

    def __init__(self, seconds_per_frame):

        # Configuration parameters
        self.threshold_color = config.getint('THRESHOLD_COLOR')
        self.threshold_size = config.getint('THRESHOLD_SIZE')
        self.threshold_distance = config.getint('THRESHOLD_DISTANCE')
        self.max_seconds_without_update = \
            config.getfloat('MAX_SECONDS_WITHOUT_UPDATE')
        self.max_seconds_to_predict_position = \
            config.getfloat('MAX_SECONDS_TO_PREDICT_POSITION')
        self.max_seconds_without_any_blob = \
            config.getfloat('MAX_SECONDS_WITHOUT_ANY_BLOB')
        self.min_seconds_to_be_accepted_in_group = \
            config.getfloat('MIN_SECONDS_TO_BE_ACCEPTED_IN_GROUP')

        self.INFINITE_DISTANCE = config.getint('INFINITE_DISTANCE')

        self.last_frame = 0
        self.seconds_per_frame = seconds_per_frame

        # calculate the amount of valid frames to be without an update
        self.valid_frames_without_update = self.max_seconds_without_update / self.seconds_per_frame

        # calculate the amount of valid frames to predict position of kalman filters without one to one relationship
        self.valid_frames_to_predict_position = self.max_seconds_to_predict_position / self.seconds_per_frame

        # calculate the amount of valid frames to be without any near blob
        self.valid_frames_without_any_blob = self.max_seconds_without_any_blob / self.seconds_per_frame

        self.valid_frames_since_created = self.min_seconds_to_be_accepted_in_group / self.seconds_per_frame

        def position_distance_function(blob, k_filter):
            prediction = k_filter.kalman_filter.statePost
            return euclidean_distance((prediction[0], prediction[3]), blob[0]["position"].pt)

        # Hungarian Algorithm for blob position
        self.hung_alg_blob_pos = HungarianAlgorithm(position_distance_function, self.threshold_distance,
                                                    self.INFINITE_DISTANCE)

        def position_distance_function_ini(blob, k_filter):
            prediction = k_filter.kalman_filter.statePost
            return euclidean_distance((prediction[0], prediction[3]), blob["position"].pt)

        # Hungarian Algorithm for blob position
        self.hung_alg_blob_pos_ini = HungarianAlgorithm(position_distance_function_ini, self.threshold_distance,
                                                        self.INFINITE_DISTANCE)

        # TODO: IMPLEMENT
        """
        def blob_size_distance_function(k_filter, blob):
            return abs(blob.size - k_filter.size)

        # Hungarian Algorithm for blob size
        self.hung_alg_blob_size = HungarianAlgorithm(blob_size_distance_function, self.threshold_size,
                                                     self.INFINITE_DISTANCE)
        """

        def blob_color_distance_function(color, k_filter):
            return euclidean_distance(color, k_filter.color)

        # Hungarian Algorithm for blob color
        self.hung_alg_blob_color = HungarianAlgorithm(blob_color_distance_function, self.threshold_color,
                                                      self.INFINITE_DISTANCE)

        # General matrixes for the Kalman Filters

        q = Q_discrete_white_noise(dim=3, dt=self.seconds_per_frame, var=0.05)  # Var = variation of model between steps

        aux = block_diag(q, q)
        self.process_noise_cov = np.array(aux, np.float32)

    def apply(self, blobs, raw_image, bg_subtraction_image, frame_number, scores):
        """
        For every blob, detect the corresponded tracked object and update it
        with the new information
        :param blobs: List of new blobs detected
        :param raw_image: The raw image captured
        :param frame_number: The actual frame number of the video/stream
        :return: A list of TrackInfo which journey is greater than 5
        """

        journeys = []

        # elapsed_time = (frame_number - self.last_frame) * self.seconds_per_frame
        self.last_frame = frame_number

        for kf in self.k_filters:
            # Amount of frames it has been without a one to one relationship
            frames_without_one_to_one = self.last_frame - kf.last_frame_update
            if frames_without_one_to_one <= self.valid_frames_to_predict_position:
                # predict position of kfs without one at one relationship for a valid time frame
                kf.predict()

        if len(blobs) > 0:
            for item in self.kfs_per_blob:
                item['blobs'] = []
                item['has_been_assigned'] = False

            # Apply hungarian algorithm for blob position
            best_kf_per_blob_pos, best_kf_per_blob_pos_costs = self.hung_alg_blob_pos_ini.apply(blobs, self.k_filters)

            group_per_blob = []

            # Blobs are assigned to the nearest kalman filter (one kalman filter per blob)
            for i, blob in enumerate(blobs):
                best_kf = best_kf_per_blob_pos[i]
                if best_kf != -1:
                    kf = self.k_filters[best_kf]
                    self.kfs_per_blob[kf.group_number]['blobs'].append((blob, i))
                    self.kfs_per_blob[kf.group_number]['has_been_assigned'] = True
                    group_per_blob.append(kf.group_number)
                else:
                    # this is the result of a new blob (shaped like a person) in the scene
                    # new kalman filter is created for the blob
                    best_kf = self.add_new_tracking(blob["position"].pt,
                                                    blob["position"].size, blob, frame_number, scores[i],
                                                    raw_image, bg_subtraction_image)
                    kf = self.k_filters[best_kf]
                    self.kfs_per_blob.append({'k_filters': [kf], 'blobs': [(blob, i)],
                                              'has_been_assigned': True,
                                              'color': (random.randint(0, 255),
                                                        random.randint(0, 255),
                                                        random.randint(0, 255))})
                    group_per_blob.append(len(self.kfs_per_blob) - 1)

            for item in self.kfs_per_blob:
                if not item['has_been_assigned']:
                    # this is the result of two or more blobs merging (occlusion)
                    nearest_blob = self.search_nearest_blob(item, blobs)
                    if nearest_blob != -1:
                        item['has_been_assigned'] = True
                        self.kfs_per_blob[group_per_blob[nearest_blob]]['k_filters'].extend(item['k_filters'])
                        item['k_filters'] = []

            items_to_remove = []
            kf_to_remove = []
            groups_to_append = []
            for i, item in enumerate(self.kfs_per_blob):
                item_kf = item['k_filters']
                item_blobs = item['blobs']
                if len(item_blobs) == 0:
                    # there are not blobs assigned to the kalman filter(s)

                    kf_to_remove_in_item = []
                    for j, kf in enumerate(item_kf):
                        # Amount of frames it has been without any blob relationship
                        frames_without_any_blob = self.last_frame - kf.last_frame_not_alone
                        # Amount of frames since it has been created
                        frames_since_created = self.last_frame - kf.created_frame
                        if frames_without_any_blob > self.valid_frames_without_any_blob:
                            # If TrackInfo has been without blobs for some time, remove it forever
                            kf_to_remove_in_item.append({"index": j, "kf": kf})
                        elif frames_since_created < self.valid_frames_since_created:
                            # it has been created a very short time ago: remove it
                            kf_to_remove_in_item.append({"index": j, "kf": kf})

                    kf_to_remove.extend(kf_to_remove_in_item)

                    # Remove the old tracked objects
                    for x in reversed(kf_to_remove_in_item):
                        item_kf.pop(x["index"])

                    if len(item_kf) == 0:
                        items_to_remove.append(i)

                elif len(item_blobs) == 1:
                    blob, index = item_blobs[0]
                    if len(item_kf) == 1:
                        # normal case: one on one
                        # kalman filter is updated with all the blob info
                        kf = item_kf[0]
                        kf.update_info(new_position=blob["position"].pt,
                                       size=blob["position"].size, blob=blob, last_frame_update=frame_number,
                                       score=scores[index], raw_image=raw_image,
                                       bg_subtraction_image=bg_subtraction_image)
                    elif len(item_kf) > 1:
                        # merged blobs: many kalman filters on one blob
                        # kalman filters are updated only with the blob position

                        self.remove_or_update_kalman_filters(i, frame_number, item_kf, blob,
                                                             kf_to_remove, items_to_remove)

                elif len(item_blobs) > 1:
                    if len(item_kf) >= len(item_blobs):
                        # blobs that were merged have been split
                        # color, size, and any appearance comparisons are made to match blobs to  kalman filter(s)
                        # there must be no kalman filters left alone either

                        unassigned_blobs = []
                        unassigned_blobs_ind = []
                        for j, blob in enumerate(item_blobs):
                            unassigned_blobs.append(blob)
                            unassigned_blobs_ind.append(j)

                        kfs_to_compare = []
                        kfs_to_compare_ind = []
                        kfs_to_compare_later = []
                        kfs_to_compare_later_ind = []

                        for j, kf in enumerate(item_kf):
                            # Amount of frames it has been without a one to one relationship
                            frames_without_one_to_one = self.last_frame - kf.last_frame_update
                            if frames_without_one_to_one <= self.valid_frames_to_predict_position:
                                # If it has been without one to one for a short time, compare by position
                                kfs_to_compare.append(kf)
                                kfs_to_compare_ind.append(j)
                            else:
                                # If it has been without one to one for a long time, compare by color
                                kfs_to_compare_later.append(kf)
                                kfs_to_compare_later_ind.append(j)

                        # the blobs position are compared with all kfs with valid position comparison
                        # for each match, both go to a new group
                        # if all blobs are matched with valid kfs, the worst match keeps the remaining kfs

                        kf_to_remove_in_item = []
                        blob_to_remove_in_item = []

                        best_filter_per_blob, best_filter_per_blob_costs = \
                            self.hung_alg_blob_pos.apply(unassigned_blobs, kfs_to_compare)

                        choose_worst_fit_blob = False
                        # if more kalman filters than blobs, the worst fitting blob keeps the remaining filters
                        if len(item_kf) > len(unassigned_blobs):
                            choose_worst_fit_blob = True

                        aux_kfs_to_remove, aux_blobs_to_remove = self.get_nearest_blobs(groups_to_append, raw_image,
                                                                                        bg_subtraction_image,
                                                                                        frame_number, scores,
                                                                                        unassigned_blobs,
                                                                                        unassigned_blobs_ind,
                                                                                        kfs_to_compare,
                                                                                        kfs_to_compare_ind,
                                                                                        best_filter_per_blob,
                                                                                        best_filter_per_blob_costs,
                                                                                        choose_worst_fit_blob)

                        kf_to_remove_in_item.extend(aux_kfs_to_remove)
                        blob_to_remove_in_item.extend(aux_blobs_to_remove)

                        if len(unassigned_blobs) > 1:
                            # if there is more than one blob left to assign, then show must go on

                            # kalman filters which were not matched by position
                            # are added to the ones to compare by color
                            kfs_to_compare.extend(kfs_to_compare_later)
                            kfs_to_compare_ind.extend(kfs_to_compare_later_ind)

                            # unassigned blobs are compared by color with remaining kfs,
                            # including with kfs with valid position comparison that were not matched
                            average_colors = []
                            for blob in unassigned_blobs:
                                average_colors.append(get_avg_color(raw_image, bg_subtraction_image,
                                                                    blob[0]["box"]))

                            best_filter_per_blob, best_filter_per_blob_costs = \
                                self.hung_alg_blob_color.apply(average_colors, kfs_to_compare)

                            # if more kalman filters than blobs, the worst fitting blob keeps the remaining filters
                            if len(kfs_to_compare) > len(unassigned_blobs):
                                choose_worst_fit_blob = True

                            aux_kfs_to_remove, aux_blobs_to_remove = self.get_nearest_blobs(groups_to_append, raw_image,
                                                                                            bg_subtraction_image,
                                                                                            frame_number, scores,
                                                                                            unassigned_blobs,
                                                                                            unassigned_blobs_ind,
                                                                                            kfs_to_compare,
                                                                                            kfs_to_compare_ind,
                                                                                            best_filter_per_blob,
                                                                                            best_filter_per_blob_costs,
                                                                                            choose_worst_fit_blob)

                            kf_to_remove_in_item.extend(aux_kfs_to_remove)
                            blob_to_remove_in_item.extend(aux_blobs_to_remove)

                        kf_to_remove_in_item.sort()
                        # Remove the moved tracked objects
                        for x in reversed(kf_to_remove_in_item):
                            item_kf.pop(x)

                        blob_to_remove_in_item.sort()
                        # Remove the moved blobs
                        for x in reversed(blob_to_remove_in_item):
                            item_blobs.pop(x)

                        if len(item_kf) == 0:
                            items_to_remove.append(i)
                        else:
                            # kalman filters are updated only with the blob position
                            self.remove_or_update_kalman_filters(i, frame_number, item_kf, item_blobs[0][0],
                                                                 kf_to_remove, items_to_remove)

                    elif len(item_kf) < len(item_blobs):
                        # this can not happen; each blob must have at least one kalman filter assigned
                        pass

            for x in reversed(items_to_remove):
                self.kfs_per_blob.pop(x)

            # Remove the old tracked objects
            for x in kf_to_remove:
                self.k_filters.remove(x["kf"])

            self.kfs_per_blob.extend(groups_to_append)

            for i, item in enumerate(self.kfs_per_blob):
                if len(item['blobs']) > 0:
                    blob = item['blobs'][0][0]
                    item['average_pos'] = blob["position"].pt
                for kf in item['k_filters']:
                    kf.group_number = i

            # Prepare the return data
            for kf in self.k_filters:

                # TODO: ¡¡¡Resolver como calcular el score y como afecta a esta
                # TODO: parte!!!
                # if kf.score > 0.3:
                journeys.append((kf.journey, kf.journey_color, kf.short_id,
                                 kf.rectangle, kf.kalman_filter.statePost, False,
                                 self.kfs_per_blob[kf.group_number]['color']))

        return journeys, [kf.to_dict() for kf in self.k_filters], \
            {k.id: k for k in self.k_filters}

    def add_new_tracking(self, point, size, blob, frame_number, score, raw_image, bg_subtraction_image):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(size, point, self.tracklets_short_id, blob,
                               frame_number, score, self.seconds_per_frame, self.process_noise_cov,
                               raw_image, bg_subtraction_image)
        self.k_filters.append(track_info)

        self.tracklets_short_id += 1

        return len(self.k_filters) - 1

    def remove_or_update_kalman_filters(self, item_id, frame_number, kalman_filters, blob,
                                        kf_to_remove, items_to_remove):
        # kalman filters are updated only with the blob position
        kf_to_remove_in_item = []
        for j, kf in enumerate(kalman_filters):
            # Amount of frames it has been without a one to one relationship
            frames_without_one_to_one = self.last_frame - kf.last_frame_update
            # Amount of frames since it has been created
            frames_since_created = self.last_frame - kf.created_frame
            if frames_without_one_to_one > self.valid_frames_without_update:
                # If TrackInfo is too old, remove it forever
                kf_to_remove_in_item.append({"index": j, "kf": kf})
            elif frames_without_one_to_one > self.valid_frames_to_predict_position:
                # If it has been without one to one for a long time, correct with the merged blob
                kf.update_pos_info(new_position=blob["position"].pt, frame_number=frame_number)
            elif frames_since_created < self.valid_frames_since_created:
                # it has been created a very short time ago: remove it
                kf_to_remove_in_item.append({"index": j, "kf": kf})
            else:
                # It has been with one to one recently. It is left only with prediction.
                kf.update_last_frame_not_alone(frame_number)

        kf_to_remove.extend(kf_to_remove_in_item)

        # Remove the old tracked objects
        for x in reversed(kf_to_remove_in_item):
            kalman_filters.pop(x["index"])

        if len(kalman_filters) == 0:
            items_to_remove.append(item_id)

    def search_nearest_blob(self, kfs_group_item, blobs):
        min_distance = self.INFINITE_DISTANCE
        nearest_blob = -1
        for i in range(0, len(blobs)):
            prediction = kfs_group_item['average_pos']
            distance = euclidean_distance((prediction[0], prediction[1]), blobs[i]["position"].pt)
            if distance < min_distance:
                min_distance = distance
                nearest_blob = i

        if min_distance <= self.threshold_distance:
            return nearest_blob
        else:
            return -1

    def get_nearest_blobs(self, groups, raw_image, bg_subtraction_image, frame_number,
                          scores, blobs, blobs_ind, filters, filters_ind, best_filter_per_blob,
                          best_filter_per_blob_costs, choose_worst_fit_blob):

        kf_to_remove_in_item = []
        blob_to_remove_in_item = []
        filters_to_remove = []
        blobs_to_remove = []

        worst_fit_blob = -1
        worst_fit = 100000

        # if more kalman filters than blobs, the worst fitting blob keeps the remaining filters
        if choose_worst_fit_blob:
            for j, fit in enumerate(best_filter_per_blob_costs):
                if fit < worst_fit:
                    worst_fit_blob = j
                    worst_fit = fit

        for j, kf_ind in enumerate(best_filter_per_blob):
            if j != worst_fit_blob:
                if kf_ind != -1:
                    blob, blob_index = blobs[j]
                    kf = filters[kf_ind]
                    # this blob has to go to a new group, with the assigned kalman filter
                    groups.\
                        append({'k_filters': [kf],
                                'blobs': [(blob, blob_index)],
                                'color': (random.randint(0, 255),
                                          random.randint(0, 255),
                                          random.randint(0, 255))})

                    # kalman filter is updated with all the blob info
                    kf.update_info(new_position=blob["position"].pt,
                                   size=blob["position"].size, blob=blob,
                                   last_frame_update=frame_number, score=scores[blob_index],
                                   raw_image=raw_image, bg_subtraction_image=bg_subtraction_image)

                    blob_to_remove_in_item.append(blobs_ind[j])
                    kf_to_remove_in_item.append(filters_ind[kf_ind])

                    blobs_to_remove.append(j)
                    filters_to_remove.append(kf_ind)

                else:
                    # may be more than one non assigned blob (this one and, maybe, the worst fit blob)
                    pass  # TODO: what to do if there is more than one non assigned blob...
            else:
                # this blob has to be kept in the group, with the remaining kalman filters
                # nothing has to be done here
                pass

        # Remove the moved blobs
        for x in reversed(blobs_to_remove):
            blobs.pop(x)
            blobs_ind.pop(x)

        filters_to_remove.sort()
        # Remove the moved tracked objects
        for x in reversed(filters_to_remove):
            filters.pop(x)
            filters_ind.pop(x)

        return kf_to_remove_in_item, blob_to_remove_in_item


class TrackInfo:

    def __init__(self, size, point, short_id, blob, frame_number,
                 score, time_interval, process_noise_cov, raw_image, bg_subtraction_image):

        self.size = size
        self.created_datetime = datetime.now()
        self.created_frame = frame_number
        self.id = uuid4().hex
        self.short_id = short_id
        self.last_frame_update = frame_number
        self.last_frame_not_alone = frame_number
        self.last_update = self.created_datetime
        self.last_point = point
        self.group_number = -1
        self.score = score

        self.rectangle = blob["box"]
        self.color = get_avg_color(raw_image, bg_subtraction_image, self.rectangle)

        self.kalman_filter = cv2.KalmanFilter(6, 2, 0)

        acceleration_change = time_interval * time_interval / 2

        self.kalman_filter.transitionMatrix = \
            np.array([[1, time_interval, acceleration_change, 0,             0,                   0],
                      [0,             1,       time_interval, 0,             0,                   0],
                      [0,             0,                   1, 0,             0,                   0],
                      [0,             0,                   0, 1, time_interval, acceleration_change],
                      [0,             0,                   0, 0,             1,       time_interval],
                      [0,             0,                   0, 0,             0,                   1]], np.float32)

        self.kalman_filter.measurementMatrix = \
            np.array([[1, 0, 0, 0, 0, 0],
                      [0, 0, 0, 1, 0, 0]], np.float32)

        self.process_noise_cov = process_noise_cov
        self.initial_position = point

        # Initialize the process noise matrix to the identity, in order to
        # only take into account the measurements in the first frames.
        # Process prediction is not taken into account in first frames, as...
        # ... there is not a good initial velocity prediction
        self.kalman_filter.processNoiseCov = np.eye(N=6, dtype=np.float32)

        self.kalman_filter.measurementNoiseCov = \
            np.array([[1, 0],
                      [0, 1]], np.float32)

        self.journey = []

        if config.getboolean("JOURNEYS_RANDOM_COLOR"):
            self.journey_color = (random.randint(0, 255), random.randint(0, 255),
                                  random.randint(0, 255))
        else:
            self.journey_color = self.color

        self.number_updates = 1

        array_aux = np.array(
            [[point[0]], [0.0], [0.0], [point[1]], [0.0], [0.0]], np.float32)
        self.kalman_filter.statePost = array_aux

        # prediction of next new position
        self.predict()

        self.journey.append(np.array(array_aux.copy()))

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self):
        self.kalman_filter.predict()

    def correct(self, measurement):
        correction = self.kalman_filter.correct(measurement)

        self.journey.append(np.array(correction.copy()))

        return correction

    def update_last_frame(self, last_frame_update):
        self.last_frame_update = last_frame_update
        self.last_frame_not_alone = last_frame_update
        self.last_update = datetime.now()

    def update_info(self, new_position, size,
                    blob, last_frame_update, score,
                    raw_image, bg_subtraction_image):
        # correction with the known new position
        self.correct(np.array(new_position, np.float32))
        # self.color = color
        self.size = size
        self.last_frame_update = last_frame_update
        self.last_frame_not_alone = last_frame_update
        self.last_update = datetime.now()
        self.last_point = new_position

        self.score = (self.score * self.number_updates + score) /\
                     (self.number_updates + 1)

        self.rectangle = blob["box"]

        self.number_updates += 1

        if self.number_updates == 5:
            # Use the information of the initial position and 5th update
            # new_position to initialize the kalman filter velocity.
            # Also, initialize the kalman filter process noise matrix.
            self.kalman_filter.processNoiseCov = self.process_noise_cov
            aux = (new_position[0] - self.initial_position[0],
                   new_position[1] - self.initial_position[1])
            self.kalman_filter.statePost[1] = aux[0]/5.0
            self.kalman_filter.statePost[4] = aux[1]/5.0

        # if color has not been set and there are at least 5 updates, calculate and set color
        if (self.color is None) and (self.number_updates % 10 == 0):
            self.color = get_avg_color(raw_image, bg_subtraction_image, self.rectangle)
            if not config.getboolean("JOURNEYS_RANDOM_COLOR"):
                self.journey_color = self.color

    def update_pos_info(self, new_position, frame_number):  # , last_frame_update):
        self.correct(np.array(new_position, np.float32))
        self.last_point = new_position
        self.last_frame_not_alone = frame_number

        self.number_updates += 1

        if self.number_updates == 5:
            # Use the information of the initial position and 5th update
            # new_position to initialize the kalman filter velocity.
            # Also, initialize the kalman filter process noise matrix.
            self.kalman_filter.processNoiseCov = self.process_noise_cov
            aux = (new_position[0] - self.initial_position[0],
                   new_position[1] - self.initial_position[1])
            self.kalman_filter.statePost[1] = aux[0] / 5.0
            self.kalman_filter.statePost[4] = aux[1] / 5.0

    def update_last_frame_not_alone(self, frame_number):
        self.last_frame_not_alone = frame_number

    def to_dict(self):
        return {
            # "color": list(self.color),
            # "size": self.size,
            "created_timestamp":
                self.created_datetime.isoformat(),
            "id": self.id,
            "last_update_timestamp":
                self.last_update.isoformat(),
            "last_position": self.last_point
        }
