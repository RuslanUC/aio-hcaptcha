from ._autosolver import PluggableObjects, YOLO, PluggableONNXModels
import re

class AutoSolverException(Exception):
    pass

class AutoSolver:
    BAD_CODE = {
        "а": "a",
        "е": "e",
        "e": "e",
        "i": "i",
        "і": "i",
        "ο": "o",
        "с": "c",
        "ԁ": "d",
        "ѕ": "s",
        "һ": "h",
        "у": "y",
        "р": "p",
        "ー": "一",
        "土": "士",
    }

    def __init__(self):
        self.label_alias = {
            "airplane": "airplane",
            "motorbus": "bus",
            "bus": "bus",
            "truck": "truck",
            "motorcycle": "motorcycle",
            "boat": "boat",
            "bicycle": "bicycle",
            "train": "train",
            "vertical river": "vertical river",
            "airplane in the sky flying left": "airplane in the sky flying left",
            "Please select all airplanes in the sky that are flying to the right": "airplanes in the sky that are flying to the right",
            "car": "car",
            "elephant": "elephant",
            "bird": "bird",
            "dog": "dog",
            "canine": "dog",
            "horse": "horse",
            "giraffe": "giraffe",
        }
        self.pom_handler = PluggableONNXModels(path_objects_yaml="./objects.yaml", dir_model="./models/", lang="en")
        self.label_alias.update(self.pom_handler.label_alias)

        self._init = False

    async def init(self):
        await PluggableObjects("./models/").sync()
        await YOLO("./models/", None).pull_model()
        self._init = True
        return self

    def _get_label(self, label: str):
        def split_prompt_message(prompt_message: str) -> str:
            prompt_message = prompt_message.replace(".", "").lower()
            if "containing" in prompt_message:
                return re.split(r"containing a", prompt_message)[-1][1:].strip()
            if "select all" in prompt_message:
                return re.split(r"all (.*) images", prompt_message)[1].strip()
            return prompt_message

        def label_cleaning(raw_label: str) -> str:
            clean_label = raw_label
            for c in self.BAD_CODE:
                clean_label = clean_label.replace(c, self.BAD_CODE[c])
            return clean_label

        try:
            _label = split_prompt_message(prompt_message=label)
        except (AttributeError, IndexError):
            raise Exception("Get the exception label object")
        else:
            return label_cleaning(_label)

    async def solve(self, image: bytes, question: str) -> bool:
        label = self._get_label(question)
        label_alias = self.label_alias.get(label)
        if label_alias not in self.pom_handler.fingers:
            model = YOLO("./assets/", None)
        else:
            model = self.pom_handler.lazy_loading(label_alias)
        try:
            return await model.solution(img_stream=image, label=self.label_alias[label])
        except KeyError:
            raise AutoSolverException()