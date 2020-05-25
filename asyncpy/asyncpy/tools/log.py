# -*- coding: utf-8 -*-
# @Author  : lx

import logging
from asyncpy import settings



def get_logger(name="Asyncpy",filename=None,level=logging.INFO):
    logging_format = f"[%(asctime)s] %(levelname)-5s %(name)-{len(name)}s "
    logging_format += "%(message)s"

    logging.basicConfig(
        filename=filename,filemode='a',
        format=logging_format, level=level, datefmt="%Y:%m:%d %H:%M:%S",
    )

    logging.getLogger("asyncio").setLevel(level)
    logging.getLogger("websockets").setLevel(level)
    return logging.getLogger(name)




def check_logger(name):
    if 'LOG_FILE' and 'LOG_LEVEL' in dir(settings):
        logger = get_logger(name=name, filename=settings.LOG_FILE, level=settings.LOG_LEVEL)
    else:
        logger = get_logger(name=name)
    return logger