from django.contrib.auth.decorators import user_passes_test

def facilitator_required(view_func):
    return user_passes_test(lambda u: u.is_staff and u.profile.user_type == 'facilitator')(view_func)

def student_required(view_func):
    return user_passes_test(lambda u: u.profile.user_type == 'student')(view_func)