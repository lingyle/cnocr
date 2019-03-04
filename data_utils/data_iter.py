from __future__ import print_function

import os
from PIL import Image
import numpy as np
import mxnet as mx
import random


class SimpleBatch(object):
    def __init__(self, data_names, data, label_names=list(), label=list()):
        self._data = data
        self._label = label
        self._data_names = data_names
        self._label_names = label_names

        self.pad = 0
        self.index = None  # TODO: what is index?

    @property
    def data(self):
        return self._data

    @property
    def label(self):
        return self._label

    @property
    def data_names(self):
        return self._data_names

    @property
    def label_names(self):
        return self._label_names

    @property
    def provide_data(self):
        return [(n, x.shape) for n, x in zip(self._data_names, self._data)]

    @property
    def provide_label(self):
        return [(n, x.shape) for n, x in zip(self._label_names, self._label)]


# class ImageIter(mx.io.DataIter):
#
#     """
#     Iterator class for generating captcha image data
#     """
#     def __init__(self, data_root, data_list, batch_size, data_shape, num_label, name=None):
#         """
#         Parameters
#         ----------
#         data_root: str
#             root directory of images
#         data_list: str
#             a .txt file stores the image name and corresponding labels for each line
#         batch_size: int
#         name: str
#         """
#         super(ImageIter, self).__init__()
#         self.batch_size = batch_size
#         self.data_shape = data_shape
#         self.num_label  = num_label
#
#         self.data_root = data_root
#         self.dataset_lst_file = open(data_list)
#
#         self.provide_data = [('data', (batch_size, 1, data_shape[1], data_shape[0]))]
#         self.provide_label = [('label', (self.batch_size, self.num_label))]
#         self.name = name
#
#     def __iter__(self):
#         data = []
#         label = []
#         cnt = 0
#         for m_line in self.dataset_lst_file:
#             img_lst = m_line.strip().split(' ')
#             img_path = os.path.join(self.data_root, img_lst[0])
#
#             cnt += 1
#             img = Image.open(img_path).resize(self.data_shape, Image.BILINEAR).convert('L')
#             img = np.array(img).reshape((1, self.data_shape[1], self.data_shape[0]))
#             data.append(img)
#
#             ret = np.zeros(self.num_label, int)
#             for idx in range(1, len(img_lst)):
#                 ret[idx-1] = int(img_lst[idx])
#
#             label.append(ret)
#             if cnt % self.batch_size == 0:
#                 data_all = [mx.nd.array(data)]
#                 label_all = [mx.nd.array(label)]
#                 data_names = ['data']
#                 label_names = ['label']
#                 data.clear()
#                 label.clear()
#                 yield SimpleBatch(data_names, data_all, label_names, label_all)
#                 continue
#
#
#     def reset(self):
#         if self.dataset_lst_file.seekable():
#             self.dataset_lst_file.seek(0)

class ImageIterLstm(mx.io.DataIter):

    """
    Iterator class for generating captcha image data
    """

    def __init__(self, data_root, data_list, batch_size, data_shape, num_label, lstm_init_states, name=None):
        """
        Parameters
        ----------
        data_root: str
            root directory of images
        data_list: str
            a .txt file stores the image name and corresponding labels for each line
        batch_size: int
        name: str
        """
        super(ImageIterLstm, self).__init__()
        self.batch_size = batch_size
        self.data_shape = data_shape
        self.num_label = num_label

        self.init_states = lstm_init_states
        self.init_state_arrays = [mx.nd.zeros(x[1]) for x in lstm_init_states]

        self.data_root = data_root
        self.dataset_lines = open(data_list).readlines()

        self.provide_data = [('data', (batch_size, 1, data_shape[1], data_shape[0]))] + lstm_init_states
        self.provide_label = [('label', (self.batch_size, self.num_label))]
        self.name = name

    def __iter__(self):
        init_state_names = [x[0] for x in self.init_states]
        data = []
        label = []
        cnt = 0
        for m_line in self.dataset_lines:
            img_lst = m_line.strip().split(' ')
            img_path = os.path.join(self.data_root, img_lst[0])

            cnt += 1
            img = Image.open(img_path).resize(self.data_shape, Image.BILINEAR).convert('L')
            img = np.array(img).reshape((1, self.data_shape[1], self.data_shape[0]))
            data.append(img)

            ret = np.zeros(self.num_label, int)
            for idx in range(1, len(img_lst)):
                ret[idx - 1] = int(img_lst[idx])

            label.append(ret)
            if cnt % self.batch_size == 0:
                data_all = [mx.nd.array(data)] + self.init_state_arrays
                label_all = [mx.nd.array(label)]
                data_names = ['data'] + init_state_names
                label_names = ['label']
                data = []
                label = []
                yield SimpleBatch(data_names, data_all, label_names, label_all)
                continue

    def reset(self):
        # if self.dataset_lst_file.seekable():
        #     self.dataset_lst_file.seek(0)
        random.shuffle(self.dataset_lines)


class OCRIter(mx.io.DataIter):
    """
    Iterator class for generating captcha image data
    """
    def __init__(self, count, batch_size, lstm_init_states, captcha, name):
        """
        Parameters
        ----------
        count: int
            Number of batches to produce for one epoch
        batch_size: int
        lstm_init_states: list of tuple(str, tuple)
            A list of tuples with [0] name and [1] shape of each LSTM init state
        captcha MPCaptcha
            Captcha image generator. Can be MPCaptcha or any other class providing .shape and .get() interface
        name: str
        """
        super(OCRIter, self).__init__()
        self.batch_size = batch_size
        self.count = count
        self.init_states = lstm_init_states
        self.init_state_arrays = [mx.nd.zeros(x[1]) for x in lstm_init_states]
        data_shape = captcha.shape
        self.provide_data = [('data', (batch_size, 1, data_shape[1], data_shape[0]))] + lstm_init_states
        self.provide_label = [('label', (self.batch_size, 4))]
        self.mp_captcha = captcha
        self.name = name

    def __iter__(self):
        init_state_names = [x[0] for x in self.init_states]
        for k in range(self.count):
            data = []
            label = []
            for i in range(self.batch_size):
                img, num = self.mp_captcha.get()
                # print(img.shape)
                img = np.expand_dims(np.transpose(img, (1, 0)), axis=0)  # size: [1, channel, height, width]
                # import pdb; pdb.set_trace()
                data.append(img)
                label.append(self._get_label(num))
            data_all = [mx.nd.array(data)] + self.init_state_arrays
            label_all = [mx.nd.array(label)]
            data_names = ['data'] + init_state_names
            label_names = ['label']

            data_batch = SimpleBatch(data_names, data_all, label_names, label_all)
            yield data_batch

    @classmethod
    def _get_label(cls, buf):
        ret = np.zeros(4)
        for i in range(len(buf)):
            ret[i] = 1 + int(buf[i])
        if len(buf) == 3:
            ret[3] = 0
        return ret