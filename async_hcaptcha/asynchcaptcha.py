import re
from asyncio import get_event_loop, sleep as asleep, create_subprocess_shell, subprocess
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from hashlib import sha1
from json import dumps as jdumps, loads as jloads
from logging import getLogger
from math import ceil, floor
from random import randint, choice
from time import time
from typing import Tuple
from urllib.parse import urlparse
from os.path import join as pjoin, dirname, realpath
from aiohttp import ClientSession
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service

from .utils import mouse_curve, getUrl

import hcaptcha_challenger
hcaptcha_challenger.logger.remove() # TODO: Redirect logs from loguru to logging or use loguru instead of logging

log = getLogger("AsyncHcaptcha")

with open(pjoin(dirname(realpath(__file__)), "window.js")) as f:
    w = f.read()
    w = w.replace("  ", "")
    w = w.replace("\n", "")
    w += ";const window = new Window();"
_WINDOW = w

class MotionData:
    def __init__(self, x=0, y=0, controller=None):
        self._point = (x, y)
        self._meanPeriod = 0
        self._meanCounter = 0
        self._data = []
        self._controller = controller

    @property
    def timestamp(self):
        return self._controller.timestamp

    @timestamp.setter
    def timestamp(self, val):
        self._controller.timestamp = val

    def moveTo(self, x, y, s):
        curve = mouse_curve(self._point, (x, y), s)
        for pt in curve:
            self.addPoint(*pt)
        self._point = self._data[-1][:2]

    def addPoint(self, x, y):
        self.timestamp += randint(20, 40)
        self._data.append([x, y, self.timestamp])
        if self._meanCounter != 0:
            delta = self._data[-1][2] - self._data[-2][2]
            self._meanPeriod = (self._meanPeriod * self._meanCounter + delta) / (self._meanCounter + 1)
        self._meanPeriod += 1

    @property
    def data(self):
        return self._data

    @property
    def mp(self):
        return self._meanPeriod

    @property
    def point(self):
        return self._point

class MotionController:
    def __init__(self, timestamp: int, start_point: Tuple[int, int]):
        self.timestamp = timestamp or time()
        self._mm = MotionData(*start_point, controller=self)
        self._md = MotionData(controller=self)
        self._mu = MotionData(controller=self)

        self._lastPoint = start_point

    def move(self, x, y, s):
        self._mm.moveTo(x, y, s)
        self._lastPoint = self._mm.point

    def click(self, x=0, y=0):
        if not x and not y:
            x, y = self._lastPoint
        self._md.addPoint(x, y)
        self._mu.addPoint(x, y)
        self._lastPoint = (x, y)

    def get(self, mm=True, md=True, mu=True):
        r = {}
        if mm:
            r["mm"] = self._mm.data
            r["mm-mp"] = self._mm.mp
        if md:
            r["md"] = self._md.data
            r["md-mp"] = self._md.mp
        if mu:
            r["mu"] = self._mu.data
            r["mu-mp"] = self._mu.mp
        return r

