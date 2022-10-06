# AsyncHcaptcha

### Installing
Python 3.7 or higher and chrome with chromedriver are required
```sh
pip install async-hcaptcha
```

### Example
```py
from async_hcaptcha import AioHcaptcha
from async_hcaptcha.utils import getUrl

async def getAnswers(question, tasklist):
    answers = {}

    tl = {str(i): list(tasklist.keys())[i] for i in range(len(tasklist.keys()))}
    for i, k in tl.items():
        with open(f"captcha_images/{i}.jpg", "wb") as f:
            f.write(await getUrl(tasklist[k], False))

    print(question)
    print("Answer with true/false or 1/0:")

    for i, uuid in tl.items():
        ans = input(f"{i}? ").lower()
        if ans in ("1", "true"):
            answers[uuid] = "true"
        else:
            answers[uuid] = "false"
    return answers

async def main():
    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo", getAnswers,
                         {"executable_path": "chromedriver.exe"})
    resp = await solver.solve()
    print(resp)

if __name__ == "__main__":
    from asyncio import get_event_loop
    get_event_loop().run_until_complete(main())

```

### Automatically solved example
```py
from async_hcaptcha import AioHcaptcha

async def main():
    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo",
                         {"executable_path": "chromedriver.exe"})
    resp = await solver.solve()
    print(resp)

if __name__ == "__main__":
    from asyncio import get_event_loop
    get_event_loop().run_until_complete(main())
```

### Captcha with rqdata example
```py
from async_hcaptcha import AioHcaptcha

async def main():
    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo",
                         {"executable_path": "chromedriver.exe"})
    resp = await solver.solve(custom_params={"rqdata": "xHJHshn3p71FcYoVCW5zA3m2CFw59JXBecFaR2l90z/NjjoYaXq2FBTi05LPnOX1v/MwStZg9DZKQA4f4ExkDjwlMaS3AKGIrcb2rUKsg8nDI9IaXEFDAhWqvuuCuaW3urxO2J1B/NEkfS938O58cqrE00aPILCQPUHVU1l/Ek8"})
    print(resp)

if __name__ == "__main__":
    from asyncio import get_event_loop
    get_event_loop().run_until_complete(main())
```

# TODO
  - Make hsw solving without selenium
  
### Async-hcaptcha using code from [hcaptcha-challenger](https://github.com/QIN2DIM/hcaptcha-challenger/tree/main/src/services/hcaptcha_challenger/solutions) and [py-hcaptcha](https://github.com/AcierP/py-hcaptcha/blob/main/hcaptcha/proofs/hsl.py).
