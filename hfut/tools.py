from argparse import ArgumentParser
from argparse import FileType as ArgFileType
from base64 import b64encode
from hashlib import sha1
from json import loads as load_json
from random import uniform as randfloat
from time import localtime
from time import sleep
from time import time as time_sec

from requests import Session

user_config = None


def base64_calc(text: str) -> str:
    return b64encode(text.encode('utf-8')).decode('utf-8')


def current_timestamp(precise: bool = True) -> str:
    if precise:
        return f'{int(time_sec()*1000)}'
    return f'{int(time_sec())}000'


def generate_session(mobile: bool = False) -> Session:
    session = Session()
    if mobile:
        session.headers.update({
            'User-Agent':
            'Mozilla/5.0 (Linux; Android 9; MI 6X Build/PKQ1.180904.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/88.0.4324.181 Mobile Safari/537.36'
        })
    else:
        session.headers.update({
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        })
    return session


def load_config() -> dict:
    global user_config
    if user_config:
        print_log('tools.load_config -> Config already loaded')
        return user_config
    print_log('tools.load_config -> Read config from arg')
    arg_parse = ArgumentParser(description='Get data about you at hfut', epilog='https://github.com/RayAlto/hfut-crawler')
    arg_parse.add_argument('-c',
                           nargs='?',
                           metavar='config file',
                           type=ArgFileType('r', encoding='utf-8'),
                           default='config.json',
                           help='input config file')
    user_config = load_json(arg_parse.parse_args().c.read())
    return user_config


def print_log(text: str) -> None:
    print(f'[{"%.2d-%.2d-%.2d %.2d:%.2d:%.2d" % localtime()[:6]}]: {text}')


def rand_sleep(min_sec: int = 5, max_sec: int = 10):
    sleep(randfloat(min_sec, max_sec))


def sha1_calc(text: str) -> str:
    return sha1(text.encode('utf-8')).hexdigest()
