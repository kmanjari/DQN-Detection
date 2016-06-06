import tensorflow as tf
import numpy as np
import os

from .dataset import Dataset
from .memory import Memory

class State(object):
    def __init__(self, img_id, height, width):
        self.img_id = img_id
        self.height, self.width = width 
        # box = [left, top, right, down]
        self.box = [1, 1, self.height, self.width]  

    def clip_box(self):
        self.box[0] = max(self.box[0], 1)
        self.box[1] = max(self.box[1], 1)
        self.box[2] = min(self.box[2], self.width)
        self.box[3] = min(self.box[3], self.height)

        self.img_id = val.img_id

class Env(object):
    def __init__(self, config):
        self.data = Dataset(config.train_dir, config.train_ano_dir, config.test_dir, config.test_ano_dir)
        self.cur_img = 0
        self.train_set_size = self.train_size
        self.alpha = config.alpha 
        self.state = None
        self.action_size = 8
        self.IoU = 0.0
        self.accept_rate = config.accept_rate
        self.eps = config.eps
        self.define_act()
    
    def _act(self, action):
        self.move[str(action)]()
        self.state.clip_box()
        self._calc_IoU()
    def _calc_area(self, box):
        return (box[2] - box[0]) * (box[3] - box[1])
    def _isIntersect(self, box, gt):
        if box[0] >= gt[2]:
            return False
        if box[2] <= gt[0]:
            return False
        if box[1] >= gt[3]:
            return False
        if box[3] <= gt[1]:
            return False
        return True
    def _calc_IoU(self):
        gt = self.data.ground_truth[cur_img]
        box = self.state.box
        if self._isIntersect(box, gt):
            inter = [max(box[0], gt[0]), max(box[1], gt[1]), min(box[2], gt[2]), min(box[3], gt[3])]
            interArea = self._calc_area(inter)
            self.IoU = (1. * interArea) / (self._calc_area(box) + self._calc_area(gt) - interArea + 0.)
        else:
            self.IoU = 0.0

    def define_act(self):
        self.move = {}
        self.move['0'] = self.move_left
        self.move['1'] = self.move_right
        self.move['2'] = self.move_up
        self.move['3'] = self.move_down
        self.move['4'] = self.bigger
        self.move['5'] = self.smaller
        self.move['6'] = self.fatter
        self.move['7'] = self.taller

    def move_left(self):
        self.state.box[0] -= self.alpha
        self.state.box[2] -= self.alpha
    def move_right(self):
        self.state.box[0] += self.alpha
        self.state.box[2] += self.alpha
    def move_up(self):
        self.state.box[1] -= self.alpha
        self.state.box[3] -= self.alpha
    def move_down(self):
        self.state.box[1] += self.alpha
        self.state.box[3] += self.alpha
    def bigger(self):
        delta_x = ((self.state.box[0] + self.state.box[2]) * 0.5 - self.state.box[0]) * self.alpha
        delta_y = ((self.state.box[1] + self.state.box[3]) * 0.5 - self.state.box[1]) * self.alpha
        delta_x = int(delta_x)
        delta_y = int(delta_y)
        self.state.box[0] -= delta_x
        self.state.box[2] += delta_x
        self.state.box[1] -= delta_y
        self.state.box[3] += delta_y
    def smaller(self):
        delta_x = ((self.state.box[0] + self.state.box[2]) * 0.5 - self.state.box[0]) * self.alpha
        delta_y = ((self.state.box[1] + self.state.box[3]) * 0.5 - self.state.box[1]) * self.alpha
        delta_x = int(delta_x)
        delta_y = int(delta_y)
        self.state.box[0] += delta_x
        self.state.box[2] -= delta_x
        self.state.box[1] += delta_y
        self.state.box[3] -= delta_y
    def fatter(self):
        delta_y = ((self.state.box[1] + self.state.box[3]) * 0.5 - self.state.box[1]) * self.alpha
        delta_y = int(delta_y)
        self.state.box[1] += delta_y
        self.state.box[3] -= delta_y
    def taller(self):
        delta_x = ((self.state.box[0] + self.state.box[2]) * 0.5 - self.state.box[0]) * self.alpha
        delta_x = int(delta_x)
        self.state.box[0] += delta_x
        self.state.box[2] -= delta_x

    def clear(self):
        self.cur_img = 0
    def reset(self, isTrain = True):
        if isTrain:
            self.state = State(self.cur_img, self.data.train_img[self.cur_img].shape[0], self.data.train_img[self.cur_img].shape[1])
            self.ground_truth = self.data.train_img_ano[self.cur_img]
            self.cur_img = (self.cur_img + 1) % self.train_size
        else:
            self.state = State(self.cur_img, self.data.test_img[self.cur_img].shape[0], self.data.test_img[self.cur_img].shape[1])
            self.ground_truth = self.data.test_img_ano[self.cur_img]
            self.cur_img += 1

    def _sign(self, x):
        return 1 if x >= self.eps else -1
    def _isTerminal(self):
        if self.IoU >= self.accept_rate:
            return True
        else:
            return False

    def act(self, action):
        pre_IoU = self.state.IoU
        self._act(action)
        self.
        return self.state, self._sign(self.IoU - pre_IoU), _isTerminal()
