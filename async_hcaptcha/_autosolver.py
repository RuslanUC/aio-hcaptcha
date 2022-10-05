# -*- coding: utf-8 -*-
# Time       : 2022/4/30 22:34
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from json import load as jload, dump as jdump, JSONDecodeError
from shutil import move
from time import time
from asyncio import run as arun
from os.path import join as pjoin, isfile, basename, exists, getsize
from logging import getLogger
from aiohttp import ClientSession
from os import makedirs, listdir
from typing import Optional, Dict, Any, Union, List, Callable
import warnings
import cv2
import numpy as np
from yaml import safe_load

warnings.filterwarnings("ignore", category=UserWarning)
logger = getLogger("autosolver")

class ChallengeStyle:
    WATERMARK = 100
    GENERAL = 128
    GAN = 144

class Memory:
    _fn2memory = {}

    ASSET_TOKEN = "RA_kw"

    def __init__(self, fn: str, dir_memory: str = None):
        self.fn = fn
        self._dir_memory = "model/_memory" if dir_memory is None else dir_memory

        self._build()

    def _build(self) -> Optional[Dict[str, str]]:
        if not self._fn2memory:
            makedirs(self._dir_memory, exist_ok=True)
            for memory_name in listdir(self._dir_memory):
                fn = memory_name.split(".")[0]
                fn = fn if fn.endswith(".onnx") else f"{fn}.onnx"
                node_id = memory_name.split(".")[-1]
                if node_id.startswith(self.ASSET_TOKEN):
                    self._fn2memory[fn] = node_id
        return self._fn2memory

    def get_node_id(self) -> Optional[str]:
        return self._fn2memory.get(self.fn, "")

    def dump(self, new_node_id: str):
        old_node_id = self._fn2memory.get(self.fn)
        self._fn2memory[self.fn] = new_node_id

        if not old_node_id:
            memory_name = pjoin(self._dir_memory, f"{self.fn}.{new_node_id}")
            with open(memory_name, "w", encoding="utf8") as file:
                file.write(memory_name)
        else:
            memory_src = pjoin(self._dir_memory, f"{self.fn}.{old_node_id}")
            memory_dst = pjoin(self._dir_memory, f"{self.fn}.{new_node_id}")
            move(memory_src, memory_dst)

    def is_outdated(self, remote_node_id: str) -> Optional[bool]:
        local_node_id = self.get_node_id()
        if not local_node_id or not remote_node_id or not isinstance(remote_node_id, str) or not remote_node_id.startswith(self.ASSET_TOKEN):
            return

        if local_node_id != remote_node_id:
            return True
        return False

class Assets:
    GITHUB_RELEASE_API = "https://api.github.com/repos/qin2dim/hcaptcha-challenger/releases"

    NAME_ASSETS = "assets"
    NAME_ASSET_NAME = "name"
    NAME_ASSET_SIZE = "size"
    NAME_ASSET_DOWNLOAD_URL = "browser_download_url"
    NAME_ASSET_NODE_ID = "node_id"

    _fn2assets = {}

    # Cache validity period: 2h
    CACHE_CONTROL = 7200

    def __init__(self, fn: str, dir_assets: str = None):
        self.fn = fn
        self._dir_assets = "model/_assets" if dir_assets is None else dir_assets

    def _preload(self):
        if self._fn2assets:
            return

        makedirs(self._dir_assets, exist_ok=True)
        assets = [i for i in listdir(self._dir_assets) if i.isdigit()]
        if len(assets) >= 1:
            asset_name = assets[-1]
            if int(asset_name) + self.CACHE_CONTROL > int(time()):
                recoded_name = pjoin(self._dir_assets, asset_name)
                try:
                    with open(recoded_name, "r", encoding="utf8") as file:
                        self._fn2assets = jload(file)
                except JSONDecodeError as err:
                    logger.warning(err)

    def _offload(self):
        makedirs(self._dir_assets, exist_ok=True)
        for asset_fn in listdir(self._dir_assets):
            asset_src = pjoin(self._dir_assets, asset_fn)
            asset_dst = pjoin(self._dir_assets, f"_{asset_fn}")
            move(asset_src, asset_dst)
        recoded_name = pjoin(self._dir_assets, str(int(time())))
        with open(recoded_name, "w", encoding="utf8") as file:
            jdump(self._fn2assets, file)

    async def _pull(self, skip_preload: bool = False) -> Optional[Dict[str, dict]]:
        async def request_assets():
            logger.debug(f"Pulling AssetsObject from {self.GITHUB_RELEASE_API}")

            try:
                async with ClientSession() as sess:
                    resp = await sess.get(self.GITHUB_RELEASE_API, timeout=3)
                    data = (await resp.json())[0]
            except (AttributeError, IndexError, KeyError, JSONDecodeError) as err:
                logger.error(err)
            else:
                if isinstance(data, dict):
                    assets: List[dict] = data.get(self.NAME_ASSETS, [])
                    for asset in assets:
                        self._fn2assets[asset[self.NAME_ASSET_NAME]] = asset
            finally:
                self._offload()

        if not skip_preload:
            self._preload()
        if not self._fn2assets:
            await request_assets()
        return self._fn2assets

    def _get_asset(self, key: str, oncall_default: Any):
        return self._fn2assets.get(self.fn, {}).get(key, oncall_default)

    def sync(self, force: Optional[bool] = None, **kwargs):
        raise NotImplementedError

    @property
    def dir_assets(self):
        return self._dir_assets

    def get_node_id(self) -> Optional[str]:
        return self._get_asset(self.NAME_ASSET_NODE_ID, "")

    def get_download_url(self) -> Optional[str]:
        return self._get_asset(self.NAME_ASSET_DOWNLOAD_URL, "")

    def get_size(self) -> Optional[int]:
        return self._get_asset(self.NAME_ASSET_SIZE, 0)

