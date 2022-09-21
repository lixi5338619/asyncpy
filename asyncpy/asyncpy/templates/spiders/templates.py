# -*- coding: utf-8 -*-

from asyncpy.spider import Spider


class DemoSpider(Spider):
    name = 'templates'

    start_urls = []


    async def parse(self, response):
        pass



DemoSpider.start()