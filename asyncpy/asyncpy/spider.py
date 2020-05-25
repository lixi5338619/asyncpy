# -*- coding: utf-8 -*-


import asyncio
import collections
import typing
import weakref
import traceback
from datetime import datetime
from functools import reduce
from inspect import isawaitable,getabsfile
from signal import SIGINT, SIGTERM
from types import AsyncGeneratorType
from aiohttp import ClientSession
from asyncpy.exceptions import InvalidCallbackResult,NotImplementedParseError,NothingMatchedError
from asyncpy.exceptions import SpiderHookError
from asyncpy.middleware import Middleware
from asyncpy.request import Request
from asyncpy.response import Response
from asyncpy.tools import check_logger,get_logger,get_attrs
import importlib
import sys






try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


class SpiderHook:
    """
    SpiderHook is used for extend spider
    """

    callback_result_map: dict = None

    async def _run_spider_hook(self, hook_func):
        """
        Run hook before/after spider start crawling
        :param hook_func: aws function
        :return:
        """
        if callable(hook_func):
            try:
                aws_hook_func = hook_func(weakref.proxy(self)) # 创建弱引用
                if isawaitable(aws_hook_func):          # 如果对象isawait可返回True
                    await aws_hook_func
            except Exception as e:
                raise SpiderHookError(f"<Hook {hook_func.__name__}: {e}")

    async def process_failed_response(self, request, response):
        """     失败响应的处理
        Corresponding processing for the failed response
        :param request: Request
        :param response: Response
        :return:
        """
        pass

    async def process_succeed_response(self, request, response):
        """     成功响应的处理
        Corresponding processing for the succeed response
        :param request: Request
        :param response: Response
        :return:
        """
        pass

    async def process_item(self, item,spider):
        """
        Corresponding processing for the Item type
        """
        pass


    async def process_callback_result(self, callback_result):
        """
        Corresponding processing for the invalid callback result
        :param callback_result: Custom instance
        :return:
        """
        callback_result_name = type(callback_result).__name__
        process_func_name = self.callback_result_map.get(callback_result_name, "")
        process_func = getattr(self, process_func_name, None)
        if process_func is not None:
            await process_func(callback_result)
        else:
            raise InvalidCallbackResult(
                f"<Parse invalid callback result type: {callback_result_name}>"
            )


