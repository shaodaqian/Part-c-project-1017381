#!/usr/bin/env python

"""
A data structure for organising search

author: Xiaowei Huang
"""

import time
import os
import copy
import sys
import operator
import random
import math

from basics import *
from GameMoves import *

MCTS_multi_samples = 1
effectiveConfidenceWhenChanging = 0.0
explorationRate = math.sqrt(2)


class MCTSCompetitive:

    def __init__(self, data_set, model, image_index, image, tau, eta):
        self.data_set = data_set
        self.image_index = image_index
        self.image = image
        self.model = model
        self.tau = tau
        self.eta = eta

        (self.originalClass, self.originalConfident) = self.model.predict(self.image)

        self.moves = GameMoves(self.data_set, self.model, self.image, self.tau)

        self.cost = {}
        self.numberOfVisited = {}
        self.parent = {}
        self.children = {}
        self.children[-1] = {0}
        self.fullyExpanded = {}

        self.indexToNow = 0
        # current root node
        self.rootIndex = 0

        # maintain for every node on the tree the current best 
        self.bestCaseList = {}
        # best case for the root node 
        # please note the difference with the cooperative game 
        self.bestCase = (2 ^ 20, {})

        self.manipulation = {}
        # initialise root node
        self.manipulation[-1] = {}
        self.initialiseLeafNode(0, -1, {})
        self.bestCaseList[0] = (0, [])
        self.bestCaseList[-1] = (0, [])

        # record all the keypoints: index -> kp
        self.keypoints = {}
        # mapping nodes to keypoints
        self.keypoint = {}
        self.keypoint[-1] = 0
        self.keypoint[0] = 0

        # local actions
        self.actions = {}
        self.usedActionsID = {}
        self.indexToActionID = {}

        self.numConverge = 0


        # how many sampling is conducted
        self.numOfSampling = 0

        # number of adversarial examples
        self.numAdv = 0

        # temporary variables for sampling 
        self.atomicManipulationPath = []
        self.depth = 0
        self.availableActionIDs = []

    def initialiseMoves(self):
        # initialise actions according to the type of manipulations
        actions = self.moves.moves
        print((actions.keys()))
        self.keypoints[0] = 0
        i = 1
        for k in actions[0]:
            self.keypoints[i] = k
            i += 1

        for i in range(len(actions)):
            ast = {}
            for j in range(len(actions[i])):
                ast[j] = actions[i][j]
            self.actions[i] = ast
        nprint("%s actions have been initialised. " % (len(self.actions)))

    def initialiseLeafNode(self, index, parentIndex, newAtomicManipulation):
        nprint("initialising a leaf node %s from the node %s" % (index, parentIndex))
        self.manipulation[index] = mergeTwoDicts(self.manipulation[parentIndex], newAtomicManipulation)
        self.cost[index] = 0
        self.parent[index] = parentIndex
        self.children[index] = []
        self.fullyExpanded[index] = False
        self.numberOfVisited[index] = 0

        # activations1 = self.moves.applyManipulation(self.image,self.manipulation[index])

    def destructor(self):
        self.image = 0
        self.image = 0
        self.model = 0
        self.model = 0
        self.manipulatedDimensions = {}
        self.manipulation = {}
        self.cost = {}
        self.parent = {}
        self.children = {}
        self.fullyExpanded = {}
        self.numberOfVisited = {}

        self.actions = {}
        self.usedActionsID = {}
        self.indexToActionID = {}

    # move one step forward
    # it means that we need to remove children other than the new root
    def makeOneMove(self, newRootIndex):
        if self.keypoint[newRootIndex] != 0:
            player = "the first player"
        else:
            player = "the second player"
        print("%s making a move into the new root %s, whose value is %s and visited number is %s"
              % (player, newRootIndex, self.cost[newRootIndex], self.numberOfVisited[newRootIndex]))
        self.removeChildren(self.rootIndex, [newRootIndex])
        self.rootIndex = newRootIndex

    def removeChildren(self, index, indicesToAvoid):
        if self.fullyExpanded[index] is True:
            for childIndex in self.children[index]:
                if childIndex not in indicesToAvoid: self.removeChildren(childIndex, [])
        self.manipulation.pop(index, None)
        self.cost.pop(index, None)
        self.parent.pop(index, None)
        self.keypoint.pop(index, None)
        self.children.pop(index, None)
        self.fullyExpanded.pop(index, None)
        self.numberOfVisited.pop(index, None)

    def bestChild(self, index):
        allValues = {}
        for childIndex in self.children[index]:
            allValues[childIndex] = float(self.numberOfVisited[childIndex]) / self.cost[childIndex]
        nprint("finding best children from %s" % allValues)
        # for competitive
        return max(allValues.items(), key=operator.itemgetter(1))[0]

    def treeTraversal(self, index):
        if self.fullyExpanded[index] is True:
            print("tree traversal on node %s with childrens %s" % (index, self.children[index]))
            allValues = {}
            for childIndex in self.children[index]:
                # UCB values
                # allValues[childIndex] = ((float(self.numberOfVisited[childIndex]) / self.cost[childIndex]) * self.eta[1]
                #                          + explorationRate * math.sqrt(
                #             math.log(self.numberOfVisited[index]) / float(self.numberOfVisited[childIndex])))
                if self.fullyExpanded[childIndex] is False:
                    allValues[childIndex]=1/float(self.bestCaseList[childIndex][0])

            if self.keypoint[index] == 0:
                allValues2 = {}
                for k, v in allValues.items():
                    allValues2[k] = 1 / float(allValues[k])
                probdist = [x / sum(allValues2.values()) for x in allValues2.values()]
                # nextIndex = np.random.choice(list(allValues.keys()), 1, p=probdist)[0]
                nextIndex = list(allValues.keys())[probdist.index(max(probdist))]
            else:
                probdist = [x / sum(allValues.values()) for x in allValues.values()]
                # nextIndex = np.random.choice(list(allValues.keys()), 1, p=probdist)[0]
                nextIndex = list(allValues.keys())[probdist.index(max(probdist))]

            if self.keypoint[index] in self.usedActionsID.keys() and self.keypoint[index] != 0:
                self.usedActionsID[self.keypoint[index]].append(self.indexToActionID[index])
            elif self.keypoint[index] != 0:
                self.usedActionsID[self.keypoint[index]] = [self.indexToActionID[index]]

            return self.treeTraversal(nextIndex)

        else:
            print("tree traversal terminated on node %s" % index)
            availableActions = copy.deepcopy(self.actions)
            # for k in self.usedActionsID.keys():
            #    for i in self.usedActionsID[k]: 
            #        availableActions[k].pop(i, None)
            return index, availableActions

    def usefulAction(self, ampath, am):
        newAtomicManipulation = mergeTwoDicts(ampath, am)
        activations0 = self.moves.applyManipulation(self.image, ampath)
        x1 = np.expand_dims(activations0, axis=0)
        newConfident0 = self.model.model.predict(x1)
        activations1 = self.moves.applyManipulation(self.image, newAtomicManipulation)
        x2 = np.expand_dims(activations1, axis=0)
        newConfident1 = self.model.model.predict(x2)
        # print(l1Distance(newConfident0,newConfident1))
        # print(linfDistance(newConfident0,newConfident1))
        if (l1Distance(newConfident0,newConfident1)<0.003) and (linfDistance(newConfident0,newConfident1)<0.001):
            # print('no')
            return False
        else:
            # print('yes')
            return True


    def initialiseExplorationNode(self, index, availableActions):
        nprint("expanding %s" % index)
        self.datalog=[]
        if self.keypoint[index] != 0:
            count=0
            size=min(len(availableActions[self.keypoint[index]].items()),200)
            samples = random.sample(availableActions[self.keypoint[index]].items(),size)
            for (actionId, am) in samples:
                if count<11:
                    if self.usefulAction(self.manipulation[index], am) == True:
                        count+=1
                        self.indexToNow += 1
                        self.keypoint[self.indexToNow] = 0
                        self.indexToActionID[self.indexToNow] = actionId
                        self.initialiseLeafNode(self.indexToNow, index, am)
                        self.children[index].append(self.indexToNow)
                        self.bestCaseList[self.indexToNow] = (0, {})
                        print('number of children initialised', count)

        else:
            for kp in list(set(self.keypoints.keys()) - set([0])):
                self.indexToNow += 1
                self.keypoint[self.indexToNow] = kp
                self.indexToActionID[self.indexToNow] = 0
                self.initialiseLeafNode(self.indexToNow, index, {})
                self.children[index].append(self.indexToNow)
                self.bestCaseList[self.indexToNow] = (self.eta[1], {})

        self.fullyExpanded[index] = True
        self.usedActionsID = {}
        return self.children[index]

    def backPropagation(self, index, value):
        self.cost[index] += value
        self.numberOfVisited[index] += 1
        if self.parent[index] in self.parent:
            nprint("start backPropagating the value %s from node %s, whose parent node is %s" % (
                value, index, self.parent[index]))
            self.backPropagation(self.parent[index], value)
        else:
            nprint("backPropagating ends on node %s" % index)

    # start random sampling and return the Euclidean value as the value
    def sampling(self, index, availableActions):
        nprint("start sampling node %s" % index)
        availableActions2 = copy.deepcopy(availableActions)
        # availableActions2[self.keypoint[index]].pop(self.indexToActionID[index], None)
        sampleValues = []
        samplePaths = []
        if self.keypoint[index] == 0:
            self.atomicManipulationPath = self.manipulation[index]
            self.depth = 0
            self.availableActionIDs = {}
            for k in self.keypoints.keys():
                self.availableActionIDs[k] = list(availableActions2[k].keys())
            cur=random.choice(list(availableActions2[0].values()))
            (childTerminated, val) = self.sampleNext(cur)
            self.numOfSampling += 1
            sampleValues.append(val)
            samplePaths.append(self.atomicManipulationPath)
            minIndex = sampleValues.index(min(sampleValues))
            self.numConverge += 1
            self.bestCaseList[index] = (sampleValues[minIndex], samplePaths[minIndex])
                # update best case
            self.updateBestCase(index)
            return childTerminated, min(sampleValues)
        else:
            for i in range(MCTS_multi_samples):
                self.atomicManipulationPath = self.manipulation[index]
                self.depth = 0
                self.availableActionIDs = {}
                for k in self.keypoints.keys():
                    self.availableActionIDs[k] = list(availableActions2[k].keys())
                (childTerminated, val) = self.sampleNext(self.keypoint[index])
                self.numOfSampling += 1
                sampleValues.append(val)
                samplePaths.append(self.atomicManipulationPath)
                minIndex = sampleValues.index(min(sampleValues))
                # print(index, self.bestCaseList[index][0], min(sampleValues), self.eta)
                if self.bestCaseList[index][0] > sampleValues[minIndex]:
                    print("on node %s, update best case from %s to %s, start updating ancestor nodes" % (
                        index, self.bestCaseList[index][0], sampleValues[minIndex]))
                    self.numConverge += 1
                    self.bestCaseList[index] = (sampleValues[minIndex], samplePaths[minIndex])
                    # update best case
                    self.updateBestCase(index)
            return childTerminated, min(sampleValues)

    def computeDistance(self, newImage):
        (distMethod, _) = self.eta
        if distMethod == "L2":
            dist = l2Distance(newImage, self.image)
        elif distMethod == "L1":
            dist = l1Distance(newImage, self.image)
        elif distMethod == "Percentage":
            dist = diffPercent(newImage, self.image)
        elif distMethod == "NumDiffs":
            dist = diffPercent(newImage, self.image) * self.image.size
        return dist

    def sampleNext(self, k):
        orig = self.moves.applyManipulation(self.image, self.atomicManipulationPath)
        cur = k
        (distMethod, distVal) = self.eta

        while self.depth<1000:
            j=0
            while j<=10 :
                randomActionIndex = random.choice(self.availableActionIDs[cur])
                nextAtomicManipulation = self.actions[cur][randomActionIndex]
                j+= 1
                if self.usefulAction(self.atomicManipulationPath,nextAtomicManipulation) == True:
                    break
            # randomActionIndex = random.choice(self.availableActionIDs[cur])
            # nextAtomicManipulation = self.actions[cur][randomActionIndex]
            orig=self.moves.applyManipulation(orig,nextAtomicManipulation)
            self.atomicManipulationPath = mergeTwoDicts(self.atomicManipulationPath, nextAtomicManipulation)
            (newClass, newconfident) = self.model.predict(orig)
            self.depth += 1
            dist = self.computeDistance(orig)
            if newClass != self.originalClass:
                print("sampling a path ends in a terminal node with depth %s... " % self.depth)
                self.atomicManipulationPath = self.scrutinizePath(self.atomicManipulationPath)
                self.numAdv += 1
                newimg = self.moves.applyManipulation(self.image, self.atomicManipulationPath)
                dist = self.computeDistance(newimg)
                nprint("current best %s, considered to be replaced by %s" % (self.bestCase[0], dist))

                return (self.depth == 0, dist)

            elif dist > distVal:
                print("sampling a path ends by eta with depth %s ... " % self.depth)
                return (self.depth == 0, distVal)

            # self.atomicManipulationPath=mergeTwoDicts(self.atomicManipulationPath, nextAtomicManipulation)
            cur = random.choice(self.availableActionIDs[0])
            cur = self.actions[0][cur]

        return (self.depth == 0, distVal)

    def scrutinizePath(self, manipulations):
        flag = False
        tempManipulations = copy.deepcopy(manipulations)
        for k, v in manipulations.items():
            tempManipulations[k] = 0
            activations1 = self.moves.applyManipulation(self.image, tempManipulations)
            (newClass, newConfident) = self.model.predict(activations1)
            if newClass != self.originalClass:
                manipulations.pop(k)
                flag = True
                break

        if flag is True:
            return self.scrutinizePath(manipulations)
        else:
            return manipulations

    def terminalNode(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        (newClass, _) = self.model.predict(activations1)
        return newClass != self.originalClass

    def terminatedByEta(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        dist = self.computeDistance(activations1)
        nprint("terminated by controlled search: distance = %s" % dist)
        return dist > self.eta[1]

    def applyManipulation(self, manipulation):
        activations1 = self.moves.applyManipulation(self.image, manipulation)
        return activations1

    def l2Dist(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        return l2Distance(self.image, activations1)

    def l1Dist(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        return l1Distance(self.image, activations1)

    def l0Dist(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        return l0Distance(self.image, activations1)

    def diffImage(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        return diffImage(self.image, activations1)

    def diffPercent(self, index):
        activations1 = self.moves.applyManipulation(self.image, self.manipulation[index])
        return diffPercent(self.image, activations1)

    def updateBestCase(self, index):
        if index > 0:
            parentIndex = self.parent[index]
            if self.keypoint[parentIndex] == 0:
                tempVal = 0
                tempPath = []
                for childIndex in self.children[parentIndex]:
                    if self.bestCaseList[childIndex][0] > tempVal:
                        tempVal = self.bestCaseList[childIndex][0]
                        tempPath = self.bestCaseList[childIndex][1]
                self.bestCaseList[parentIndex] = (tempVal, tempPath)
            else:
                tempVal = self.eta[1]
                tempPath = []
                for childIndex in self.children[parentIndex]:
                    if self.bestCaseList[childIndex][0] < tempVal:
                        tempVal = self.bestCaseList[childIndex][0]
                        tempPath = self.bestCaseList[childIndex][1]
                self.bestCaseList[parentIndex] = (tempVal, tempPath)
            self.updateBestCase(parentIndex)
        else:

            if self.bestCase[0] != self.bestCaseList[0][0]:
                self.bestCase = self.bestCaseList[0]
                for childIndex in self.children[0]:
                    self.datalog.append([childIndex] + self.included_features(self.bestCaseList[childIndex][1]) + [
                        self.bestCaseList[childIndex][0]])
                print("the best case is updated into distance %s and manipulation %s" % (
                    self.bestCase[0], self.bestCase[1]))

    def bestFeatures(self):
        bestManipulation = self.bestCase[1]
        maxdims = []
        nf = 0
        for i in range(1, len(self.actions)):
            md = []
            flag = False
            for k, v in bestManipulation.items():
                for k1, v1 in self.actions[i].items():
                    md += list(v1.keys())
                    if k in v1.keys():
                        flag = True
            if flag is True:
                nf += 1
                maxdims += md
        if len(maxdims) == 0:
            return (0, 0)
        elif len(maxdims[0]) == 3:
            maxdims = [(x, y) for (x, y, z) in maxdims]
        return (nf, maxdims)

    def included_features(self,manipulation):
        features=[]
        for i in range (1,len(self.actions)):
            flag = 0
            for k,v in manipulation.items():
                for k1, v1 in self.actions[i].items():
                    if k in v1.keys():
                        flag+=1
            features.append(flag)
        return features