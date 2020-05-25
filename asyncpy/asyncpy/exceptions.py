# -*- coding: utf-8 -*-
# @Author  : lx


class IgnoreThisItem(Exception):
    pass


class InvalidCallbackResult(Exception):
    pass


class InvalidFuncType(Exception):
    pass


class InvalidRequestMethod(Exception):
    pass


class NotImplementedParseError(Exception):
    pass


class NothingMatchedError(Exception):
    pass


class SpiderHookError(Exception):
    pass


class AsyncpyDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """
    pass


class CloseSpider_Warning(Warning):
    # CLOSESPIDER_TIMEOUT
    pass