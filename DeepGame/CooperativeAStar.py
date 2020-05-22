#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Construct a CooperativeAStar class to compute
the lower bound of Player I’s minimum adversary distance
while Player II being cooperative.

Author: Min Wu
Email: min.wu@cs.ox.ac.uk
"""

import heapq
import collections
from FeatureExtraction import *
from basics import *


class CooperativeAStar:
    def __init__(self, idx, image, model, eta, tau, bounds=(0, 1)):
        self.IDX = idx
        self.IMAGE = image
        self.IMAGE_BOUNDS = bounds
        self.MODEL = model
        self.DIST_METRIC = eta[0]
        self.DIST_VAL = eta[1]
        self.TAU = tau
        self.LABEL, _ = self.MODEL.predict(self.IMAGE)
        self.mul=100

        feature_extraction = FeatureExtraction()
        self.PARTITIONS,self.kps = feature_extraction.word_seg(self.IMAGE)

        self.DIST_EVALUATION = {}
        self.ADV_MANIPULATION = ()
        self.Explored={}
        self.ADVERSARY_FOUND = None
        self.ADVERSARY = None

        self.current_d = [0]

        print("Distance metric %s, with bound value %s." % (self.DIST_METRIC, self.DIST_VAL))

    def target_pixels(self, image, pixels):
        # tau = self.TAU
        # model = self.MODEL
        (row, col, chl) = image.shape

        # img_batch = np.kron(np.ones((chl * 2, 1, 1, 1)), image)
        # atomic_manipulations = {}
        # manipulated_images = []
        # idx = 0
        # for (x, y) in pixels:
        #     changed_img_batch = img_batch.copy()
        #     for z in range(chl):
        #         atomic = (x, y, z, 1 * tau)
        #         changed_img_batch[z * 2] = self.atomic_manipulation(image, atomic)
        #         # changed_img_batch[z * 2, x, y, z] += tau
        #         atomic_manipulations.update({idx: atomic})
        #         idx += 1
        #         atomic = (x,  y, z, -1 * tau)
        #         changed_img_batch[z * 2 + 1] = self.atomic_manipulation(image, atomic)
        #         # changed_img_batch[z * 2 + 1, x, y, z] -= tau
        #         atomic_manipulations.update({idx: atomic})
        #         idx += 1
        #     manipulated_images.append(changed_img_batch)  # each loop append [chl*2, row, col, chl]
        #
        # manipulated_images = np.asarray(manipulated_images)  # [len(pixels), chl*2, row, col, chl]
        # manipulated_images = manipulated_images.reshape(len(pixels) * chl * 2, row, col, chl)

        atomic_manipulations = []
        manipulated_images = []
        for (x, y) in pixels:
            for z in range(chl):
                atomic = (x, y, z, 1 * self.TAU)
                valid, atomic_image = self.apply_atomic_manipulation(image, atomic)
                if valid is True:
                    manipulated_images.append(atomic_image)
                    atomic_manipulations.append(atomic)
                atomic = (x, y, z, -1 * self.TAU)
                valid, atomic_image = self.apply_atomic_manipulation(image, atomic)
                if valid is True:
                    manipulated_images.append(atomic_image)
                    atomic_manipulations.append(atomic)
        manipulated_images = np.asarray(manipulated_images)

        probabilities = self.MODEL.model.predict(manipulated_images)
        # probabilities shape(preturbs,31,84)
        # print(probabilities.shape)
        # softmax_logits = self.MODEL.softmax_logits(manipulated_images)

        for idx in range(len(manipulated_images)):
            if not diffImage(manipulated_images[idx], self.IMAGE) or not diffImage(manipulated_images[idx], image):
                continue
            cost = self.cal_distance(manipulated_images[idx], self.IMAGE)
            heuristic=self.cal_heuristic(probabilities[idx])
            estimation = cost + heuristic

            self.DIST_EVALUATION.update({self.ADV_MANIPULATION + atomic_manipulations[idx]: estimation})
        # print("Atomic manipulations of target pixels done.")

    def apply_atomic_manipulation(self, image, atomic):
        atomic_image = image.copy()
        chl = atomic[0:3]
        manipulate = atomic[3]
        atomic_list = [self.ADV_MANIPULATION[i:i + 4] for i in range(0, len(self.ADV_MANIPULATION), 4)]
        length=len(atomic_list)

        # fixes loops
        for a in atomic_list:
            if (a[0:3]==chl) and (a[3]==-manipulate):
                valid=False
                return valid, atomic_image

        # disallow permutations of explored manipulations

        # atomic_list.append(atomic)
        # atoctr=collections.Counter(atomic_list)
        # if length in self.Explored.keys():
        #     for ato in self.Explored[length]:
        #         dif=atoctr-collections.Counter(ato)
        #         if sum(dif.values())==1:
        #             valid=False
        #             return valid, atomic_image

        if (atomic_image[chl] >= max(self.IMAGE_BOUNDS) and manipulate >= 0) or (
                atomic_image[chl] <= min(self.IMAGE_BOUNDS) and manipulate <= 0):
            valid = False
            return valid, atomic_image
        else:
            if atomic_image[chl] + manipulate > max(self.IMAGE_BOUNDS):
                atomic_image[chl] = max(self.IMAGE_BOUNDS)
            elif atomic_image[chl] + manipulate < min(self.IMAGE_BOUNDS):
                atomic_image[chl] = min(self.IMAGE_BOUNDS)
            else:
                atomic_image[chl] += manipulate
            valid = True
            return valid, atomic_image

    def cal_distance(self, image1, image2):
        if self.DIST_METRIC == 'L0':
            return l0Distance(image1, image2)
        elif self.DIST_METRIC == 'L1':
            return l1Distance(image1, image2)
        elif self.DIST_METRIC == 'L2':
            return l2Distance(image1, image2)
        else:
            print("Unrecognised distance metric. "
                  "Try 'L0', 'L1', or 'L2'.")

    def cal_heuristic(self,probabilities):
        diffs = []
        for i in range(probabilities.shape[0]):
            frame = probabilities[i]
            [p4, p3, p2, p1] = frame.argsort()[-4:]
            if p1 == 83:
                if i == 0:
                    if p2 == probabilities[i + 1].argmax():
                        diffs.append(frame[p1] - frame[p3])
                    else:
                        diffs.append(frame[p1] - frame[p2])
                if i == (probabilities.shape[0] - 1):
                    if p2 == probabilities[i - 1].argmax():
                        diffs.append(frame[p1] - frame[p3])
                    else:
                        diffs.append(frame[p1] - frame[p2])
                else:
                    if p2 == probabilities[i - 1].argmax() or p2 == probabilities[i + 1].argmax():
                        if p3 == probabilities[i - 1].argmax() or p3 == probabilities[i + 1].argmax():
                            diffs.append(frame[p1] - frame[p4])
                        else:
                            diffs.append(frame[p1] - frame[p3])
                    else:
                        diffs.append(frame[p1] - frame[p2])
            else:
                if i == 0:
                    if p1 == probabilities[i + 1].argmax():
                        if p2 == 83:
                            diffs.append(frame[p1] - frame[p3])
                            diffs.append(self.cal_distance([frame[p1], probabilities[i + 1].max()],
                                                           [frame[p2], probabilities[i + 1][83]]))
                        else:
                            diffs.append(frame[p1] - frame[p2])
                    else:
                        diffs.append(frame[p1] - frame[p2])
                if i == (probabilities.shape[0] - 1):
                    if p1 == probabilities[i - 1].argmax():
                        if p2 == 83:
                            diffs.append(frame[p1] - frame[p3])
                            diffs.append(self.cal_distance([frame[p1], probabilities[i - 1].max()],
                                                           [frame[p2], probabilities[i - 1][83]]))
                        else:
                            diffs.append(frame[p1] - frame[p2])
                    else:
                        diffs.append(frame[p1] - frame[p2])
                else:
                    if p1 == probabilities[i - 1].argmax() and p1 == probabilities[i + 1].argmax():
                        diffs.append(frame[p1] - frame[p2])
                    elif p1 == probabilities[i - 1].argmax():
                        diffs.append(self.cal_distance([frame[p1], probabilities[i - 1].max()],
                                                       [frame[p2], probabilities[i - 1][p2]]))
                        if p2 == 83:
                            if p3 == probabilities[i + 1].argmax():
                                diffs.append(frame[p1] - frame[p4])
                            else:
                                diffs.append(frame[p1] - frame[p3])
                        elif p2 == probabilities[i + 1].argmax():
                            if p3 == 83:
                                diffs.append(frame[p1] - frame[p4])
                            else:
                                diffs.append(frame[p1] - frame[p3])
                        else:
                            diffs.append(frame[p1] - frame[p2])
                    elif p1 == probabilities[i + 1].argmax():
                        diffs.append(self.cal_distance([frame[p1], probabilities[i + 1].max()],
                                                       [frame[p2], probabilities[i + 1][p2]]))
                        if p2 == 83:
                            if p3 == probabilities[i - 1].argmax():
                                diffs.append(frame[p1] - frame[p4])
                            else:
                                diffs.append(frame[p1] - frame[p3])
                        elif p2 == probabilities[i - 1].argmax():
                            if p3 == 83:
                                diffs.append(frame[p1] - frame[p4])
                            else:
                                diffs.append(frame[p1] - frame[p3])
                        else:
                            diffs.append(frame[p1] - frame[p2])
                    else:
                        diffs.append(frame[p1] - frame[p2])

        smallest = min(diffs)
        heuristic = smallest * self.mul*self.TAU  # heuristic value determines Admissible (lb) or not (ub)
        return heuristic

    def add_to_exp(self,advatomic):
        atomic_list=[advatomic[i:i+4] for i in range(0,len(advatomic),4)]
        size=len(atomic_list)
        if size==0:
            pass
        elif size in self.Explored.keys():
            self.Explored[size].append(atomic_list)
        else:
            self.Explored[size]=[atomic_list]

    def play_game(self, image):
        new_image = copy.deepcopy(self.IMAGE)
        new_label, new_confidence = self.MODEL.predict(new_image)
        log=np.array([[]])
        temp=np.expand_dims(new_image, axis=0)
        probability=self.MODEL.model.predict(temp)
        print(self.cal_heuristic(probability[0]))

        itera=0
        curbest=0
        while self.cal_distance(self.IMAGE, new_image) <= self.DIST_VAL and new_label == self.LABEL:
            itera+=1
            for partitionID in self.PARTITIONS.keys():
                pixels = self.PARTITIONS[partitionID]
                self.target_pixels(new_image, pixels)
            self.add_to_exp(self.ADV_MANIPULATION)
            self.ADV_MANIPULATION = min(self.DIST_EVALUATION, key=self.DIST_EVALUATION.get)
            # print("Current best manipulations:", self.ADV_MANIPULATION)
            print('itera',itera)
            print("%s distance (estimated): %s" % (self.DIST_METRIC, self.DIST_EVALUATION[self.ADV_MANIPULATION]))
            self.DIST_EVALUATION.pop(self.ADV_MANIPULATION)

            new_image = copy.deepcopy(self.IMAGE)
            atomic_list = [self.ADV_MANIPULATION[i:i + 4] for i in range(0, len(self.ADV_MANIPULATION), 4)]
            for atomic in atomic_list:
                valid, new_image = self.apply_atomic_manipulation(new_image, atomic)
            dist = self.cal_distance(self.IMAGE, new_image)
            print("%s distance (actual): %s" % (self.DIST_METRIC, dist))

            if dist>curbest:
                curbest=dist
                if itera==1:
                    log=np.array([[itera,dist]])
                else:
                    log=np.append(log,np.array([[itera,dist]]),axis=0)
                np.savetxt("lb/coop/adv/%sdatalog.csv" % (self.IDX), log, delimiter=",")
                self.MODEL.save_input(new_image, "lb/coop/idx_%s_currentBest_%s.png" % (self.IDX,itera))
                self.MODEL.save_input(np.absolute(new_image - self.IMAGE),
                                  "lb/coop/idx_%s_diff_%s.png" % (self.IDX,itera),mul=50)

            new_label, new_confidence = self.MODEL.predict(new_image)
            if self.cal_distance(self.IMAGE, new_image) > self.DIST_VAL:
                # print("Adversarial distance exceeds distance bound.")
                self.ADVERSARY_FOUND = False
                break
            elif new_label != self.LABEL:
                # print("Adversarial image is found.")
                self.ADVERSARY_FOUND = True
                self.ADVERSARY = new_image
                break


"""
    def play_game(self, image):
        self.player1(image)

        self.ADV_MANIPULATION = min(self.DIST_EVALUATION, key=self.DIST_EVALUATION.get)
        self.DIST_EVALUATION.pop(self.ADV_MANIPULATION)
        print("Current best manipulations:", self.ADV_MANIPULATION)

        new_image = copy.deepcopy(self.IMAGE)
        atomic_list = [self.ADV_MANIPULATION[i:i + 4] for i in range(0, len(self.ADV_MANIPULATION), 4)]
        for atomic in atomic_list:
            valid, new_image = self.apply_atomic_manipulation(new_image, atomic)
        print("%s distance: %s" % (self.DIST_METRIC, self.cal_distance(self.IMAGE, new_image)))

        new_label, new_confidence = self.MODEL.predict(new_image)
        if self.cal_distance(self.IMAGE, new_image) > self.DIST_VAL:
            # print("Adversarial distance exceeds distance bound.")
            self.ADVERSARY_FOUND = False
        elif new_label != self.LABEL:
            # print("Adversarial image is found.")
            self.ADVERSARY_FOUND = True
            self.ADVERSARY = new_image
        else:
            self.play_game(new_image)

    def player1(self, image):
        # print("Player I is acting on features.")

        for partitionID in self.PARTITIONS.keys():
            self.player2(image, partitionID)

    def player2(self, image, partition_idx):
        # print("Player II is acting on pixels in each partition.")

        pixels = self.PARTITIONS[partition_idx]
        self.target_pixels(image, pixels)
"""
