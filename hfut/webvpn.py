from re import search as re_search
from re import finditer as re_finditer
from re import DOTALL as RE_DOTALL

from bs4 import BeautifulSoup

from . import tools


class Webvpn:

    index_url: str = None

    def __init__(self) -> None:
        self.__user_config: dict = tools.load_config()
        self.__requests_session: tools.Session = tools.generate_session()
        self.__logged_in: bool = False

        self.protals: list = None

    def check_login_status(self) -> None:
        while not self.__logged_in:
            tools.print_log('Webvpn -> Not logged in')
            if not self.login():
                tools.rand_sleep()

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
        if not login_result.get('success'):
            tools.print_log('Webvpn.login -> Failed')
            self.__requests_session = tools.generate_session()
            return False
        tools.print_log('Webvpn.login -> Succeed')
        self.__logged_in = True
        return True

    def get_portals(self) -> list:
        tools.print_log('Webvpn.get_portals -> Try to get portals')
        self.check_login_status()
        portals_response = self.__requests_session.get(f'{self.index_url}/user/portal_groups',
                                                       data={'_': tools.current_timestamp()})
        self.portals: list = tools.load_json(portals_response.text).get('data')
        return self.portals

    def get_user_config(self) -> dict:
        return self.__user_config.copy()

    def get_requests_session(self) -> tools.Session:
        return self.__requests_session

    def get_jxgl_webvpn(self):
        return JxglWebvpn(self)


