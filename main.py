from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from json import dumps as jdumps
from json import loads as jloads
from random import randint, random
from time import time
from urllib.parse import urlparse

from aiohttp import ClientSession
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service

from utils import mouse_curve, getUrl

#SITEKEY =
#URL = "accounts.hcaptcha.com"

class AioHcaptcha:
    def __init__(self, sitekey, url, captcha_callback):
        self.sitekey = sitekey
        self.url = url
        self.domain = urlparse(url).netloc

        self._s = None
        self._question_callback = captcha_callback

    async def _getN(self):
        if self._c["type"] == "hsw":
            tok = self._c["req"]
            t = tok.split(".")[1].encode("utf8")
            t += b'=' * (-len(t) % 4)
            d = jloads(b64decode(t).decode("utf8"))
            scr = await getUrl(f"{d['l']}/hsw.js")
            return await self._solve_hsw(scr, tok)
        elif self._c["type"] == "hsl":
            await self._solve_hsl(self._c["req"])

    async def _getMotionData(self, start):
        j = {
            "st": start+1000+randint(10, 100),
            "v": 1,
            "topLevel": {
                "inv": False,
                "st": start,
                "sc": {"availWidth": 1920,
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
                    "language": "ru-RU",
                    "languages": ["ru-RU", "ru", "en-US", "en", "uk"],
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

        curve = mouse_curve(
            (randint(0, 480), randint(0, 270)),
            (randint(1440, 1920), randint(810, 1022)),
            35
        )
        idx = randint(23, 30)
        mm = deepcopy(curve[:idx])
        mm_mp = randint(10, 20)+random()*randint(1, 4) # TODO: ???
        md = curve[idx].copy()
        mu = curve[idx].copy()
        ctime = start
        for m in mm:
            ctime += randint(20, 40)
            m.append(ctime)
        ctime += randint(30, 50)
        md.append(ctime)
        ctime += randint(30, 50)
        mu.append(ctime)
        j["mm"] = mm
        j["mm-mp"] = mm_mp
        j["md"] = md
        j["md-mp"] = 0
        j["mu"] = mu
        j["mu-mp"] = 0

        curve = mouse_curve(
            (randint(0, 480), randint(0, 270)),
            (randint(1440, 1920), randint(810, 1022)),
            70
        )
        idx = randint(60, 70)
        mm = curve[:idx]
        ctime = start+1000+randint(100, 150)
        for m in mm:
            ctime += randint(20, 40)
            m.append(ctime)
        j["topLevel"]["mm"] = mm
        j["topLevel"]["mm-mp"] = randint(100, 120)+random()*randint(1, 4)

        j["topLevel"]["wn"] = []
        j["topLevel"]["wn-mp"] = 0
        j["topLevel"]["xy"] = []
        j["topLevel"]["xy-mp"] = 0
        return j

    async def _solve_hsw(self, script, token):
        def _hsw():
            options = ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            driver = Chrome(service=Service(executable_path="chromedriver.exe"), options=options)
            #with open("test_hsw.js", "w") as f:
            #    f.write(f"{script}\n\nreturn await hsw(\"{token}\");")
            return driver.execute_script(f"{script}\n\nreturn await hsw(\"{token}\");")
        return await get_event_loop().run_in_executor(ThreadPoolExecutor(4), _hsw)

    async def _solve_hsl(self, token):
        raise RuntimeError("HSL not implemented!")

    async def solve(self):
        start = int(time() * 1000) - 2000
        sess = ClientSession(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"})
        siteconfig = await sess.post("https://hcaptcha.com/checksiteconfig", params={
            "v": "1f7dc62",
            "host": self.domain,
            "sitekey": self.sitekey,
            "sc": 1,
            "swa": 1
        })
        self._c = (await siteconfig.json())["c"]
        captcha = await sess.post(f"https://hcaptcha.com/getcaptcha/{self.sitekey}", data={
            "v": "1f7dc62",
            "host": self.domain,
            "sitekey": self.sitekey,
            "hl": "en-US",
            "n": await self._getN(),
            "c": jdumps(self._c),
            "motionData": await self._getMotionData(start)
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})

        captcha = await captcha.json()
        key = captcha["key"]
        tasklist = {task["task_key"]: task["datapoint_uri"] for task in captcha["tasklist"]}

        answers = await self._question_callback(captcha["requester_question"]["en"], tasklist)
        print(answers)

        res = await sess.post(f"https://hcaptcha.com/checkcaptcha/{self.sitekey}/{key}", json={
            "answers": answers,
            "v": "1f7dc62",
            "serverdomain": self.domain,
            "job_mode": "image_label_binary",
            "c": jdumps(self._c),
            "n": await self._getN(),
            "sitekey": self.sitekey,
            "motionData": jdumps(await self._getMotionData(start))
        })

        r = await res.text()
        await sess.close()
        return r

async def getAnswers(question, tasklist):
    answers = {}

    tl = {str(i): list(tasklist.keys())[i] for i in range(len(tasklist.keys()))}
    for i, k in tl.items():
        with open(f"captcha_images/{i}.jpg", "wb") as f:
            f.write(await getUrl(tasklist[k], False))

    print(question)

    for i, uuid in tl.items():
        ans = input(f"{i}? ").lower()
        if ans in ("1", "true"):
            answers[uuid] = "true"
        else:
            answers[uuid] = "false"
    return answers

async def main():
    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo", getAnswers)
    resp = await solver.solve()
    print(resp)  # {"success":false,"error-codes":["invalid-data"]} ??

if __name__ == "__main__":
    from asyncio import run, get_event_loop

    run(main())