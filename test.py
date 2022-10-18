from asyncio import get_running_loop, new_event_loop
import pytest as pt
from aiohttp import ClientSession
from async_hcaptcha import AioHcaptcha

@pt.fixture(scope="session")
def event_loop():
    try:
        loop = get_running_loop()
    except RuntimeError:
        loop = new_event_loop()
    yield loop
    loop.close()

@pt.mark.asyncio
async def test_simple_chromedriver():
    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo",
                         {"chromedriver": "chromedriver"})
    resp = await solver.solve(retry_count=3)
    assert resp is not None
    async with ClientSession() as sess:
        r = await sess.post("https://accounts.hcaptcha.com/demo?sitekey=a5f74b19-9e45-40e0-b45d-47ff91b7a6c2",
                            headers={"Content-Type": "application/x-www-form-urlencoded"},
                            data={"email": "", "g-recaptcha-response": resp, "h-captcha-response": resp})
        assert "Verification Success!" in await r.text()

@pt.mark.asyncio
async def test_with_rqdata_chromedriver():
    solver = AioHcaptcha("f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34", "https://discord.com/channels/@me",
                         {"chromedriver": "chromedriver"})
    resp = await solver.solve(
        retry_count=5,
        custom_params={"rqdata": "xHJHshn3p71FcYoVCW5zA3m2CFw59JXBecFaR2l90z/NjjoYaXq2FBTi05LPnOX1v/MwStZg9DZKQA4f4ExkDjwlMaS3AKGIrcb2rUKsg8nDI9IaXEFDAhWqvuuCuaW3urxO2J1B/NEkfS938O58cqrE00aPILCQPUHVU1l/Ek8"}
    )
    assert resp is not None

#@pt.mark.asyncio
#async def test_simple_node():
#    solver = AioHcaptcha("a5f74b19-9e45-40e0-b45d-47ff91b7a6c2", "https://accounts.hcaptcha.com/demo",
#                         {"node": "node"})
#    resp = await solver.solve(retry_count=3)
#    assert resp is not None
#    async with ClientSession() as sess:
#        r = await sess.post("https://accounts.hcaptcha.com/demo?sitekey=a5f74b19-9e45-40e0-b45d-47ff91b7a6c2",
#                            headers={"Content-Type": "application/x-www-form-urlencoded"},
#                            data={"email": "", "g-recaptcha-response": resp, "h-captcha-response": resp})
#        assert "Verification Success!" in await r.text()
#
#@pt.mark.asyncio
#async def test_with_rqdata_node():
#    solver = AioHcaptcha("f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34", "https://discord.com/channels/@me",
#                         {"node": "node"})
#    resp = await solver.solve(
#        retry_count=3,
#        custom_params={"rqdata": "xHJHshn3p71FcYoVCW5zA3m2CFw59JXBecFaR2l90z/NjjoYaXq2FBTi05LPnOX1v/MwStZg9DZKQA4f4ExkDjwlMaS3AKGIrcb2rUKsg8nDI9IaXEFDAhWqvuuCuaW3urxO2J1B/NEkfS938O58cqrE00aPILCQPUHVU1l/Ek8"}
#    )
#    assert resp is not None