class JxglWebvpn:

    index_url: str = None

    def __init__(self, webvpn: Webvpn) -> None:
        self.__user_config: dict = webvpn.get_user_config()
        self.__requests_session: tools.Session = webvpn.get_requests_session()
        self.__logged_in: bool = False
        self.__student_id: str = None
        self.__biz_type_id: str = None
        self.__semester_id: str = None
        self.__semester_list: list = None
        self.__lesson_ids: list = None
        self.__exam_arrange: dict = None

        # generate jxgl url
        while webvpn.portals is None:
            webvpn.get_portals()
        for data in webvpn.portals:
            for res in data.get('resource'):
                if res.get('name') == '教务系统学生端' and res.get('detail') == 'jxglstu.hfut.edu.cn':
                    self.index_url = f'{webvpn.index_url}{res.get("redirect")}'.removesuffix('login')

    def check_login_status(self) -> None:
        while not self.__logged_in:
            tools.print_log('JxglWebvpn -> Not logged in')
            if not self.login():
                tools.rand_sleep()

    def login(self) -> bool:
        salt = self.__requests_session.get(f'{self.index_url}login-salt').text
        self.__requests_session.headers.update({'Content-Type': 'application/json;charset=UTF-8'})
        tools.print_log('JxglWebvpn.login -> Try to login jxgl ...')
        login_response = self.__requests_session.post(f'{self.index_url}login',
                                                      json={
                                                          'username': self.__user_config.get('username'),
                                                          'password':
                                                          tools.sha1_calc(f'{salt}-{self.__user_config.get("password")}'),
                                                          'captcha': ''
                                                      })
        self.__requests_session.headers.pop('Content-Type')
        login_result = tools.load_json(login_response.text)
        if not login_result.get('result'):
            tools.print_log('JxglWebvpn.login -> Failed')
            self.__requests_session = tools.generate_session()
            return False
        tools.print_log('JxglWebvpn.login -> Succeed')
        self.__logged_in = True
        id_response = self.__requests_session.get(f'{self.index_url}for-std/course-table')
        self.__student_id = id_response.request.url.split('/')[-1]
        self.__biz_type_id = re_search(r'bizTypeId: (\d+)', id_response.text).group(1)
        self.__semester_id = re_search(r'<option selected="selected" value="(\d+)">', id_response.text).group(1)
        semester_html_text = re_search(r'<select[^>]*?id="allSemesters"[^>]*?>\s*(.*?)\s*</select>', id_response.text,
                                       RE_DOTALL).group(1)
        self.__semester_list = [{
            'id': semester_option.group(1),
            'name': semester_option.group(2)
        } for semester_option in re_finditer(r'<option[^>]*?value="(\d+)"[^>]*>\s*(.*?)\s*</option>', semester_html_text)]
        return True

    def get_semester_list(self) -> list:
        self.check_login_status()
        return self.__semester_list

    def get_course_data(self, semester_id: str = None) -> dict:
        self.check_login_status()
        course_data_response = self.__requests_session.get(f'{self.index_url}for-std/course-table/get-data',
                                                           params={
                                                               'bizTypeId': self.__biz_type_id,
                                                               'semesterId': semester_id if semester_id else self.__semester_id,
                                                               'dataId': self.__student_id
                                                           })
        course_data = tools.load_json(course_data_response.text)
        self.__lesson_ids = course_data.get('lessonIds')
        return course_data

    def get_schedule_data(self, lesson_ids: list = None, week_index: int = 0) -> dict:
        self.check_login_status()
        post_parms = {
            'lessonIds': lesson_ids if lesson_ids else self.__lesson_ids,
            'studentId': self.__student_id,
            'weekIndex': f'{week_index}' if week_index else ''
        }
        self.__requests_session.headers.update({'Content-Type': 'application/json;charset=UTF-8'})
        schedule_response = self.__requests_session.post(f'{self.index_url}ws/schedule-table/datum', json=post_parms)
        self.__requests_session.headers.pop('Content-Type')
        return tools.load_json(schedule_response.text).get('result')

    def get_exam_arrange(self) -> dict:
        self.check_login_status()
        exam_arrange_response = self.__requests_session.get(f'{self.index_url}for-std/exam-arrange/info/{self.__student_id}')
        exam_arrange_soup: BeautifulSoup = BeautifulSoup(exam_arrange_response.text).find(name='table', attrs={'id': 'exams'})
        self.__exam_arrange = {}
        if exam_arrange_soup:
            self.__exam_arrange.update({'titles': [], 'data': []})
            table_head: BeautifulSoup = exam_arrange_soup.find('thead')
            for title_row in table_head.find_all('tr'):
                self.__exam_arrange.get('titles').append([title_block.get_text('\n') for title_block in title_row.find_all('th')])
            table_body: BeautifulSoup = exam_arrange_soup.find('tbody')
            for data_row in table_body.find_all('tr'):
                self.__exam_arrange.get('data').append([data_block.get_text('\n') for data_block in data_row.find_all('td')])
        return self.__exam_arrange

    def get_score_data(self, semester_id: str = '') -> list:
        self.check_login_status()
        score_data_response = self.__requests_session.get(f'{self.index_url}for-std/grade/sheet/info/{self.__student_id}',
                                                          params={'semester': semester_id})
        score_soups = BeautifulSoup(score_data_response.text).find_all(name='div', attrs={'class': 'row'})
        score_data = []
        for semester in score_soups:
            score = {'semester': semester.find('h3').get_text('\n'), 'titles': [], 'score': []}
            for title_row in semester.find('thead').find_all('tr'):
                score.get('titles').append([title_block.get_text('\n') for title_block in title_row.find_all('th')])
            for score_row in semester.find('tbody').find_all('tr'):
                score.get('score').append([score_block.get_text('\n') for score_block in score_row.find_all('td')])
            score_data.append(score)
        return score_data

    def get_course_select_data(self) -> dict:
        '''TODO: Fix 选课学生和登录用户不符'''
        pass

    def get_lesson_survy_data(self, semester_id: str = None) -> dict:
        self.check_login_status()
        lesson_survy_response = self.__requests_session.get(
            f'{self.index_url}for-std/lesson-survey/{semester_id if semester_id else self.__semester_id}/search/{self.__student_id}'
        )
        return tools.load_json(lesson_survy_response.text)

    def search_lesson(self, semester_id: str = None, custom_params: dict = {}) -> list:
        self.check_login_status()
        self.__requests_session.headers.update({'Referer': f'{self.index_url}for-std/lesson-search/index/{self.__student_id}'})
        search_params = {
            'courseCodeLike': '',
            'courseNameZhLike': '',
            'codeLike': '',
            'nameZhLike': '',
            'courseTypeAssoc': '',
            'examModeAssoc': '',
            'campusAssoc': '',
            'teachLangAssoc': '',
            'requiredPeriodInfo.totalGte': '',
            'requiredPeriodInfo.totalLte': '',
            'requiredPeriodInfo.weeksGte': '',
            'requiredPeriodInfo.weeksLte': '',
            'requiredPeriodInfo.periodsPerWeekGte': '',
            'requiredPeriodInfo.periodsPerWeekLte': '',
            'roomTypeAssoc': '',
            'limitCountGte': '',
            'limitCountLte': '',
            'queryPage__': '1,20',
            '_': tools.current_timestamp()
        }
        search_params.update(custom_params)
        page_number, page_size = [int(i) for i in search_params.get('queryPage__').split(',')]
        tools.print_log(f'JxglWebvpn.search_lesson -> Processing page {page_number}')
        search_url = f'{self.index_url}for-std/lesson-search/semester/{semester_id if semester_id else self.__semester_id}/search/{self.__student_id}'
        search_response = self.__requests_session.get(search_url, params=search_params)
        self.__requests_session.headers.pop('Referer')
        page_number += 1
        response_data: dict = tools.load_json(search_response.text)
        lesson_data: list = response_data.get('data')
        page_count = response_data.get('_page_').get('totalPages')
        while page_number <= page_count:
            tools.rand_sleep()
            tools.print_log(f'JxglWebvpn.search_lesson -> Processing page {page_number}')
            search_params.update({'queryPage__': f'{page_number},{page_size}', '_': tools.current_timestamp()})
            search_response = self.__requests_session.get(search_url, params=search_params)
            lesson_data.extend(tools.load_json(search_response.text).get('data'))
            page_number += 1
        return lesson_data