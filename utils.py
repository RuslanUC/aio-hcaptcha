from math import ceil
from random import choice

from aiohttp import ClientSession


def _bezier(xys, ts):
    result = []
    for t in ts:
        tpowers = (t ** i for i in range(4))
        upowers = reversed([(1 - t) ** i for i in range(4)])
        coefs = [c * a * b for c, a, b in zip([1, 3, 3, 1], tpowers, upowers)]
        result.append(list(sum([coef * p for coef, p in zip(coefs, ps)]) for ps in zip(*xys)))
    return result

def mouse_curve(start_pos, end_pos, ln):
    ts = [t / ln for t in range(int(ln / 100 * 101))]
    control_1 = (start_pos[0] + choice((-1, 1)) * abs(ceil(end_pos[0]) - ceil(start_pos[0])) * 0.01 * 3,
                 start_pos[1] + choice((-1, 1)) * abs(ceil(end_pos[1]) - ceil(start_pos[1])) * 0.01 * 3)
    control_2 = (start_pos[0] + choice((-1, 1)) * abs(ceil(end_pos[0]) - ceil(start_pos[0])) * 0.01 * 3,
                 start_pos[1] + choice((-1, 1)) * abs(ceil(end_pos[1]) - ceil(start_pos[1])) * 0.01 * 3)
    xys = [start_pos, control_1, control_2, end_pos]
    points = _bezier(xys, ts)
    return [[ceil(x), ceil(y)] for x, y, in points]

async def getUrl(url, decode=True):
    async with ClientSession() as sess:
        async with sess.get(url) as resp:
            data = await resp.content.read()
            if not decode:
                return data
            return data.decode("utf8")