class AioHcaptcha:
    def __init__(self, sitekey, url, args, captcha_callback=None, autosolve=False, headers=None):
        self.sitekey = sitekey
        self.url = url
        self.domain = urlparse(url).netloc
        if "executable_path" in args:
            args["chromedriver"] = args["executable_path"]
            del args["executable_path"]
        if "node" not in args and "chromedriver" not in args:
            raise AttributeError("")
        self.args = args
        self.headers = headers

        autosolve = autosolve or not captcha_callback

        self._req = None
        self._start = None
        self._script = {}
        self._version = "21130e0"
        self._widgetId = ""
        self._question_callback = captcha_callback if not autosolve else self.autosolve
        self._retries = 0

        log.debug(f"Initialized {self.__class__.__name__} with "
                  f"sitekey={self.sitekey}, url={self.url}, domain={self.domain}, args={self.args}, "
                  f"autosolve={autosolve}, _question_callback={self._question_callback}.")

    async def _getN(self) -> str:
        if self._req["type"] == "hsw":
            log.debug("Generating proof with type = hsw.")
            token = self._req["req"].split(".")[1].encode("utf8")
            token += b'=' * (-len(token) % 4)
            d = jloads(b64decode(token).decode("utf8"))
            log.debug(f"Hsw url: {d['l']}/hsw.js")
            if f"hsw_{d['l']}" not in self._script:
                self._script[f"hsw_{d['l']}"] = await getUrl(f"{d['l']}/hsw.js")
            return await self._solve_hsw(d['l'])
        elif self._req["type"] == "hsl":
            log.debug("Generating proof with type = hsl.")
            await self._solve_hsl()

    async def _solve_hsw(self, sc: str) -> str:
        token = self._req["req"]
        script = self._script[f"hsw_{sc}"]

        async def _hsw_node():
            proc = await create_subprocess_shell(self.args["node"]+" -", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            stdout, _ = await proc.communicate((_WINDOW + "\n\n" + script + "\n\nasync function idk(){" + f"console.log(await hsw(\"{token}\"));" + "}\nidk();").encode("utf8"))
            data = stdout.decode("utf8").strip()
            return data

        async def _hsw_chromedriver():
            def _hsw():
                log.debug("Running chromedriver.")
                options = ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                driver = Chrome(service=Service(executable_path=self.args["chromedriver"]), options=options)
                res = driver.execute_script(f"{script}\n\nreturn await hsw(\"{token}\");")
                log.debug(f"Got proof result: {res}. Closing chromedriver...")
                driver.close()
                return res
            return await get_event_loop().run_in_executor(ThreadPoolExecutor(4), _hsw)

        if "node" in self.args:
            res = await _hsw_node()
            if not res:
                if "chromedriver" in self.args:
                    return await _hsw_chromedriver()
            return res
        elif "chromedriver" in self.args:
            return await _hsw_chromedriver()

    async def _solve_hsl(self) -> str: # From https://github.com/AcierP/py-hcaptcha/blob/main/hcaptcha/proofs/hsl.py
        x  = "0123456789/:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        token = self._req["req"].split(".")[1].encode("utf8")
        token += b'=' * (-len(token) % 4)
        req = jloads(b64decode(token).decode("utf8"))

        def a(r):
            for t in range(len(r) - 1, -1, -1):
                if r[t] < len(x) - 1:
                    r[t] += 1
                    return True
                r[t] = 0
            return False

        def i(r):
            t = ""
            for n in range(len(r)):
                t += x[r[n]]
            return t

        def o(r, e):
            hashed = sha1(e.encode())
            t = hashed.digest()
            n = -1
            p = []
            for n in range(n + 1, 8 * len(t)):
                e = t[floor(n / 8)] >> n % 8 & 1
                p.append(e)
            l = p[:r]
            def index2(b,y):
                if y in b:
                    return b.index(y)
                return -1
            return 0 == l[0] and index2(l, 1) >= r - 1 or -1 == index2(l, 1)

        def get():
            for e in range(25):
                n = [0 for _ in range(e)]
                while a(n):
                    u = req["d"] + "::" + i(n)
                    if o(req["s"], u):
                        return i(n)

        result = get()
        hsl = ":".join([
            "1",
            str(req["s"]),
            datetime.now().isoformat()[:19].replace("T", "").replace("-", "").replace(":", ""),
            req["d"],
            "",
            result
        ])
        log.debug(f"Got proof result: {hsl}.")
        return hsl

    @property
    def _motionData(self) -> dict:
        return {
            "st": self._start + 1000 + randint(10, 100),
            "v": 1,
            "topLevel": {
                "inv": False,
                "st": self._start,
                "sc": {
                    "availWidth": 1920, "availHeight": 1022, "width": 1920, "height": 1080, "colorDepth": 24,
                    "pixelDepth": 24, "availLeft": 0, "availTop": 18, "onchange": None, "isExtended": True
                },
                "nv": {
                    "vendorSub": "", "productSub": "20030107", "vendor": "Google Inc.", "maxTouchPoints": 0,
                    "scheduling": {}, "userActivation": {}, "doNotTrack": "1", "geolocation": {}, "connection": {},
                    "pdfViewerEnabled": True, "webkitTemporaryStorage": {}, "webkitPersistentStorage": {},
                    "hardwareConcurrency": 8, "cookieEnabled": True, "appCodeName": "Mozilla", "appName": "Netscape",
                    "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
                    "platform": "Win32", "product": "Gecko", "language": "en-US", "languages": ["en-US", "en"],
                    "onLine": True, "webdriver": False, "bluetooth": {}, "clipboard": {}, "credentials": {},
                    "keyboard": {}, "managed": {}, "mediaDevices": {}, "storage": {}, "serviceWorker": {},
                    "virtualKeyboard": {}, "wakeLock": {}, "deviceMemory": 8, "ink": {}, "hid": {}, "locks": {},
                    "mediaCapabilities": {}, "mediaSession": {}, "permissions": {}, "presentation": {}, "serial": {},
                    "usb": {}, "windowControlsOverlay": {}, "xr": {},
                    "userAgentData": {
                        "brands": [
                            {"brand": "Chromium", "version": "106"},
                            {"brand": "Google Chrome", "version": "106"},
                            {"brand": "Not;A=Brand", "version": "99"}
                        ],
                        "mobile": False,
                        "platform": "Windows"
                    },
                    "plugins": [
                        "internal-pdf-viewer",
                        "internal-pdf-viewer",
                        "internal-pdf-viewer",
                        "internal-pdf-viewer",
                        "internal-pdf-viewer"
                    ]
                },
                "dr": "", "exec": False, "wn": [], "wn-mp": 0, "xy": [], "xy-mp": 0,
            },
            "session": [],
            "widgetList": [self._widgetId],
            "widgetId": self._widgetId,
            "href": self.url,
            "prev": {"escaped": False, "passed": False, "expiredChallenge": False, "expiredResponse": False}
        }

    async def _getMotionData(self) -> dict:
        j = self._motionData

        log.debug("Generating motionData...")
        mc = MotionController(j["st"], (randint(0, 480), randint(0, 270)))
        mc.move(randint(1440, 1920), randint(810, 1022), 35)
        mc.click()
        j.update(**mc.get())

        tmm = MotionController(self._start + 1000 + randint(100, 150), (randint(0, 480), randint(0, 270)))
        tmm.move(randint(1440, 1920), randint(810, 1022), 70)

        j["topLevel"].update(tmm.get(md=False, mu=False))

        log.debug(f"motionData={j}")
        return j

    async def _getMotionDataForSolved(self, answers: dict) -> dict:
        j = self._motionData
        j["dct"] = j["st"]
        ans = list(answers.values())
        sx = randint(300, 500)
        sy = randint(150, 300)

        log.debug("Generating motionData for solved captcha...")
        mc = MotionController(self._start, (randint(1440, 1920), randint(810, 1022)))
        mc.move(randint(0, 480), randint(0, 270), 40)
        mc.click()
        j["topLevel"].update(**mc.get())

        mc = MotionController(j["st"] + randint(50, 150), (sx, sy))
        for idx, ans in enumerate(ans):
            if idx == 9:
                mc.move(randint(330, 370), randint(420, 460), randint(10, 15))
                mc.click()
            if ans == "true":
                row = ceil(round((idx + 1) / 3))
                col = (idx + 1) % 3
                if col == 0:
                    col = 3
                x = sx + 80 * row + randint(80, 160)
                y = sy + 80 * col + randint(80, 160)
                mc.move(x, y, randint(10, 15))
                mc.click()
        j.update(**mc.get())
        t = j["mm"][-1][2]
        if t / 1000 > time():
            s = (t - time() * 1000) / 1000
            await asleep(s)
        log.debug(f"motionData={j}")
        return j

    async def autosolve(self, question: str, tasklist: dict) -> dict:
        log.debug("Solving captcha with AutoSolver.")
        answers = {}

        imgs = []
        for uuid, url in tasklist.items():
            imgs.append(await getUrl(url, False))

        def _autosolve():
            hcaptcha_challenger.install()
            challenger = hcaptcha_challenger.new_challenger()
            if res := challenger.classify(question, imgs):
                return res

        res = await get_event_loop().run_in_executor(ThreadPoolExecutor(4), _autosolve)
        log.debug(f"AutoSolver result: {res}")
        if res:
            for idx, uuid in enumerate(tasklist.keys()):
                answers[uuid] = "true" if res[idx] else "false"

            log.debug(f"Answers: {answers}")
            return answers

    async def solve(self, retry_count=1, custom_params=None):
        if not custom_params:
            custom_params = {}
        log.debug(f"Solving with retry_count={retry_count}, custom_params={custom_params}")

        self._widgetId = "".join([choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(12)])

        # Initialize session with headers
        self._start = int(time() * 1000 - 2000)
        sess = ClientSession(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
            "Origin": "https://newassets.hcaptcha.com",
            "Referer": "https://newassets.hcaptcha.com/",
            "dnt": "1",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Language": "en-US,en;q=0.9",
            **(self.headers if isinstance(self.headers, dict) else {})
        })

        # Get latest hcaptcha version code
        api_js = await sess.get("https://js.hcaptcha.com/1/api.js")
        api_js = await api_js.text()
        versions = re.findall(r'captcha\\/v1\\/([a-z0-9]{4,8})\\/static', api_js)
        if versions:
            self._version = versions[0]

        log.debug(f"HCaptcha version: {self._version}")

        # Get site config
        siteconfig = await sess.post("https://hcaptcha.com/checksiteconfig", params={
            "v": self._version,
            "host": self.domain,
            "sitekey": self.sitekey,
            "sc": 1,
            "swa": 1
        })

        siteconfig_j = await siteconfig.json()
        log.debug(f"checksiteconfig response code: {siteconfig.status}")
        log.debug(f"SiteConfig: {siteconfig_j}")
        self._req = siteconfig_j["c"]

        # Get captcha
        captcha = await sess.post(f"https://hcaptcha.com/getcaptcha/{self.sitekey}", data={
            "v": self._version,
            "host": self.domain,
            "sitekey": self.sitekey,
            "hl": "en-US",
            "n": await self._getN(),
            "c": jdumps(self._req),
            "motionData": await self._getMotionData(),
            **custom_params
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        log.debug(f"getcaptcha/{self.sitekey} response code: {siteconfig.status}")

        # Return captcha key if it in response
        captcha = await captcha.json()
        log.debug(f"GetCaptcha: {captcha}")
        if captcha.get("pass"):
            log.debug(f"Captcha solved!")
            return captcha["generated_pass_UUID"]

        key = captcha["key"]
        tasklist = {task["task_key"]: task["datapoint_uri"] for task in captcha["tasklist"]} # Format tasks to `uuid: url` format

        log.debug(f"Question: {captcha['requester_question']['en']}")
        self._start = int(time() * 1000 - 2000)
        if (answers := await self._question_callback(captcha["requester_question"]["en"], tasklist)) is None: # Get answers
            log.debug(f"Can't solve this captcha. Retrying...")
            self._retries += 1
            return await self.solve(retry_count, custom_params)
        log.debug(f"Got answers: {answers}, sending to /checkcaptcha/{self.sitekey}/{key}")

        # Send answers
        res = await sess.post(f"https://hcaptcha.com/checkcaptcha/{self.sitekey}/{key}", json={
            "answers": answers,
            "v": self._version,
            "serverdomain": self.domain,
            "job_mode": "image_label_binary",
            "c": jdumps(self._req),
            "n": await self._getN(),
            "sitekey": self.sitekey,
            "motionData": jdumps(await self._getMotionDataForSolved(answers))
        })
        log.debug(f"checkcaptcha/{self.sitekey}/{key} response code: {res.status}")

        r = await res.json()
        await sess.close()

        log.debug(f"CheckCaptcha response: {r}")

        # Return captcha key if it in response
        if r.get("pass"):
            log.debug(f"Captcha solved!")
            return r["generated_pass_UUID"]

        # Retry if failed to solve captcha
        if retry_count > 0 and self._retries < retry_count:
            log.debug(f"Retrying...")
            self._retries += 1
            return await self.solve(retry_count, custom_params)