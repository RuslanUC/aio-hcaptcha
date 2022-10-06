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
from typing import List
from urllib.parse import urlparse
from aiohttp import ClientSession
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from asyncio import get_event_loop, sleep as asleep
from .utils import mouse_curve, getUrl
from .autosolver import AutoSolver

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
                "exec": False
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

    def _getMp(self, arr: List[List[int]]) -> float:
        mp = 0
        count = 0
        for idx, item in enumerate(arr):
            if idx == 0:
                continue
            delta = item[2] - arr[idx - 1][2]
            mp = (mp * count + delta) / (count + 1)
            count += 1
        return mp

    async def _getMotionData(self):
        j = self._motionData

        curve = mouse_curve(
            (randint(0, 480), randint(0, 270)),
            (randint(1440, 1920), randint(810, 1022)),
            35
        )
        idx = randint(23, 30)
        mm = deepcopy(curve[:idx])
        md = curve[idx].copy()
        mu = curve[idx].copy()
        ctime = j["st"]
        for m in mm:
            ctime += randint(20, 40)
            m.append(ctime)
        ctime += randint(30, 50)
        md.append(ctime)
        ctime += randint(30, 50)
        mu.append(ctime)
        md = [md]
        mu = [mu]
        j["mm"] = mm
        j["mm-mp"] = self._getMp(mm)
        j["md"] = md
        j["md-mp"] = self._getMp(md)
        j["mu"] = mu
        j["mu-mp"] = self._getMp(mu)

        curve = mouse_curve(
            (randint(0, 480), randint(0, 270)),
            (randint(1440, 1920), randint(810, 1022)),
            70
        )
        idx = randint(60, 70)
        mm = curve[:idx]
        ctime = self._start + 1000 + randint(100, 150)
        for m in mm:
            ctime += randint(20, 40)
            m.append(ctime)
        j["topLevel"]["mm"] = mm
        j["topLevel"]["mm-mp"] = self._getMp(mm)

        j["topLevel"]["wn"] = []
        j["topLevel"]["wn-mp"] = 0
        j["topLevel"]["xy"] = []
        j["topLevel"]["xy-mp"] = 0
        return j

    async def _getMotionDataForSolved(self, answers):
        j = self._motionData
        j["dct"] = j["st"]
        mm = []
        md = []
        mu = []
        ans = list(answers.values())
        sx = randint(300, 500)
        sy = randint(150, 300)
        lastp = sx, sy
        st = j["st"] + randint(50, 150)

        tc = mouse_curve(
            (randint(1440, 1920), randint(810, 1022)),
            (randint(0, 480), randint(0, 270)),
            40
        )
        idx = randint(30, 38)
        tmm = deepcopy(tc[:idx])
        tmd = tc[idx].copy()
        tmu = tc[idx].copy()
        ctime = self._start
        for m in tmm:
            ctime += randint(20, 40)
            m.append(ctime)
        ctime += randint(30, 50)
        tmd.append(ctime)
        ctime += randint(30, 50)
        tmu.append(ctime)
        tmd = [tmd]
        tmu = [tmu]
        j["topLevel"]["mm"] = tmm
        j["topLevel"]["mm-mp"] = self._getMp(tmm)
        j["topLevel"]["md"] = tmd
        j["topLevel"]["md-mp"] = self._getMp(tmd)
        j["topLevel"]["mu"] = tmu
        j["topLevel"]["mu-mp"] = self._getMp(tmu)
        j["topLevel"]["wn"] = []
        j["topLevel"]["wn-mp"] = 0
        j["topLevel"]["xy"] = []
        j["topLevel"]["xy-mp"] = 0

        for idx, ans in enumerate(ans):
            if idx == 9:
                pn = randint(330, 370), randint(420, 460)
                curve = mouse_curve(lastp, pn, randint(10, 15))
                for c in curve:
                    c.append(st)
                    st += randint(10, 20)
                mm += curve
                md.append([pn[0], pn[1], st])
                st += randint(20, 30)
                mu.append([pn[0], pn[1], st])
                st += randint(10, 20)
                lastp = pn
            if ans == "true":
                row = ceil(round((idx + 1) / 3))
                col = (idx + 1) % 3
                if col == 0:
                    col = 3
                x = sx + 80 * row + randint(80, 160)
                y = sy + 80 * col + randint(80, 160)
                curve = mouse_curve(lastp, (x, y), randint(10, 15))
                for c in curve:
                    c.append(st)
                    st += randint(10, 20)
                mm += curve
                md.append([x, y, st])
                st += randint(20, 30)
                mu.append([x, y, st])
                st += randint(10, 20)
                lastp = x, y
        j["mm"] = mm
        j["md"] = md
        j["mu"] = mu
        j["mm-mp"] = self._getMp(mm)
        j["md-mp"] = self._getMp(md)
        j["mu-mp"] = self._getMp(mu)
        t = mm[-1][2]
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
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
