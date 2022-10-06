import re
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from hashlib import sha1
from json import dumps as jdumps
from json import loads as jloads
from math import ceil, floor
from random import randint
from time import time
from typing import List, Tuple
from urllib.parse import urlparse
from aiohttp import ClientSession
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from asyncio import get_event_loop, sleep as asleep
from .utils import mouse_curve, getUrl
from .autosolver import AutoSolver

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
    def __init__(self, sitekey, url, chromedriver_args, captcha_callback=None, autosolve=False):
        self.sitekey = sitekey
        self.url = url
        self.domain = urlparse(url).netloc
        self.chromedriver_args = chromedriver_args

        autosolve = autosolve or not captcha_callback

        self._c = None
        self._start = None
        self._script = {}
        self._version = "21130e0"
        self._question_callback = captcha_callback if not autosolve else self.autosolve

    async def _getN(self) -> str:
        if self._c["type"] == "hsw":
            token = self._c["req"].split(".")[1].encode("utf8")
            token += b'=' * (-len(token) % 4)
            d = jloads(b64decode(token).decode("utf8"))
            if f"hsw_{d['l']}" not in self._script:
                self._script[f"hsw_{d['l']}"] = await getUrl(f"{d['l']}/hsw.js")
            return await self._solve_hsw(d['l'])
        elif self._c["type"] == "hsl":
            await self._solve_hsl()

    async def _solve_hsw(self, sc) -> str:
        token = self._c["req"]
        script = self._script[f"hsw_{sc}"]

        def _hsw():
            options = ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver = Chrome(service=Service(**self.chromedriver_args), options=options)
            return driver.execute_script(f"{script}\n\nreturn await hsw(\"{token}\");")

        return await get_event_loop().run_in_executor(ThreadPoolExecutor(4), _hsw)

    async def _solve_hsl(self): # From https://github.com/AcierP/py-hcaptcha/blob/main/hcaptcha/proofs/hsl.py
        x  = "0123456789/:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        token = self._c["req"].split(".")[1].encode("utf8")
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
            n = e
            hashed = sha1(e.encode())
            o = hashed.hexdigest()
            t = hashed.digest()
            e = None
            n = -1
            o = []
            for n in range(n + 1, 8 * len(t)):
                e = t[floor(n / 8)] >> n % 8 & 1
                o.append(e)
            a = o[:r]
            def index2(x,y):
                if y in x:
                    return x.index(y)
                return -1
            return 0 == a[0] and index2(a, 1) >= r - 1 or -1 == index2(a, 1)

        def get():
            for e in range(25):
                n = [0 for i in range(e)]
                while a(n):
                    u = req["d"] + "::" + i(n)
                    if o(req["s"], u):
                        return i(n)

        result = get()
        hsl = ":".join([
            "1",
            str(req["s"]),
            datetime.now().isoformat()[:19] \
                .replace("T", "") \
                .replace("-", "") \
                .replace(":", ""),
            req["d"],
            "",
            result
        ])
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
                    "availWidth": 1920,
                    "availHeight": 1022,
                    "width": 1920,
                    "height": 1080,
                    "colorDepth": 24,
                    "pixelDepth": 24,
                    "availLeft": 0,
                    "availTop": 18,
                    "onchange": None,
                    "isExtended": True
                },
                "nv": {
                    "vendorSub": "",
                    "productSub": "20030107",
                    "vendor": "Google Inc.",
                    "maxTouchPoints": 0,
                    "scheduling": {},
                    "userActivation": {},
                    "doNotTrack": "1",
                    "geolocation": {},
                    "connection": {},
                    "pdfViewerEnabled": True,
                    "webkitTemporaryStorage": {},
                    "webkitPersistentStorage": {},
                    "hardwareConcurrency": 8,
                    "cookieEnabled": True,
                    "appCodeName": "Mozilla",
                    "appName": "Netscape",
                    "appVersion": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
                    "platform": "Win32",
                    "product": "Gecko",
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
                    "language": "en-US",
                    "languages": ["en-US", "en"],
                    "onLine": True,
                    "webdriver": False,
                    "bluetooth": {},
                    "clipboard": {},
                    "credentials": {},
                    "keyboard": {},
                    "managed": {},
                    "mediaDevices": {},
                    "storage": {},
                    "serviceWorker": {},
                    "virtualKeyboard": {},
                    "wakeLock": {},
                    "deviceMemory": 8,
                    "ink": {},
                    "hid": {},
                    "locks": {},
                    "mediaCapabilities": {},
                    "mediaSession": {},
                    "permissions": {},
                    "presentation": {},
                    "serial": {},
                    "usb": {},
                    "windowControlsOverlay": {},
                    "xr": {},
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
                "dr": "",
                "exec": False,
                "wn": [],
                "wn-mp": 0,
                "xy": [],
                "xy-mp": 0,
            },
            "session": [],
            "widgetList": ["099kzxm1krnm"],
            "widgetId": "099kzxm1krnm",
            "href": self.url,
            "prev": {
                "escaped": False,
                "passed": False,
                "expiredChallenge": False,
                "expiredResponse": False
            }
        }

    async def _getMotionData(self):
        j = self._motionData

        mc = MotionController(j["st"], (randint(0, 480), randint(0, 270)))
        mc.move(randint(1440, 1920), randint(810, 1022), 35)
        mc.click()
        j.update(**mc.get())

        tmm = MotionController(self._start + 1000 + randint(100, 150), (randint(0, 480), randint(0, 270)))
        tmm.move(randint(1440, 1920), randint(810, 1022), 70)

        j["topLevel"].update(tmm.get(md=False, mu=False))
        return j

    async def _getMotionDataForSolved(self, answers):
        j = self._motionData
        j["dct"] = j["st"]
        ans = list(answers.values())
        sx = randint(300, 500)
        sy = randint(150, 300)

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
        return j

    async def autosolve(self, question, tasklist):
        answers = {}
        solver = await AutoSolver().init()
            
        for uuid, url in tasklist.items():
            data = await getUrl(url, False)
            result = await solver.solve(data, question)
            answers[uuid] = "true" if result else "false"

        return answers

    async def solve(self, *, custom_params=None):
        if not custom_params:
            custom_params = {}

        self._start = int(time() * 1000 - 2000)
        sess = ClientSession(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
            "Origin": "https://newassets.hcaptcha.com",
            "Referer": "https://newassets.hcaptcha.com/",
            "dnt": "1",
        })

        api_js = await sess.get("https://js.hcaptcha.com/1/api.js")
        api_js = await api_js.text()
        versions = re.findall('captcha\\/v1\\/([a-z0-9]{4,8})\\/static', api_js)
        if versions:
            self._version = versions[0]

        siteconfig = await sess.post("https://hcaptcha.com/checksiteconfig", params={
            "v": self._version,
            "host": self.domain,
            "sitekey": self.sitekey,
            "sc": 1,
            "swa": 1
        })
        self._c = (await siteconfig.json())["c"]
        captcha = await sess.post(f"https://hcaptcha.com/getcaptcha/{self.sitekey}", data={
            "v": self._version,
            "host": self.domain,
            "sitekey": self.sitekey,
            "hl": "en-US",
            "n": await self._getN(),
            "c": jdumps(self._c),
            "motionData": await self._getMotionData(),
            **custom_params
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        captcha = await captcha.json()
        if captcha.get("pass"):
            return captcha["generated_pass_UUID"]

        key = captcha["key"]
        tasklist = {task["task_key"]: task["datapoint_uri"] for task in captcha["tasklist"]}

        self._start = int(time() * 1000 - 2000)
        answers = await self._question_callback(captcha["requester_question"]["en"], tasklist)

        res = await sess.post(f"https://hcaptcha.com/checkcaptcha/{self.sitekey}/{key}", json={
            "answers": answers,
            "v": self._version,
            "serverdomain": self.domain,
            "job_mode": "image_label_binary",
            "c": jdumps(self._c),
            "n": await self._getN(),
            "sitekey": self.sitekey,
            "motionData": jdumps(await self._getMotionDataForSolved(answers))
        })
        r = await res.json()
        await sess.close()

        if r.get("pass"):
            return r["generated_pass_UUID"]
