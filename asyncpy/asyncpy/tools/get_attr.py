#-*- coding:utf-8 -*-

def get_attrs(settings):
    attr = {}
    for i in (dir(settings)):
        if i.isupper():
            attr[i] = getattr(settings,i)
    return attr
