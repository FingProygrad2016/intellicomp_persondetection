from uuid import uuid4
from datetime import datetime
import random

import numpy as np
import imutils
import cv2
from scipy.linalg import block_diag
from filterpy.common import Q_discrete_white_noise
from filterpy.kalman import FixedLagSmoother

from utils.tools import get_avg_color, euclidean_distance, compare_color,\
    compare_color_histogram, get_color_histogram
from trackermaster.black_boxes.blob_assignment import HungarianAlgorithm
from trackermaster.config import config

# Ejemplo simple de Kalman Filter
# https://github.com/Itseez/opencv/blob/master/samples/python2/kalman.py
# https://github.com/simondlevy/OpenCV-Python-Hacks/blob/master/kalman_mousetracker.py
# Metodo para reconocer a que blob hacemos referencia (por color y tamano):
# http://airccse.org/journal/sipij/papers/2211sipij01.pdf


SHOW_COMPARISONS_BY_COLOR = config.getboolean('SHOW_COMPARISONS_BY_COLOR')
SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION = \
    config.getboolean('SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION')
SHOW_COMPARISONS_BY_COLOR_ONLY_NON_ZERO = config.getboolean('SHOW_COMPARISONS_BY_COLOR_ONLY_NON_ZERO')
SHOW_COMPARISONS_BY_COLOR_GREEN = config.getboolean('SHOW_COMPARISONS_BY_COLOR_GREEN')
SHOW_COMPARISONS_BY_COLOR_RED = config.getboolean('SHOW_COMPARISONS_BY_COLOR_RED')
SHOW_COMPARISONS_BY_COLOR_GREY = config.getboolean('SHOW_COMPARISONS_BY_COLOR_GREY')
JOURNEYS_RANDOM_COLOR = config.getboolean('JOURNEYS_RANDOM_COLOR')
USE_HISTOGRAMS_FOR_TRACKING = config.getboolean('USE_HISTOGRAMS_FOR_TRACKING')
HISTOGRAM_COMPARISON_METHOD = config.get('HISTOGRAM_COMPARISON_METHOD')

PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS = \
    list(map(lambda x: float(x), config.get('PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS').split(', ')))
SECONDARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS = \
    list(map(lambda x: float(x), config.get('SECONDARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS').split(', ')))

# Kalman filter types: NORMAL (from OpenCV); SMOOTHED (from filterpy)
if config.get('KALMAN_FILTER_TYPE') == 'NORMAL':
    KALMAN_FILTER_TYPE = 1
elif config.get('KALMAN_FILTER_TYPE') == 'SMOOTHED':
    KALMAN_FILTER_TYPE = 2
else:
    KALMAN_FILTER_TYPE = 0
# Number of updates to use when smoothing
KALMAN_FILTER_SMOOTH_LAG = config.getint('KALMAN_FILTER_SMOOTH_LAG')

# Variance of measures noise (in pixels)
VARIANCE_OF_MEASURES_NOISE = config.getint('MEASURES_NOISE_IN_PIXELS')\
                             * config.getint('MEASURES_NOISE_IN_PIXELS')

# Variance of non truthful measures noise (in pixels)
VARIANCE_OF_NON_TRUTHFUL_MEASURES_NOISE = config.getint('NON_TRUTHFUL_MEASURES_NOISE_IN_PIXELS')\
                                          * config.getint('NON_TRUTHFUL_MEASURES_NOISE_IN_PIXELS')