class PluggableObjects:
    URL_REMOTE_OBJECTS = "https://raw.githubusercontent.com/QIN2DIM/hcaptcha-challenger/main/src/objects.yaml"

    DEFAULT_FILENAME = "objects.yaml"

    def __init__(self, path_objects: str):
        self.path_objects = path_objects
        if not isfile(self.path_objects):
            self.path_objects = self.DEFAULT_FILENAME
        self.fn = basename(self.path_objects)

    async def sync(self):
        await _request_asset(self.URL_REMOTE_OBJECTS, self.path_objects, self.fn)

class ModelHub:
    _fn2net = {}

    def __init__(self, onnx_prefix: str, name: str, dir_model: str):
        self._dir_model = "model" if dir_model is None else dir_model

        self.net = None
        self.flag = name
        self.fn = f"{onnx_prefix}.onnx" if not onnx_prefix.endswith(".onnx") else onnx_prefix
        self.path_model = pjoin(dir_model, self.fn)

        self.memory = Memory(fn=self.fn, dir_memory=pjoin(dir_model, "_memory"))
        self.assets = Assets(fn=self.fn, dir_assets=pjoin(dir_model, "_assets"))

    async def pull_model(self, fn: str = None, path_model: str = None):
        await self.assets._pull()

        fn = self.fn if fn is None else fn
        path_model = self.path_model if path_model is None else path_model

        asset_node_id = self.assets.get_node_id()
        asset_download_url = self.assets.get_download_url()
        asset_size = self.assets.get_size()

        if not fn.endswith(".onnx") or not isinstance(asset_download_url, str) or not asset_download_url.startswith("https:"):
            return

        if not exists(path_model) or getsize(path_model) != asset_size or self.memory.is_outdated(remote_node_id=asset_node_id):
            await _request_asset(asset_download_url, path_model, fn)
            self.memory.dump(new_node_id=asset_node_id)

    def register_model(self) -> Optional[bool]:
        if exists(self.path_model) and not self.memory.is_outdated(self.assets.get_node_id()):
            self.net = cv2.dnn.readNetFromONNX(self.path_model)
            self._fn2net[self.fn] = self.net
            return True
        return False

    def match_net(self):
        if not self.net:
            self.pull_model()
            self.register_model()
        return self.net

    def solution(self, img_stream, **kwargs) -> bool:
        raise NotImplementedError

async def _request_asset(asset_download_url: str, asset_path: str, fn_tag: str):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.27"
    }
    logger.debug(f"Downloading {fn_tag} from {asset_download_url}")

    async with ClientSession() as sess:
        async with sess.get(asset_download_url, headers=headers) as resp:
            with open(asset_path, "wb") as file:
                async for chunk in resp.content.iter_chunked(32*1024):
                    file.write(chunk)

class ResNetFactory(ModelHub):
    def __init__(self, _onnx_prefix, _name, _dir_model: str):
        super().__init__(_onnx_prefix, _name, _dir_model)
        self.register_model()

    def classifier(self, img_stream, feature_filters: Union[Callable, List[Callable]] = None):
        img_arr = np.frombuffer(img_stream, np.uint8)
        img = cv2.imdecode(img_arr, flags=1)

        if img.shape[0] == ChallengeStyle.WATERMARK:
            img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

        if feature_filters is not None:
            if not isinstance(feature_filters, list):
                feature_filters = [feature_filters]
            for tnt in feature_filters:
                if not tnt(img):
                    return False

        img = cv2.resize(img, (64, 64))
        blob = cv2.dnn.blobFromImage(img, 1 / 255.0, (64, 64), (0, 0, 0), swapRB=True, crop=False)

        net = self.match_net()
        if net is None:
            raise ResourceWarning(f"""
                The remote network does not exist or the local cache has expired.
                1. Check objects.yaml for typos | model={self.fn};
                2. Restart the program after deleting the local cache | dir={self.assets.dir_assets};
            """)
        net.setInput(blob)
        out = net.forward()
        if not np.argmax(out, axis=1)[0]:
            return True
        return False

    def solution(self, img_stream, **kwargs) -> bool:
        return self.classifier(img_stream, feature_filters=None)

