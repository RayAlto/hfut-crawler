from . import tools


class JxglMobile:

    index_url: str = None

    def __init__(self) -> None:
        self.__user_config: dict = tools.load_config()
        self.__requests_session: tools.Session = tools.generate_session(mobile=True)
        self.__logged_in: bool = False
        self.__user_info: dict = None
        self.__user_key: str = None
        self.__project_id: str = None
        self.__semester_code: str = None
        self.__week_index: int = None
        self.__semester_list: list = None

    def check_login_status(self) -> None:
        while not self.__logged_in:
            tools.print_log('JxglMobile -> Not logged in')
            if not self.login():
                tools.rand_sleep()

    def login(self) -> bool:
        tools.print_log('JxglMobile.login -> Try to login jxgl mobile ...')
        login_response = self.__requests_session.post(f'{self.index_url}appLogin/login.action',
                                                      data={
                                                          'password': tools.base64_calc(self.__user_config.get('password')),
                                                          'username': self.__user_config.get('username'),
                                                          'identity': 0
                                                      })
        login_data: dict = tools.load_json(login_response.text)
        if login_data.get('error'):
            tools.print_log(f'JxglMobile.login -> Failed, {login_data.get("error")}')
            return False
        tools.print_log('JxglMobile.login -> Succeed')
        self.__logged_in = True
        self.__user_info = login_data.get('obj').get('business_data')
        self.__user_key = login_data.get('obj').get('userKey')
        project_data_response = self.__requests_session.post(f'{self.index_url}publicdata/getProjectInfo.action',
                                                             data={
                                                                 'userKey': self.__user_key,
                                                                 'identity': '0'
                                                             })
        project_data: dict = tools.load_json(project_data_response.text).get('obj').get('business_data')[0]
        self.__project_id = project_data.get('id')
        semester_week_response = self.__requests_session.post(f'{self.index_url}publicdata/getSemesterAndWeekList.action',
                                                              data={
                                                                  'projectId': self.__project_id,
                                                                  'userKey': self.__user_key
                                                              })
        semester_week_data: dict = tools.load_json(semester_week_response.text)
        self.__semester_code = semester_week_data['obj']['business_data']['cur_semester_code']
        self.__week_index = semester_week_data['obj']['business_data']['cur_week_index']
        self.__semester_list = semester_week_data['obj']['business_data']['semesters']
        tools.print_log(f'JxglMobile.login -> project name: {project_data.get("name")}')
        return True

    def get_user_info(self) -> dict:
        self.check_login_status()
        return self.__user_info

    def get_semester_list(self) -> list:
        self.check_login_status()
        return self.__semester_list

    def get_week_schedule(self, week_index: int = None, semester_code: str = None) -> list:
        self.check_login_status()
        week_schedule_response = self.__requests_session.post(f'{self.index_url}schedule/getWeekSchedule.action',
                                                              data={
                                                                  'userKey': self.__user_key,
                                                                  'identity': '0',
                                                                  'projectId': self.__project_id,
                                                                  'semestercode':
                                                                  semester_code if semester_code else self.__semester_code,
                                                                  'weekIndex': week_index if week_index else self.__week_index
                                                              })
        week_schedule_data: dict = tools.load_json(week_schedule_response.text)
        return week_schedule_data['obj']['business_data']

    def get_classmates(self, lesson_code: str, semester_code: str = None) -> list:
        self.check_login_status()
        classmates_response = self.__requests_session.post(f'{self.index_url}schedule/getClassList.action',
                                                           data={
                                                               'lessonCode': lesson_code,
                                                               'projectId': self.__project_id,
                                                               'semestercode':
                                                               semester_code if semester_code else self.__semester_code,
                                                               'userKey': self.__user_key
                                                           })
        classmates_data = tools.load_json(classmates_response.text)
        return classmates_data['obj']['business_data']