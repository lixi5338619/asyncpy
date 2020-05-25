# -*- coding: utf-8 -*-

"""Asyncpy
Usage:
  asyncpy genspider <name>
  asyncpy (-h | --help | --version)
Options:
  --version        Show version.
"""


from asyncpy.middleware import Middleware
from asyncpy.request import Request
from asyncpy.response import Response
from asyncpy.spider import Spider
from asyncpy.exceptions import IgnoreThisItem
from pathlib import Path
from docopt import docopt

__all__ = ["Middleware","Request","Response","Spider","IgnoreThisItem"]


VERSION = '1.1.5'

DEFAULT_ENCODING = 'utf-8'


import os
import shutil
def create_base(name):
    template = 'templates'
    template_path = Path(__file__).parent / template
    project_path = os.path.join(os.getcwd(), name)
    if not os.path.exists(project_path):
        shutil.copytree(template_path, project_path)
        os.rename(project_path,project_path)
        spider_path = os.path.join(project_path, 'spiders/templates.py')
        new_spider_path = os.path.join(project_path, 'spiders/{}.py'.format(name))
        os.rename(spider_path,new_spider_path)

        with open(file=new_spider_path,mode='r',encoding='utf-8')as f:
            doc = f.read()
            doc = doc.replace('templates',name).replace('Demo',name.capitalize())
            with open(file=new_spider_path,mode='w',encoding='utf-8')as f1:
                f1.write(doc)
                print("Created successfully")
    else:
        print("file already exist")





def cli():
    """
    Commandline for Asyncpy :d
    """
    argv = docopt(__doc__, version=VERSION)
    if argv.get('genspider'):
        name = argv['<name>']
        create_base(name=name)