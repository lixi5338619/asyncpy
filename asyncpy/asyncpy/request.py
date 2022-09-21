# -*- coding: utf-8 -*-

import aiohttp
import asyncio
from asyncpy.exceptions import InvalidRequestMethod
from typing import Coroutine, Optional, Tuple
from asyncpy.tools import check_logger, get_logger
from asyncpy.response import Response
import async_timeout
from inspect import iscoroutinefunction, getabsfile
from asyncio.locks import Semaphore
from types import AsyncGeneratorType
import weakref
import traceback
from asyncpy import settings


class Request(object):
    name = "Request"

    REQUEST_CONFIG = settings.DEFAULT_REQUEST_CONFIG
    REQUEST_CONFIG["RETRY_FUNC"] = Coroutine
    REQUEST_CONFIG["VALID"] = Coroutine

    METHOD = ["GET", "POST"]

    def __init__(self,
                 url: str,
                 method: str = "GET", *,
                 settings_attr=None,
                 callback=None, encoding: Optional[str] = None,
                 headers: dict = None,
                 cookies: dict = None,
                 meta: dict = None, custom_settings: dict = None,
                 request_session=None, **aiohttp_kwargs):
        self.url = url
        self.method = method.upper()
        self.custom_settings = None

        if self.method not in self.METHOD:
            raise InvalidRequestMethod("%s method is not supported" % self.method)

        self.callback = callback
        self.encoding = encoding
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.meta = meta or {}
        self.request_session = request_session

        self.settings_attr = settings_attr or {}
        if self.settings_attr and settings_attr.get('USER_AGENT'):
            self.headers['User-Agent'] = settings_attr.get('USER_AGENT')

        self.request_settings = self.REQUEST_CONFIG
        if self.settings_attr and settings_attr.get('DEFAULT_REQUEST_CONFIG'):
            self.request_settings = settings_attr.get('DEFAULT_REQUEST_CONFIG')

        if custom_settings:
            self.request_settings = custom_settings

        self.ssl = aiohttp_kwargs.pop("ssl", False)
        self.aiohttp_kwargs = aiohttp_kwargs

        self.close_request_session = False

        if custom_settings and custom_settings.get('LOG_FILE'):
            LOG_FILE, LOG_LEVEL = custom_settings.get('LOG_FILE'), custom_settings.get('LOG_LEVEL', 'INFO')
            self.logger = get_logger(name=self.name, filename=LOG_FILE, level=LOG_LEVEL)
        else:
            self.logger = check_logger(name=self.name)

        self.retry_times = self.request_settings.get("RETRIES", 3)

    @property
    def current_request_session(self):
        if self.request_session is None:
            self.request_session = aiohttp.ClientSession()
            self.close_request_session = True
        return self.request_session

    async def fetch(self, delay=True) -> Response:
        """Fetch all the information by using aiohttp"""
        if delay and self.request_settings.get("DOWNLOAD_DELAY", 0) > 0:
            await asyncio.sleep(self.request_settings["DOWNLOAD_DELAY"])

        timeout = self.request_settings.get("DOWNLOAD_TIMEOUT", 10)
        try:
            async with async_timeout.timeout(timeout):
                resp = await self._make_request()
            try:
                resp_data = await resp.text(encoding=self.encoding)
            except UnicodeDecodeError:
                resp_data = await resp.read()

            response = Response(
                url=str(resp.url),
                method=resp.method,
                encoding=resp.get_encoding(),
                text=resp_data,
                meta=self.meta,
                cookies=resp.cookies,
                headers=resp.headers,
                history=resp.history,
                status=resp.status,
                aws_json=resp.json,
                aws_text=resp.text,
                aws_read=resp.read,
            )
            aws_valid_response = self.request_settings.get("VALID")
            if aws_valid_response and iscoroutinefunction(aws_valid_response):
                response = await aws_valid_response(response)
            if response.ok:
                return response
            else:
                return await self._retry(
                    error_msg=f"Request url failed with status {response.status}!"
                )
        except asyncio.TimeoutError:
            return await self._retry(error_msg="timeout")
        except Exception as e:
            return await self._retry(error_msg=e)
        finally:
            await self._close_request()

    async def fetch_callback(
            self, sem: Semaphore
    ) -> Tuple[AsyncGeneratorType, Response]:
        """
        Request the target url and then call the callback function
        :param sem: Semaphore
        :return: Tuple[AsyncGeneratorType, Response]
        """
        try:
            async with sem:
                response = await self.fetch()
        except Exception as e:
            response = None
            self.logger.error(f"<Error: {self.url} {e}>")
            self.logger.error(f"{traceback.format_exc()}")
        if self.callback is not None:
            if iscoroutinefunction(self.callback):
                callback_result = await self.callback(response)
            else:
                callback_result = self.callback(response)
        else:
            callback_result = None
        return callback_result, response

    async def _close_request(self):
        if self.close_request_session:
            await self.request_session.close()

    async def _make_request(self):
        """Aiohttp send request"""
        self.logger.info(f"<{self.method}: {self.url}>")
        if self.method == "GET":
            request_func = self.current_request_session.get(
                self.url, headers=self.headers, cookies=self.cookies, ssl=self.ssl, **self.aiohttp_kwargs
            )
        else:
            request_func = self.current_request_session.post(
                self.url, headers=self.headers, cookies=self.cookies, ssl=self.ssl, **self.aiohttp_kwargs
            )
        resp = await request_func
        return resp

    async def _retry(self, error_msg):
        """Manage request"""
        if self.retry_times > 0:
            # Sleep to give server a chance to process/cache prior request
            if self.request_settings.get("RETRY_DELAY", 0) > 0:
                await asyncio.sleep(self.request_settings["RETRY_DELAY"])

            retry_times = self.request_settings.get("RETRIES", 3) - self.retry_times + 1
            self.logger.error(
                f"<Retry url: {self.url}>, Retry times: {retry_times}, Retry message: {error_msg}>"
            )
            self.logger.error(f"{traceback.format_exc()}")

            self.retry_times -= 1
            retry_func = self.request_settings.get("RETRY_FUNC")
            if retry_func and iscoroutinefunction(retry_func):
                request_ins = await retry_func(weakref.proxy(self))
                if isinstance(request_ins, Request):
                    return await request_ins.fetch(delay=False)
            return await self.fetch(delay=False)
        else:
            response = Response(
                url=self.url,
                method=self.method,
                meta=self.meta,
                cookies={},
                history=(),
                headers=None,
            )

            return response

    def __repr__(self):
        return f"<{self.method} {self.url}>"
