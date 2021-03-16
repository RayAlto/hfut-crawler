from re import search as re_search

from . import tools


class Webvpn:

    index_url: str = 'https://webvpn.hfut.edu.cn'

    def __init__(self) -> None:
        self.__user_config: dict = tools.load_config()
        self.__requests_session: tools.Session = tools.generate_session()
        self.__logged_in: bool = False

        self.protals: list = None

    def login(self) -> bool:
        captcha_response = self.__requests_session.get(f'{self.index_url}/login')
        login_data = self.__user_config.copy()
        login_data.update({
            'captcha_id': re_search(r'name="captcha_id" value="(\w+)"', captcha_response.text).group(1),
            'sms_code': '',
            'captcha': '',
            'needCaptcha': False
        })
        tools.print_log('Webvpn.login -> Try to log in webvpn ...')
        login_response = self.__requests_session.post(f'{self.index_url}/do-login', data=login_data)
        login_result: dict = tools.load_json(login_response.text)
        if login_result.get('success'):
            tools.print_log('Succeed')
            self.__logged_in = True
            return True

        tools.print_log('Webvpn.login -> Failed')
        return False

    def get_portals(self) -> list:
        tools.print_log('Webvpn.get_portals -> Try to get portals')
        while not self.__logged_in:
            tools.print_log('Webvpn.get_portals -> Not logged in')
            if not self.login():
                self.__requests_session = tools.generate_session()
                tools.rand_sleep()
        portals_response = self.__requests_session.get(f'{self.index_url}/user/portal_groups',
                                                       data={'_': tools.current_timestamp()})
        self.portals: list = tools.load_json(portals_response.text).get('data')
        return self.portals


class JxglWebvpn:

    index_url: str = None

    def __init__(self, webvpn: Webvpn) -> None:
        self.__user_config: dict = webvpn.__user_config.copy()
        self.__requests_session: webvpn.__requests_session
        self.__logged_in: bool = False

        # generate jxgl url
        while webvpn.portals is None:
            webvpn.get_portals()
        for data in webvpn.portals:
            for res in data.get('resource'):
                if res.get('name') == '教务系统学生端' and res.get('detail') == 'jxglstu.hfut.edu.cn':
                    self.index_url = f'{webvpn.index_url}{res.get("redirect")}'.removesuffix('login')

    def login(self) -> bool:
        salt = self.__requests_session.get(f'{self.index_url}login-salt').text
        self.__requests_session.headers.update({'Content-Type': 'application/json;charset=UTF-8'})
        login_response = self.__requests_session.post(f'{self.index_url}login',
                                                      json={
                                                          'username':
                                                          self.__user_config.get('username'),
                                                          'password':
                                                          tools.sha1_calc(
                                                              f'{salt}-{self.__user_config.get("password")}'.encode('utf-8')),
                                                          'captcha':
                                                          ''
                                                      })
        self.__requests_session.headers.pop('Content-Type')
        login_result = tools.load_json(login_response.text)
        if login_result.get('result'):
            self.__logged_in = True
            return True
        return False