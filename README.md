# AsyncHcaptcha

### Installing
Python 3.7 or higher and chrome with chromedriver are required
```sh
pip install asynchcaptcha
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
    from asyncio import get_event_loop, sleep as asleep
    get_event_loop().run_until_complete(main())

```

# TODO
  - Make hsw solving without selenium
  - Add automatic solver
  - Add custom parameters support (captcha_rqdata)