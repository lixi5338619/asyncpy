# -*- coding: utf-8 -*-


from asyncpy.middleware import Middleware
from asyncpy.request import Request
from asyncpy.spider import Spider


middleware = Middleware()


@middleware.request
async def UserAgentMiddleware(spider:Spider, request: Request):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36"
    # request.aiohttp_kwargs.update({"proxy": ""})