class Spider(SpiderHook):
    """
    Spider is used for control requests better
    """
    name = None
    custom_settings = None
    settings_attr = None
    # Default values passing to each request object. Not implemented yet.
    headers: dict = None
    meta: dict = None
    aiohttp_kwargs: dict = None

    # Some fields for statistics
    failed_counts: int = 0
    success_counts: int = 0

    # Concurrency control
    worker_numbers: int = 2
    concurrency:  int = None

    # Spider entry
    start_urls: list = None

    # A queue to save coroutines
    worker_tasks: list = []



    def __init__(
        self,
        middleware: typing.Union[typing.Iterable, Middleware] = None,
        pipelines = None,
        loop=None,
        is_async_start: bool = False,
        cancel_tasks: bool = True,
        **spider_kwargs,
    ):
        """
        Init spider object.
        :param middleware: a list of or a single Middleware
        :param loop: asyncio event llo
        :param is_async_start: start spider by using async
        :param spider_kwargs
        """


        if not isinstance(self.start_urls, collections.Iterable):
            raise ValueError(
                "start_urls must be a Iterable object"
            )
        self.pipelines = pipelines
        self.loop = loop
        asyncio.set_event_loop(self.loop)

        # Init object-level properties
        self.callback_result_map = self.callback_result_map or {}

        self.custom_settings = self.custom_settings or {}
        self.headers = self.headers or {}
        self.meta = self.meta or {}
        self.aiohttp_kwargs = self.aiohttp_kwargs or {}
        self.spider_kwargs = spider_kwargs
        self.request_session = ClientSession()

        self.cancel_tasks = cancel_tasks
        self.is_async_start = is_async_start



        # customize middleware
        if isinstance(middleware, list):
            self.middleware = reduce(lambda x, y: x + y, middleware)
        else:
            self.middleware = middleware or Middleware()

        # async queue as a producer
        self.request_queue = asyncio.Queue()
        if not self.settings_attr:
            from asyncpy import settings
        else:
            self.settings_attr = get_attrs(self.settings_attr)
            self.concurrency = self.settings_attr.get('CONCURRENT_REQUESTS')
        if not self.concurrency:
            self.concurrency = settings.CONCURRENT_REQUESTS


        # set logger
        if  isinstance(self.settings_attr,dict) and self.settings_attr.get('LOG_FILE'):
            LOG_FILE, LOG_LEVEL = self.settings_attr.get('LOG_FILE'),self.settings_attr.get('LOG_LEVEL','INFO')
            self.logger = get_logger(name=self.name,filename=LOG_FILE,level=LOG_LEVEL)

        elif self.custom_settings and self.custom_settings.get('LOG_FILE'):
            LOG_FILE, LOG_LEVEL = self.custom_settings.get('LOG_FILE'),self.custom_settings.get('LOG_LEVEL','INFO')
            self.logger = get_logger(name=self.name,filename=LOG_FILE,level=LOG_LEVEL)
        else:
            self.logger = check_logger(name=self.name)


        # semaphore, used for concurrency control
        self.sem = asyncio.Semaphore(self.concurrency)





    async def _cancel_tasks(self):
        tasks = []
        for task in asyncio.Task.all_tasks():
            if task is not asyncio.tasks.Task.current_task():
                tasks.append(task)
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_async_callback(
        self, callback_results: AsyncGeneratorType, response: Response = None
    ):
        try:
            async for callback_result in callback_results:
                if isinstance(callback_result, AsyncGeneratorType):
                    await self._process_async_callback(callback_result)
                elif isinstance(callback_result, Request):
                    self.request_queue.put_nowait(
                        self.handle_request(request=callback_result)
                    )
                elif isinstance(callback_result, typing.Coroutine):
                    self.request_queue.put_nowait(
                        self.handle_callback(
                            aws_callback=callback_result, response=response
                        )
                    )
                elif isinstance(callback_result, dict):
                    #  根据类型判断是否回调给 pipelines

                    # for pipeline in self.pipelines:
                        pipel = self.pipelines()
                        pipel.process_item(item=callback_result,spider_name=self.name)

                else:
                    await self.process_callback_result(callback_result=callback_result)
        except NothingMatchedError as e:
            error_info = f"<Field: {str(e).lower()}" + f", error url: {response.url}>"
            self.logger.error(error_info)

        except Exception as e:
            self.logger.error(e)
            self.logger.error(f"{traceback.format_exc()}")

    async def _process_response(self, request: Request, response: Response):
        if response:
            if response.ok:
                # Process succeed response
                self.success_counts += 1
                await self.process_succeed_response(request, response)
            else:
                # Process failed response
                self.failed_counts += 1
                await self.process_failed_response(request, response)

    async def _run_request_middleware(self, request: Request):
        if self.middleware.request_middleware:
            for middleware in self.middleware.request_middleware:
                if callable(middleware):
                    try:
                        aws_middleware_func = middleware(self, request)
                        if isawaitable(aws_middleware_func):
                            await aws_middleware_func
                        else:
                            self.logger.error(
                                f"<Middleware {middleware.__name__}: must be a coroutine function"
                            )
                            self.logger.error(f"{traceback.format_exc()}")

                    except Exception as e:
                        self.logger.error(f"<Middleware {middleware.__name__}: {e}")
                        self.logger.error(f"{traceback.format_exc()}")

    async def _run_response_middleware(self, request: Request, response: Response):
        if self.middleware.response_middleware:
            for middleware in self.middleware.response_middleware:
                if callable(middleware):
                    try:
                        aws_middleware_func = middleware(self, request, response)
                        if isawaitable(aws_middleware_func):
                            await aws_middleware_func
                        else:
                            self.logger.error(
                                f"<Middleware {middleware.__name__}: must be a coroutine function"
                            )

                    except Exception as e:
                        self.logger.error(f"<Middleware {middleware.__name__}: {e}")
                        self.logger.error(f"{traceback.format_exc()}")

    async def _start(self, after_start=None, before_stop=None):
        self.logger.info("Spider started!")
        start_time = datetime.now()
        global now_time
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Add signal
        for signal in (SIGINT, SIGTERM):
            try:
                self.loop.add_signal_handler(
                    signal, lambda: asyncio.ensure_future(self.stop(signal))
                )
            except NotImplementedError:
                self.logger.warning(
                    f"{self.name} tried to use loop.add_signal_handler "
                    "but it is not implemented on this platform."
                )
        # Run hook before spider start crawling
        await self._run_spider_hook(after_start)

        # Actually run crawling
        try:
            await self.start_master()
        finally:
            # Run hook after spider finished crawling
            await self._run_spider_hook(before_stop)
            await self.request_session.close()
            # Display logs about this crawl task
            end_time = datetime.now()
            self.logger.info(
                f"Total requests: {self.failed_counts + self.success_counts}"
            )

            if self.failed_counts:
                self.logger.info(f"Failed requests: {self.failed_counts}")
            self.logger.info(f"Time usage: {end_time - start_time}")
            self.logger.info("Spider finished!")





    @classmethod
    async def async_start(
        cls,
        middleware: typing.Union[typing.Iterable, Middleware] = None,
        pipelines= None,
        loop=None,
        after_start=None,
        before_stop=None,
        cancel_tasks: bool = True,
        **spider_kwargs,
    ):
        """
        Start an async spider
        :param middleware: customize middleware or a list of middleware
        :param loop:
        :param after_start: hook
        :param before_stop: hook
        :param cancel_tasks: cancel async tasks
        :param spider_kwargs: Additional keyword args to initialize spider
        :return: An instance of :cls:`Spider`
        """

        loop = loop or asyncio.get_event_loop()
        spider_ins = cls(
            middleware=middleware,
            pipelines= pipelines,
            loop=loop,
            is_async_start=True,
            cancel_tasks=cancel_tasks,
            **spider_kwargs,
        )
        await spider_ins._start(after_start=after_start, before_stop=before_stop)

        return spider_ins


    @classmethod
    def start(
        cls,
        middleware: typing.Union[typing.Iterable, Middleware] = None,
        pipelines = None,
        loop=None,
        after_start=None,
        before_stop=None,
        close_event_loop=True,
        **spider_kwargs):


        # if 'MIDDLEWARE' in dir(setting):
        #     mw_list = setting.MIDDLEWARE
        #     if mw_list:
        #         for path in mw_list:
        #             clast = path.split('.')[0]
        #             miast = path.split('.')[1]
        #             middleware_path = getabsfile(setting).replace('setting.py',clast+'.py')


        # pipelines_list = []
        # if 'PIPELINES' in dir(setting):
        #     pl_list = setting.PIPELINES
        #     if pl_list:
        #         for path in pl_list:
        #             modlt = path.split('.')[0]
        #             clast = path.split('.')[1]
        #             pilelines_path = getabsfile(setting).replace('setting.py',modlt+'.py')
        #             sys.path.append(pilelines_path)
        #             ret = importlib.import_module(modlt)
        #             pipelines = getattr(ret,clast)
        #             pipelines_list.append(pipelines)




        loop = loop or asyncio.new_event_loop()
        spider_ins = cls(middleware=middleware, loop=loop, **spider_kwargs,pipelines=pipelines)

        # Actually start crawling
        spider_ins.loop.run_until_complete(
            spider_ins._start(after_start=after_start, before_stop=before_stop)
        )
        spider_ins.loop.run_until_complete(spider_ins.loop.shutdown_asyncgens())
        if close_event_loop:
            spider_ins.loop.close()

        return spider_ins



    async def handle_callback(self, aws_callback: typing.Coroutine, response):
        """Process coroutine callback function"""
        callback_result = None

        try:
            callback_result = await aws_callback
        except NothingMatchedError as e:
            self.logger.error(f"<Item: {str(e).lower()}>")
            self.logger.error(f"{traceback.format_exc()}")

        except Exception as e:
            self.logger.error(f"<Callback[{aws_callback.__name__}]: {e}")
            self.logger.error(f"{traceback.format_exc()}")

        return callback_result, response


    async def handle_request(
        self, request: Request
    ) -> typing.Tuple[AsyncGeneratorType, Response]:
        """
        Wrap request with middleware.
        :param request:
        :return:
        """
        callback_result, response = None, None

        try:
            await self._run_request_middleware(request)
            callback_result, response = await request.fetch_callback(self.sem)
            await self._run_response_middleware(request, response)
            await self._process_response(request=request, response=response)
        except NotImplementedParseError as e:
            self.logger.error(e)
        except NothingMatchedError as e:
            error_info = f"<Field: {str(e).lower()}" + f", error url: {request.url}>"
            self.logger.error(error_info)
        except Exception as e:
            self.logger.error(f"<Callback[{request.callback.__name__}]: {e}")
            self.logger.error(f"{traceback.format_exc()}")

        return callback_result,response


    async def multiple_request(self, urls, is_gather=False, **kwargs):
        """For crawling multiple urls"""
        if is_gather:
            resp_results = await asyncio.gather(
                *[self.handle_request(self.request(url=url, **kwargs)) for url in urls],
                return_exceptions=True,
            )
            for index, task_result in enumerate(resp_results):
                if not isinstance(task_result, RuntimeError) and task_result:
                    _, response = task_result
                    response.index = index
                    yield response
        else:
            for index, url in enumerate(urls):
                _, response = await self.handle_request(self.request(url=url, **kwargs))
                response.index = index
                yield response


    async def parse(self, response):
        """
        Used for subclasses, directly parse the responses corresponding with start_urls
        :param response: Response
        :return:
        """
        raise NotImplementedParseError("<!!! parse function is expected !!!>")



    async def start_requests(self):
        """
        :return: AN async iterator
        """
        for url in self.start_urls:
            yield self.request(url=url, callback=self.parse, meta=self.meta)


    def request(
        self,
        url: str,
        method: str = "GET",
        *,
        callback=None,
        encoding: typing.Optional[str] = None,
        headers: dict = None,
        meta: dict = None,
        custom_settings: dict = None,
        request_session=None,
        **aiohttp_kwargs,
    ):
        """Init a Request class for crawling html"""
        headers = headers or {}
        meta = meta or {}
        custom_settings = custom_settings or {}
        request_session = request_session or self.request_session

        headers.update(self.headers.copy())
        custom_settings.update(self.custom_settings.copy())
        aiohttp_kwargs.update(self.aiohttp_kwargs.copy())

        return Request(
            url=url,
            method=method,
            settings_attr = self.settings_attr,
            callback=callback,
            encoding=encoding,
            headers=headers,
            meta=meta,
            custom_settings=custom_settings,
            request_session=request_session,
            **aiohttp_kwargs,
        )

    async def start_master(self):
        """Actually start crawling."""
        async for request_ins in self.start_requests():
            self.request_queue.put_nowait(self.handle_request(request_ins))
        workers = [
            asyncio.ensure_future(self.start_worker())
            for i in range(self.worker_numbers)
        ]
        self.logger.info(f"Worker started")
        for worker in workers:
            self.logger.info(f"ensure_future started_worker: {id(worker)}")

        await self.request_queue.join()

        if not self.is_async_start:
            await self.stop(SIGINT)
        else:
            if self.cancel_tasks:
                await self._cancel_tasks()


    async def start_worker(self):
        date2 = datetime.strptime(now_time, "%Y-%m-%d %H:%M:%S")
        while True:
            request_item = await self.request_queue.get()
            self.worker_tasks.append(request_item)
            if self.request_queue.empty():
                results = await asyncio.gather(
                    *self.worker_tasks, return_exceptions=True
                )
                for task_result in results:
                    if not isinstance(task_result, RuntimeError) and task_result:
                        callback_results, response = task_result
                        if isinstance(callback_results, AsyncGeneratorType):
                            await self._process_async_callback(
                                callback_results, response
                            )

                self.worker_tasks = []

            self.request_queue.task_done()


    async def stop(self, _signal):
        """
        Finish all running tasks, cancel remaining tasks, then stop loop.
        :param _signal:
        :return:
        """
        self.logger.info(f"Asyncpy finished spider: {self.name}")
        await self._cancel_tasks()
        self.loop.stop()