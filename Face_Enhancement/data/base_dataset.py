# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import torch.utils.data as data
from PIL import Image
import torchvision.transforms as transforms
import numpy as np
import random


class BaseDataset(data.Dataset):
    def __init__(self):
        super(BaseDataset, self).__init__()

    @staticmethod
    def modify_commandline_options(parser, is_train):
        return parser

    def initialize(self, opt):
        pass


def get_crop_pos(image_size, preprocess_mode: str, load_size: int, crop_size: int):
    w, h = image_size
    new_h = h
    new_w = w
    if preprocess_mode == "resize_and_crop":
        new_h = new_w = load_size
    elif preprocess_mode == "scale_width_and_crop":
        new_w = load_size
        new_h = load_size * h // w
    elif preprocess_mode == "scale_shortside_and_crop":
        ss, ls = min(w, h), max(w, h)  # shortside and longside
        width_is_shorter = w == ss
        ls = int(load_size * ls / ss)
        new_w, new_h = (ss, ls) if width_is_shorter else (ls, ss)
    else:
        raise NotImplementedError("Unknown type of 'preprocess_mode'!")

    x = random.randint(0, np.maximum(0, new_w - crop_size))
    y = random.randint(0, np.maximum(0, new_h - crop_size))
    return (x, y)


def get_random_flip() -> bool:
    return random.random() > 0.5


def get_transform(
    preprocess_mode: str, 

    image_size, 
    load_size: int, 
    crop_size: int, 
    aspect_ratio: float, 

    is_train: bool, 
    no_flip: bool, 
    flip: bool, 

    method=Image.BICUBIC, 
    normalize=True, 
    toTensor=True
):
    transform_list = []
    if "resize" in preprocess_mode:
        osize = [load_size, load_size]
        transform_list.append(transforms.Resize(osize, interpolation=method))
    elif "scale_width" in preprocess_mode:
        transform_list.append(transforms.Lambda(lambda img: __scale_width(img, load_size, method)))
    elif "scale_shortside" in preprocess_mode:
        transform_list.append(transforms.Lambda(lambda img: __scale_shortside(img, load_size, method)))

    if "crop" in preprocess_mode:
        crop_pos = get_crop_pos(image_size, preprocess_mode, load_size, crop_size)
        transform_list.append(transforms.Lambda(lambda img: __crop(img, crop_pos, crop_size)))

    if preprocess_mode == "none":
        base = 32
        transform_list.append(transforms.Lambda(lambda img: __make_power_2(img, base, method)))

    if preprocess_mode == "fixed":
        w = crop_size
        h = round(crop_size / aspect_ratio)
        transform_list.append(transforms.Lambda(lambda img: __resize(img, w, h, method)))

    if is_train and not no_flip:
        transform_list.append(transforms.Lambda(lambda img: __flip(img, flip)))

    if toTensor:
        transform_list += [transforms.ToTensor()]

    if normalize:
        transform_list += [transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
    return transforms.Compose(transform_list)


def normalize():
    return transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))


def __resize(img, w, h, method=Image.BICUBIC):
    return img.resize((w, h), method)


def __make_power_2(img, base, method=Image.BICUBIC):
    ow, oh = img.size
    h = int(round(oh / base) * base)
    w = int(round(ow / base) * base)
    if (h == oh) and (w == ow):
        return img
    return img.resize((w, h), method)


def __scale_width(img, target_width, method=Image.BICUBIC):
    ow, oh = img.size
    if ow == target_width:
        return img
    w = target_width
    h = int(target_width * oh / ow)
    return img.resize((w, h), method)


def __scale_shortside(img, target_width, method=Image.BICUBIC):
    ow, oh = img.size
    ss, ls = min(ow, oh), max(ow, oh)  # shortside and longside
    width_is_shorter = ow == ss
    if ss == target_width:
        return img
    ls = int(target_width * ls / ss)
    nw, nh = (ss, ls) if width_is_shorter else (ls, ss)
    return img.resize((nw, nh), method)


def __crop(img, pos, size):
    ow, oh = img.size
    x1, y1 = pos
    tw = th = size
    return img.crop((x1, y1, x1 + tw, y1 + th))


def __flip(img, flip):
    if flip:
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    return img