class Tracker:

    k_filters = []
    kfs_per_blob = []
    tracklets_short_id = 1

    def __init__(self, fps):

        # Configuration parameters
        self.threshold_color = config.getfloat('THRESHOLD_COLOR')
        self.threshold_distance = config.getfloat('THRESHOLD_DISTANCE')
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
        self.frames_per_second = fps
        self.seconds_per_frame = 1. / fps

        # calculate the amount of valid frames to be without an update
        self.valid_frames_without_update = self.max_seconds_without_update / self.seconds_per_frame

        # calculate the amount of valid frames to predict position of kalman filters without one to one relationship
        self.valid_frames_to_predict_position = self.max_seconds_to_predict_position / self.seconds_per_frame

        # calculate the amount of valid frames to be without any near blob
        self.valid_frames_without_any_blob = self.max_seconds_without_any_blob / self.seconds_per_frame

        self.valid_frames_since_created = self.min_seconds_to_be_accepted_in_group / self.seconds_per_frame

        def blob_previous_color_distance_function(color, k_filter):
            distance = compare_color_aux(color, k_filter.previous_color)
            return {"value": distance, "valid": distance <= self.threshold_color}

        # Hungarian Algorithm for blob color
        self.hung_alg_blob_previous_color = HungarianAlgorithm(blob_previous_color_distance_function,
                                                               self.threshold_color, self.INFINITE_DISTANCE)

        def scores_distance_function(blob, k_filter, weights):
            # TODO: review and correct the issue of weights and comparison with the thresholds
            # TODO: in the case where the weight is different from 0 and 1.
            ok = True
            distance_array = np.zeros(3)

            if weights[0] == 0:
                distance_array[0] = 0
            else:
                corrected_pos = k_filter.get_state_post()
                distance_array[0] = euclidean_distance((corrected_pos[0], corrected_pos[3]), blob["position"].pt)
                if distance_array[0] * weights[0] > self.threshold_distance:
                    ok = False
                # if the distance is valid, then the distance will be between 0 and 1
                distance_array[0] /= self.threshold_distance * weights[0]

            if weights[1] == 0:
                distance_array[1] = 0
            else:
                predicted_pos = k_filter.get_predicted_state_position()
                distance_array[1] = euclidean_distance((predicted_pos[0], predicted_pos[1]), blob["position"].pt)
                if distance_array[1] * weights[1] > self.threshold_distance:
                    ok = False
                # if the distance is valid, then the distance will be between 0 and 1
                distance_array[1] /= self.threshold_distance * weights[1]

            if weights[2] == 0:
                distance_array[2] = 0
            else:
                distance_array[2] = compare_color_aux(blob["color"], k_filter.color)
                if distance_array[2] * weights[2] > self.threshold_color:
                    ok = False
                # if the distance is valid, then the distance will be between 0 and 1
                distance_array[2] /= self.threshold_color * weights[2]

            return {"value": np.sum(distance_array), "valid": ok}

        # Hungarian Algorithm with scores
        self.hung_alg_with_scores = HungarianAlgorithm(scores_distance_function, self.threshold_color,
                                                       self.INFINITE_DISTANCE)

        # Debug/Evaluation Parameters
        self.color_comparison_average_greens_score = 0
        self.color_comparison_average_reds_score = 0
        self.color_comparison_average_greys_score = 0
        self.color_comparison_greens = 0
        self.color_comparison_reds = 0
        self.color_comparison_greys = 0

    def apply(self, blobs, raw_image, bg_subtraction_image, frame_number):
        """
        For every blob, detect the corresponded tracked object and update it
        with the new information
        :param blobs: List of new blobs detected
        :param raw_image: The raw image captured
        :param frame_number: The actual frame number of the video/stream
        :return: A list of TrackInfo which journey is greater than 5
        """

        journeys = []
        comparisons_by_color = []

        frames_from_previous_execution = frame_number - self.last_frame
        self.last_frame = frame_number

        for kf in self.k_filters:
            # Amount of frames it has been without a one to one relationship
            frames_without_one_to_one = self.last_frame - kf.last_frame_update
            if frames_without_one_to_one <= self.valid_frames_to_predict_position:
                # predict position of kfs without one at one relationship for a valid time frame
                for i in range(0, frames_from_previous_execution):
                    kf.calc_predicted_state()

        if len(blobs) > 0:
            for item in self.kfs_per_blob:
                item['blobs'] = []
                item['has_been_assigned'] = False

            for blob in blobs:
                blob["color"], image = get_color_aux(raw_image, bg_subtraction_image, blob["box"])

            # Apply hungarian algorithm for blob position
            best_kf_per_blob_pos, best_kf_per_blob_pos_costs = self.primary_hung_alg_comparison(blobs, self.k_filters)

            group_per_blob = []

            # Blobs are assigned to the nearest kalman filter (one kalman filter per blob)
            for i, blob in enumerate(blobs):
                blob["id"] = i
                best_kf = best_kf_per_blob_pos[i]
                if best_kf != -1:
                    kf = self.k_filters[best_kf]
                    self.kfs_per_blob[kf.group_number]['blobs'].append((blob, i))
                    self.kfs_per_blob[kf.group_number]['has_been_assigned'] = True
                    group_per_blob.append(kf.group_number)
                else:
                    # this is the result of a new blob (shaped like a person) in the scene
                    # new kalman filter is created for the blob
                    best_kf = self.add_new_tracking(blob, frame_number,
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
                        # Amount of frames it has been without a one to one relationship
                        frames_without_one_to_one = self.last_frame - kf.last_frame_update
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
                        elif frames_without_one_to_one < self.valid_frames_to_predict_position:
                            # It has been with one to one recently. It is left only with prediction.
                            kf.update_pos_info_with_no_measure_confidence(frame_number)

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
                        kf.update_info(blob=blob, last_frame_update=frame_number,
                                       raw_image=raw_image, bg_subtraction_image=bg_subtraction_image)
                    elif len(item_kf) > 1:
                        # merged blobs: many kalman filters on one blob
                        # kalman filters are updated only with the blob position

                        self.remove_or_update_kalman_filters(i, frame_number, item_kf, blob,
                                                             kf_to_remove, items_to_remove,
                                                             raw_image, bg_subtraction_image)

                elif len(item_blobs) > 1:
                    if len(item_kf) >= len(item_blobs):
                        # blobs that were merged have been split
                        # color, size, and any appearance comparisons are made to match blobs to  kalman filter(s)
                        # there must be no kalman filters left alone either

                        unassigned_blobs = []
                        unassigned_blobs_aux = []
                        for j, blob in enumerate(item_blobs):
                            unassigned_blobs.append((blob, j))
                            unassigned_blobs_aux.append(blob[0])

                        kfs_to_compare = []
                        kfs_to_compare_later = []

                        for j, kf in enumerate(item_kf):
                            # Amount of frames it has been without a one to one relationship
                            frames_without_one_to_one = self.last_frame - kf.last_frame_update
                            if frames_without_one_to_one <= self.valid_frames_to_predict_position:
                                # If it has been without one to one for a short time, compare by position
                                kfs_to_compare.append((kf, j))
                            else:
                                # If it has been without one to one for a long time, compare by color
                                kfs_to_compare_later.append((kf, j))

                        choose_worst_fit_blob = False
                        kf_to_remove_in_item = []
                        blob_to_remove_in_item = []
                        if len(kfs_to_compare) > 0:
                            # the blobs position are compared with all kfs with valid position comparison
                            # for each match, both go to a new group
                            # if all blobs are matched with valid kfs, the worst match keeps the remaining kfs

                            kfs_to_compare_aux = np.asarray(kfs_to_compare)
                            best_filter_per_blob, best_filter_per_blob_costs = \
                                self.primary_hung_alg_comparison(unassigned_blobs_aux, kfs_to_compare_aux[0:, 0])

                            # if more kalman filters than blobs, the worst fitting blob keeps the remaining filters
                            if len(item_kf) > len(unassigned_blobs):
                                choose_worst_fit_blob = True

                            aux_kfs_to_remove, aux_blobs_to_remove = self.get_nearest_blobs(groups_to_append, raw_image,
                                                                                            bg_subtraction_image,
                                                                                            frame_number,
                                                                                            unassigned_blobs,
                                                                                            kfs_to_compare,
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

                            # unassigned blobs are compared by color with remaining kfs,
                            # including with kfs with valid position comparison that were not matched
                            unassigned_blobs_aux = []
                            for blob in unassigned_blobs:
                                unassigned_blobs_aux.append(blob[0][0])

                            kfs_to_compare_aux = np.asarray(kfs_to_compare)
                            best_filter_per_blob, best_filter_per_blob_costs = \
                                self.secondary_hung_alg_comparison(unassigned_blobs_aux, kfs_to_compare_aux[0:, 0])

                            # if more kalman filters than blobs, the worst fitting blob keeps the remaining filters
                            if len(kfs_to_compare) > len(unassigned_blobs):
                                choose_worst_fit_blob = True

                            aux_kfs_to_remove, aux_blobs_to_remove = self.get_nearest_blobs(groups_to_append, raw_image,
                                                                                            bg_subtraction_image,
                                                                                            frame_number,
                                                                                            unassigned_blobs,
                                                                                            kfs_to_compare,
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
                                                                 kf_to_remove, items_to_remove,
                                                                 raw_image, bg_subtraction_image)

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
                journeys.append((kf.get_journey(), kf.journey_color, kf.short_id,
                                 kf.rectangle, kf.get_state_post(), False,
                                 self.kfs_per_blob[kf.group_number]['color']))

            if SHOW_COMPARISONS_BY_COLOR:
                comparisons_by_color = self.get_image_of_comparisons_by_color(raw_image,
                                                                              bg_subtraction_image,
                                                                              blobs)

        return journeys, [kf.to_dict() for kf in self.k_filters], \
            {k.id: k for k in self.k_filters}, comparisons_by_color

    def add_new_tracking(self, blob, frame_number, raw_image, bg_subtraction_image):
        """
        Add a new instance of KalmanFilter and the corresponding metadata
        to the control collection.

        :param size:
        :param color:
        :return:
        """
        track_info = TrackInfo(self.tracklets_short_id, blob,
                               frame_number, self.frames_per_second,
                               raw_image, bg_subtraction_image)
        self.k_filters.append(track_info)

        self.tracklets_short_id += 1

        return len(self.k_filters) - 1

    def remove_or_update_kalman_filters(self, item_id, frame_number, kalman_filters, blob,
                                        kf_to_remove, items_to_remove, image, bg_sub_image):

        # first of all, remove the kalman filters that are no longer valid
        kf_to_remove_in_item = []
        for j, kf in enumerate(kalman_filters):
            # Amount of frames it has been without a one to one relationship
            frames_without_one_to_one = self.last_frame - kf.last_frame_update
            # Amount of frames since it has been created
            frames_since_created = self.last_frame - kf.created_frame
            if frames_without_one_to_one > self.valid_frames_without_update:
                # If TrackInfo is too old, remove it forever
                kf_to_remove_in_item.append({"index": j, "kf": kf})
            elif frames_since_created < self.valid_frames_since_created:
                # it has been created a very short time ago: remove it
                kf_to_remove_in_item.append({"index": j, "kf": kf})

        kf_to_remove.extend(kf_to_remove_in_item)

        # Remove the old tracked objects
        for x in reversed(kf_to_remove_in_item):
            kalman_filters.pop(x["index"])

        if len(kalman_filters) == 0:
            items_to_remove.append(item_id)
        elif len(kalman_filters) == 1:
            # normal case: one on one
            # kalman filter is updated with all the blob info
            kf = kalman_filters[0]
            kf.update_info(blob=blob, last_frame_update=frame_number,
                           raw_image=image, bg_subtraction_image=bg_sub_image)
        else:
            for kf in kalman_filters:
                # Amount of frames it has been without a one to one relationship
                frames_without_one_to_one = self.last_frame - kf.last_frame_update
                if frames_without_one_to_one > self.valid_frames_to_predict_position:
                    # If it has been without one to one for a long time, correct with the merged blob
                    kf.update_with_medium_measure_confidence(new_position=blob["position"].pt,
                                                             frame_number=frame_number)
                else:
                    # It has been with one to one recently. It is left only with prediction.
                    kf.update_pos_info_with_no_measure_confidence(frame_number)

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
                          blobs, filters, best_filter_per_blob,
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
                    blob, blob_index = blobs[j][0]
                    kf = filters[kf_ind][0]
                    # this blob has to go to a new group, with the assigned kalman filter
                    groups.\
                        append({'k_filters': [kf],
                                'blobs': [(blob, blob_index)],
                                'color': (random.randint(0, 255),
                                          random.randint(0, 255),
                                          random.randint(0, 255))})

                    # kalman filter is updated with all the blob info
                    kf.update_info(blob=blob, last_frame_update=frame_number,
                                   raw_image=raw_image, bg_subtraction_image=bg_subtraction_image)

                    blob_to_remove_in_item.append(blobs[j][1])
                    kf_to_remove_in_item.append(filters[kf_ind][1])

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

        filters_to_remove.sort()
        # Remove the moved tracked objects
        for x in reversed(filters_to_remove):
            filters.pop(x)

        return kf_to_remove_in_item, blob_to_remove_in_item

    def primary_hung_alg_comparison(self, blobs, filters):
        weights = PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS
        return self.hung_alg_with_scores.apply(blobs, filters, weights)

    def secondary_hung_alg_comparison(self, blobs, filters):
        weights = SECONDARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS
        return self.hung_alg_with_scores.apply(blobs, filters, weights)

    def get_image_of_comparisons_by_color(self, raw_image, bg_subtraction_image, blobs):

        colors = []
        images = []
        for blob in blobs:
            color, image = get_color_aux(raw_image, bg_subtraction_image, blob["box"])
            colors.append(color)
            images.append(image)

        best_filter_per_blob = []
        best_filter_per_blob_costs = []
        if SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION:
            best_filter_per_blob, best_filter_per_blob_costs = \
                self.hung_alg_blob_previous_color.apply(colors, self.k_filters)

        image_to_add_in_width = []
        if SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION:
            width_to_add = 480
        else:
            width_to_add = 540 - len(self.k_filters[:9]) * 60
        if width_to_add > 0:
            image_to_add_in_width = np.zeros((120, width_to_add, 3), np.uint8)

        resized_images = []
        resized_kf_images = []
        for image in images:
            resized_images.append(cv2.resize(image, (60, 120)))  # (min_width, min_height)))
        for kf in self.k_filters:
            resized_kf_images.append(cv2.resize(kf.previous_image, (60, 120)))

        rows_filled = 0
        comparisons_by_color_aux = []
        for i, blob in enumerate(blobs):
            resized_blob_image = resized_images[i]  # resized_kf_image = cv2.resize(kf.image, (60, 120))

            if SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION:
                sorted_comparisons = []
                if best_filter_per_blob[i] != -1:
                    sorted_comparisons.append((best_filter_per_blob[i], best_filter_per_blob_costs[i]))
            else:
                color_comparisons = []
                for j, kf in enumerate(self.k_filters):
                    res = compare_color_aux(colors[i], kf.previous_color)
                    color_comparisons.append((j, res))
                sorted_comparisons = sorted(color_comparisons, key=lambda comp_item: comp_item[1])[:9]

            show = True
            if len(sorted_comparisons) > 0:
                blobs_in_best_kf_group = \
                    self.kfs_per_blob[self.k_filters[sorted_comparisons[0][0]].group_number]['blobs']
            else:
                blobs_in_best_kf_group = []
            if len(blobs_in_best_kf_group) > 0:
                if i == blobs_in_best_kf_group[0][0]['id']:
                    cv2.rectangle(resized_blob_image, (0, 0), (3, 120), (0, 255, 0), -1)
                    self.color_comparison_greens += 1
                    self.color_comparison_average_greens_score += sorted_comparisons[0][1]
                    print("Green color comparison: ", sorted_comparisons[0][1])
                    if not SHOW_COMPARISONS_BY_COLOR_GREEN:
                        show = False
                    else:
                        if SHOW_COMPARISONS_BY_COLOR_ONLY_NON_ZERO:
                            if sorted_comparisons[0][1] == 0:
                                show = False
                else:
                    cv2.rectangle(resized_blob_image, (0, 0), (3, 120), (0, 0, 255), -1)
                    self.color_comparison_reds += 1
                    self.color_comparison_average_reds_score += sorted_comparisons[0][1]
                    print("Red color comparison: ", sorted_comparisons[0][1])
                    if not SHOW_COMPARISONS_BY_COLOR_RED:
                        show = False
                    else:
                        if SHOW_COMPARISONS_BY_COLOR_ONLY_NON_ZERO:
                            if sorted_comparisons[0][1] == 0:
                                show = False
            else:
                cv2.rectangle(resized_blob_image, (0, 0), (3, 120), (100, 100, 100), -1)
                if len(sorted_comparisons) > 0:
                    self.color_comparison_greys += 1
                    self.color_comparison_average_greys_score += sorted_comparisons[0][1]
                    print("Grey color comparison: ", sorted_comparisons[0][1])
                if not SHOW_COMPARISONS_BY_COLOR_GREY:
                    show = False
                else:
                    if SHOW_COMPARISONS_BY_COLOR_ONLY_NON_ZERO and len(sorted_comparisons) > 0:
                        if sorted_comparisons[0][1] == 0:
                            show = False

            if show:
                rows_filled += 1
                x_axis_images = [resized_blob_image]
                if SHOW_COMPARISONS_BY_COLOR_GLOBAL_BETTER_DECISION and len(sorted_comparisons) == 0:
                    x_axis_images.append(np.zeros((120, 60, 3), np.uint8))
                else:
                    for comp in sorted_comparisons:
                        x_axis_images.append(cv2.putText(resized_kf_images[comp[0]],
                                                         '{0:.3f}'.format(comp[1]), (0, 20),
                                                         cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 255, 0), 1))
                if len(image_to_add_in_width) > 0:
                    x_axis_images.append(image_to_add_in_width)
                comparisons_by_color_aux.append(np.hstack(x_axis_images))

        comparisons_by_color = []
        if rows_filled > 0:
            image_to_add_in_height = []
            height_to_add = 960 - rows_filled * 120
            if height_to_add > 0:
                image_to_add_in_height = np.zeros((height_to_add, 600, 3), np.uint8)

            if len(image_to_add_in_height) > 0:
                comparisons_by_color_aux.append(image_to_add_in_height)
            if len(comparisons_by_color_aux) > 0:
                comparisons_by_color = np.vstack(comparisons_by_color_aux[:8])

                green_percentage = 0
                color_comparison_amount = self.color_comparison_greens + self.color_comparison_reds
                if color_comparison_amount:
                    green_percentage = self.color_comparison_greens * 100 / color_comparison_amount

                greens_average_score = 0
                if self.color_comparison_greens > 0:
                    greens_average_score = self.color_comparison_average_greens_score / self.color_comparison_greens
                reds_average_score = 0
                if self.color_comparison_reds > 0:
                    reds_average_score = self.color_comparison_average_reds_score / self.color_comparison_reds
                greys_average_score = 0
                if self.color_comparison_greys > 0:
                    greys_average_score = self.color_comparison_average_greys_score / self.color_comparison_greys

                cv2.putText(comparisons_by_color, '{0:.2f}%'.format(green_percentage), (200, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 3)
                cv2.putText(comparisons_by_color, '{0:.2f}'.format(greens_average_score), (200, 350),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 1)
                cv2.putText(comparisons_by_color, '{0:.2f}'.format(reds_average_score), (200, 400),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)
                cv2.putText(comparisons_by_color, '{0:.2f}'.format(greys_average_score), (200, 450),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 1)

        return comparisons_by_color


class TrackInfo:

    def __init__(self, short_id, blob, frame_number,
                 fps, raw_image, bg_subtraction_image):

        self.fps = fps

        self.id = uuid4().hex
        self.short_id = short_id
        self.size = blob["position"].size
        self.created_datetime = datetime.now()
        self.created_frame = frame_number
        self.initial_position = blob["position"].pt
        self.last_frame_update = frame_number
        self.last_frame_not_alone = frame_number
        self.last_frame_predicted = frame_number
        self.last_update = self.created_datetime
        self.last_point = self.initial_position
        self.group_number = -1
        self.score = blob['score']

        self.rectangle = blob["box"]
        self.previous_color, self.previous_image = get_color_aux(raw_image, bg_subtraction_image, self.rectangle)
        self.color = self.previous_color
        self.image = self.previous_image

        if JOURNEYS_RANDOM_COLOR:
            self.journey_color = (random.randint(0, 255), random.randint(0, 255),
                                  random.randint(0, 255))
        else:
            self.journey_color = self.color

        self.number_updates = 1

        self.frames_between_last_two_updates = 1.0

        time_interval = self.frames_between_last_two_updates / self.fps
        acceleration_change = time_interval * time_interval / 2

        f_matrix = np.array([[1, time_interval, acceleration_change, 0,             0,                   0],
                             [0,             1,       time_interval, 0,             0,                   0],
                             [0,             0,                   1, 0,             0,                   0],
                             [0,             0,                   0, 1, time_interval, acceleration_change],
                             [0,             0,                   0, 0,             1,       time_interval],
                             [0,             0,                   0, 0,             0,                   1]
                             ], np.float32)

        q_matrix = np.eye(N=6, dtype=np.float32)

        h_matrix = np.array([[1, 0, 0, 0, 0, 0],
                             [0, 0, 0, 1, 0, 0]], np.float32)

        r_matrix = np.array([[VARIANCE_OF_MEASURES_NOISE, 0],
                             [0, VARIANCE_OF_MEASURES_NOISE]], np.float32)

        if KALMAN_FILTER_TYPE == 1:
            self.kalman_filter = cv2.KalmanFilter(6, 2, 0)

            x_array = np.array([[self.initial_position[0]], [0.0], [0.0],
                                [self.initial_position[1]], [0.0], [0.0]], np.float32)

            self.kalman_filter.statePost = x_array
            self.kalman_filter.transitionMatrix = f_matrix

            self.kalman_filter.measurementMatrix = h_matrix

            self.kalman_filter.measurementNoiseCov = r_matrix

            # Initialize the process noise matrix to the identity, in order to
            # only take into account the measurements in the first frames.
            # Process prediction is not taken into account in first frames, as...
            # ... there is not a good initial velocity prediction
            self.kalman_filter.processNoiseCov = q_matrix

            self.journey = []

            self.journey.append(np.array(x_array.copy()))
        else:
            self.kalman_filter = FixedLagSmoother(dim_x=6, dim_z=2, N=KALMAN_FILTER_SMOOTH_LAG)

            x_array = np.array([self.initial_position[0], 0.0, 0.0,
                                self.initial_position[1], 0.0, 0.0], np.float32)

            self.kalman_filter.x = x_array
            self.kalman_filter.F = f_matrix

            self.kalman_filter.H = h_matrix

            self.kalman_filter.R = r_matrix

            # The next four lines are to avoid the error "integer argument expected, got float"
            # when printing journey lines in the __main__.py file
            self.kalman_filter.P = self.kalman_filter.P.astype(dtype=np.float32)
            self.kalman_filter._I = self.kalman_filter._I.astype(dtype=np.float32)
            self.kalman_filter.residual = self.kalman_filter.residual.astype(dtype=np.float32)
            self.kalman_filter.x_s = self.kalman_filter.x_s.astype(dtype=np.float32)

            # Initialize the process noise matrix to the identity, in order to
            # only take into account the measurements in the first frames.
            # Process prediction is not taken into account in first frames, as...
            # ... there is not a good initial velocity prediction
            self.kalman_filter.Q = q_matrix

        self.predicted_state_np = x_array.copy()
        self.predicted_state = self.predicted_state_np.tolist()

    def __repr__(self):
        return "<TrackInfo color: %s, size: %s, last seen: %s, created: %s>" %\
               (self.color, self.size, self.last_update, self.created_datetime)

    def predict(self):
        self.kalman_filter.predict()

    def correct(self, measurement):
        correction = self.kalman_filter.correct(measurement)

        self.journey.append(np.array(correction.copy()))

        return correction

    def predict_and_correct(self, last_frame_number, measurement, has_confidence_in_measure):
        frames_from_last_update = last_frame_number - self.last_frame_predicted
        time_interval = frames_from_last_update / self.fps

        self.last_frame_predicted = last_frame_number

        if frames_from_last_update != self.frames_between_last_two_updates:
            self.frames_between_last_two_updates = frames_from_last_update

            acceleration_change = time_interval * time_interval / 2

            f_matrix = np.array([[1, time_interval, acceleration_change, 0,             0,                   0],
                                 [0,             1,       time_interval, 0,             0,                   0],
                                 [0,             0,                   1, 0,             0,                   0],
                                 [0,             0,                   0, 1, time_interval, acceleration_change],
                                 [0,             0,                   0, 0,             1,       time_interval],
                                 [0,             0,                   0, 0,             0,                   1]
                                 ], np.float32)

            if KALMAN_FILTER_TYPE == 1:
                self.kalman_filter.transitionMatrix = f_matrix
            else:
                self.kalman_filter.F = f_matrix

            if self.number_updates >= 5:
                # Var = variation of model between steps
                q = Q_discrete_white_noise(dim=3, dt=time_interval, var=0.05)
                aux_q = block_diag(q, q)
                q_matrix = np.array(aux_q, np.float32)

                if KALMAN_FILTER_TYPE == 1:
                    self.kalman_filter.processNoiseCov = q_matrix
                else:
                    self.kalman_filter.Q = q_matrix

        if KALMAN_FILTER_TYPE == 1:
            self.predict()
            # correction with the known new position
            self.correct(np.array(measurement, np.float32))
        else:
            self.kalman_filter.smooth(np.array(measurement, np.float32))

        if has_confidence_in_measure:
            self.number_updates += 1

            if self.number_updates == 3:
                # Use the information of the initial position and 5th update
                # new_position to initialize the kalman filter velocity.
                # Also, initialize the kalman filter process noise matrix.

                # Var = variation of model between steps
                q = Q_discrete_white_noise(dim=3, dt=time_interval, var=0.05)
                aux_q = block_diag(q, q)
                q_matrix = np.array(aux_q, np.float32)

                aux = (measurement[0] - self.initial_position[0],
                       measurement[1] - self.initial_position[1])

                # si avanza aux[0] pixeles (en eje x) en [last_frame_number - self.created_frame] frames
                # -> avanza aux[0] pixeles en [(last_frame_number - self.created_frame) / fps] segundos
                # -> avanza [ aux[0] / ((last_frame_number - self.created_frame) / fps) ] pixeles en 1 segundo
                # -> avanza [ aux[0] * fps / (last_frame_number - self.created_frame) ] pixeles en 1 segundo
                frames_since_created = last_frame_number - self.created_frame
                mult_factor = self.fps / frames_since_created

                if KALMAN_FILTER_TYPE == 1:
                    self.kalman_filter.processNoiseCov = q_matrix

                    self.kalman_filter.statePost[1] = aux[0] * mult_factor
                    self.kalman_filter.statePost[4] = aux[1] * mult_factor
                else:
                    self.kalman_filter.Q = q_matrix

                    self.kalman_filter.x[1] = aux[0] * mult_factor
                    self.kalman_filter.x[4] = aux[1] * mult_factor

    def update_last_frame(self, last_frame_update):
        self.last_frame_update = last_frame_update
        self.last_frame_not_alone = last_frame_update
        self.last_update = datetime.now()

    def update_info(self, blob, last_frame_update,
                    raw_image, bg_subtraction_image):

        if last_frame_update != self.last_frame_update:
            self.predict_and_correct(last_frame_update, blob["position"].pt, True)

            self.size = blob["position"].size
            self.last_frame_update = last_frame_update
            self.last_frame_not_alone = last_frame_update
            self.last_update = datetime.now()
            self.last_point = blob["position"].pt

            self.score = (self.score * self.number_updates + blob['score']) /\
                         (self.number_updates + 1)

            self.rectangle = blob["box"]

            # if color has not been set and there are at least 5 updates, calculate and set color
            # if (self.color is None) or (self.number_updates % 5 == 0):
            self.previous_color = self.color
            self.previous_image = self.image
            self.color, self.image = get_color_aux(raw_image, bg_subtraction_image, self.rectangle)
            if not JOURNEYS_RANDOM_COLOR:
                self.journey_color = self.color

    def update_pos_info(self, frame_number, new_position, has_confidence_in_measure):  # , last_frame_update):

        self.predict_and_correct(frame_number, new_position, has_confidence_in_measure)

        self.last_frame_not_alone = frame_number

        if new_position:
            self.last_point = new_position

    def update_pos_info_with_no_measure_confidence(self, frame_number):
        self.update_pos_info(frame_number,
                             self.get_predicted_state_position(),
                             False)

    def update_with_medium_measure_confidence(self, new_position, frame_number):
        r_matrix = np.array([[VARIANCE_OF_NON_TRUTHFUL_MEASURES_NOISE, 0],
                             [0, VARIANCE_OF_NON_TRUTHFUL_MEASURES_NOISE]], np.float32)
        if KALMAN_FILTER_TYPE == 1:
            self.kalman_filter.measurementNoiseCov = r_matrix
        else:
            self.kalman_filter.R = r_matrix

        self.update_pos_info(frame_number, new_position, False)

        r_matrix = np.array([[VARIANCE_OF_MEASURES_NOISE, 0],
                             [0, VARIANCE_OF_MEASURES_NOISE]], np.float32)
        if KALMAN_FILTER_TYPE == 1:
            self.kalman_filter.measurementNoiseCov = r_matrix
        else:
            self.kalman_filter.R = r_matrix

    def get_journey(self):
        if KALMAN_FILTER_TYPE == 1:
            journey = self.journey
        else:
            if len(self.kalman_filter.xSmooth) > KALMAN_FILTER_SMOOTH_LAG:
                journey = self.kalman_filter.xSmooth[0:-KALMAN_FILTER_SMOOTH_LAG]
            else:
                journey = []

        return journey

    def get_state_post(self):
        # Get the corrected state
        if KALMAN_FILTER_TYPE == 1:
            state_post = self.kalman_filter.statePost
        else:
            state_post = self.kalman_filter.x

        return state_post

    def calc_predicted_state(self):
        # Calculate the predicted state
        if KALMAN_FILTER_TYPE == 1:
            state_pre = np.dot(self.kalman_filter.transitionMatrix,
                               self.kalman_filter.statePost)
        else:
            state_pre = np.dot(self.kalman_filter.F,
                               self.kalman_filter.x)

        # Positions must be positive. They are pixels positions on the screen.
        # Otherwise, euclidean distance comparisons throw error.
        # If they are corrected, delete the following four lines.
        if state_pre[0] < 0:
            state_pre[0] = 0
        if state_pre[3] < 0:
            state_pre[3] = 0

        self.predicted_state_np = state_pre
        self.predicted_state = state_pre.tolist()

    def get_predicted_state_position(self):
        if KALMAN_FILTER_TYPE == 1:
            state_pre_pos = (self.predicted_state[0][0], self.predicted_state[3][0])
        else:
            state_pre_pos = (self.predicted_state[0], self.predicted_state[3])

        return state_pre_pos

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


def compare_color_aux(color1, color2):
    if USE_HISTOGRAMS_FOR_TRACKING:
        result = compare_color_histogram(HISTOGRAM_COMPARISON_METHOD,
                                         color1, color2)
    else:
        result = compare_color(color1, color2)
    return result


def get_color_aux(image, bg_subtraction_image, rect):
    if USE_HISTOGRAMS_FOR_TRACKING:
        color, cropped_image = get_color_histogram(image, bg_subtraction_image, rect)
    else:
        color, cropped_image = get_avg_color(image, bg_subtraction_image, rect)
    return color, cropped_image
