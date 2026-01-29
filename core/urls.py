from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('problems/', views.problems, name='problems'),
    path('problem/<int:id>/', views.solve_problem, name='solve_problem'),
    path('contests/', views.contests, name='contests'),
    path('contest/<int:id>/', views.contest_overview, name='contest_overview'),
    path('forum/', views.forum, name='forum'),
    path('profile/', views.profile, name='profile'),
    path('stats/', views.stats, name='stats'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/add-problem/', views.add_problem, name='add_problem'),
    path('admin/add-contest/', views.add_contest, name='add_contest'),
    path('problem/<int:id>/submit/', views.submit_solution, name='submit_solution'),
    path('run/code/', views.run_code, name='run_code'), # This name matches {% url 'run_code' %}
]