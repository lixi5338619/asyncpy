# -*- coding: utf-8 -*-
# @Author  : lx



from asyncpy.middleware import Middleware

middleware = Middleware()

@middleware.request
async def UserAgentMiddleware(spider, request):
    print("spider name :%s"%spider.name)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3100.0 Safari/537.36"
    request.headers.update({"User-Agent": ua})



@middleware.request
async def ProxyMiddleware(spider, request):
    #request.aiohttp_kwargs.update({"proxy": "http://121.56.38.77:4267"})
    pass