class PluggableONNXModels:
    def __init__(self, path_objects_yaml: str, dir_model: str, lang: Optional[str] = "en"):
        self.dir_model = dir_model
        self.lang = lang
        self._fingers = []
        self._label_alias = {i: {} for i in ["zh", "en"]}
        self._register(path_objects_yaml)

    @property
    def label_alias(self) -> Dict[str, str]:
        return self._label_alias.get(self.lang)

    @property
    def fingers(self) -> List[str]:
        return self._fingers

    def _register(self, path_objects_yaml):
        if not path_objects_yaml or not exists(path_objects_yaml):
            return

        with open(path_objects_yaml, "r", encoding="utf8") as file:
            data: Dict[str, dict] = safe_load(file.read())

        label_to_i18ndict = data.get("label_alias", {})
        if not label_to_i18ndict:
            return

        for model_label, i18n_to_raw_labels in label_to_i18ndict.items():
            self._fingers.append(model_label)
            for lang, prompt_labels in i18n_to_raw_labels.items():
                for prompt_label in prompt_labels:
                    self._label_alias[lang].update({prompt_label.strip(): model_label})

    def lazy_loading(self, model_label: str) -> Optional[ModelHub]:
        return new_tarnished(onnx_prefix=model_label, dir_model=self.dir_model)

def new_tarnished(onnx_prefix: str, dir_model: str) -> ModelHub:
    return ResNetFactory(_onnx_prefix=onnx_prefix, _name=f"{onnx_prefix}(ResNet)_model", _dir_model=dir_model)

class YOLO:
    classes = [
        "person",
        "bicycle",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
        "bird",
        "cat",
        "dog",
        "horse",
        "sheep",
        "cow",
        "elephant",
        "bear",
        "zebra",
        "giraffe",
        "backpack",
        "umbrella",
        "handbag",
        "tie",
        "suitcase",
        "frisbee",
        "skis",
        "snowboard",
        "sports ball",
        "kite",
        "baseball bat",
        "baseball glove",
        "skateboard",
        "surfboard",
        "tennis racket",
        "bottle",
        "wine glass",
        "cup",
        "fork",
        "knife",
        "spoon",
        "bowl",
        "banana",
        "apple",
        "sandwich",
        "orange",
        "broccoli",
        "carrot",
        "hot dog",
        "pizza",
        "donut",
        "cake",
        "chair",
        "couch",
        "potted plant",
        "bed",
        "dining table",
        "toilet",
        "tv",
        "laptop",
        "mouse",
        "remote",
        "keyboard",
        "cell phone",
        "microwave",
        "oven",
        "toaster",
        "sink",
        "refrigerator",
        "book",
        "clock",
        "vase",
        "scissors",
        "teddy bear",
        "hair drier",
        "toothbrush",
    ]

    def __init__(self, dir_model: str, onnx_prefix: str = None):
        onnx_prefix = (
            "yolov5s6"
            if onnx_prefix not in ["yolov5m6", "yolov5s6", "yolov5n6", "yolov6n", "yolov6s", "yolov6t"]
            else onnx_prefix
        )

        name = f"YOLOv5{onnx_prefix[-2:]}"
        if onnx_prefix.startswith("yolov6"):
            name = f"MT-YOLOv6{onnx_prefix[-1]}"

        self.modelhub = ModelHub(onnx_prefix, f"{name}(ONNX)_model", dir_model)
        self.modelhub.register_model()
        self.flag = self.modelhub.flag

    async def pull_model(self):
        await self.modelhub.pull_model()

    def detect_common_objects(self, img: np.ndarray, confidence=0.4, nms_thresh=0.4):
        height, width = img.shape[:2]

        class_ids = []
        confidences = []
        boxes = []

        blob = cv2.dnn.blobFromImage(img, 1 / 255.0, (128, 128), (0, 0, 0), swapRB=True, crop=False)

        net = self.modelhub.match_net()
        net.setInput(blob)
        outs = net.forward()

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                max_conf = scores[class_id]
                if max_conf > confidence:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = center_x - (w / 2)
                    y = center_y - (h / 2)
                    class_ids.append(class_id)
                    confidences.append(float(max_conf))
                    boxes.append([x, y, w, h])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, confidence, nms_thresh)

        return [str(self.classes[class_ids[i]]) for i in indices]

    def solution(self, img_stream: bytes, label: str, **kwargs) -> bool:
        confidence = kwargs.get("confidence", 0.4)
        nms_thresh = kwargs.get("nms_thresh", 0.4)

        np_array = np.frombuffer(img_stream, np.uint8)
        img = cv2.imdecode(np_array, flags=1)
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21) if img.shape[0] == ChallengeStyle.WATERMARK else img
        try:
            labels = self.detect_common_objects(img, confidence, nms_thresh)
            return bool(label in labels)
        except ValueError:
            return False