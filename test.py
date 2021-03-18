import hfut

a=hfut.JxglMobile()
a.login()
print(a.get_user_info())
print(a.get_semester_list())
print(a.get_week_schedule())
print(a.get_classmates('0100005X--001'))