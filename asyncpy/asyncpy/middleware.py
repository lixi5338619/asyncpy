# -*- coding: utf-8 -*-



from collections import deque
from functools import wraps

class Middleware:
    """
    Define a middleware to customize the crawler request or response
    eg: middleware = Middleware()
    """

    def __init__(self):
        """
            创建1个可双向扩展的队列deque
        """
        self.request_middleware = deque()
        self.response_middleware = deque()


    def request(self, *args, **kwargs):
        """
        Define a Decorate to be called before a request.
        """
        middleware = args[0]

        @wraps(middleware)
        def register_middleware(*args, **kwargs):
            """
            @wraps：保留原有函数的名称和属性
            """
            self.request_middleware.append(middleware)
            return middleware

        return register_middleware()

    def response(self, *args, **kwargs):
        middleware = args[0]

        @wraps(middleware)
        def register_middleware(*args, **kwargs):
            self.response_middleware.appendleft(middleware)
            return middleware

        return register_middleware()


    def __add__(self, other):
        new_middleware = Middleware()

        new_middleware.request_middleware.extend(self.request_middleware)
        new_middleware.request_middleware.extend(other.request_middleware)

        new_middleware.response_middleware.extend(other.response_middleware)
        new_middleware.response_middleware.extend(self.response_middleware)
        return new_middleware


