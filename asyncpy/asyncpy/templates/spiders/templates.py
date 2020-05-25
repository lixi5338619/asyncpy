# -*- coding: utf-8 -*-


from asyncpy.spider import Spider
import settings


class DemoSpider(Spider):
    name = 'templates'
    settings_attr = settings

    start_urls = []



    async def parse(self, response):
        pass



DemoSpider.start()