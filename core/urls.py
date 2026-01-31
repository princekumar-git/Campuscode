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

    # =====================
    # Forum URLs
    # =====================
    path('forum/', views.forum, name='forum'),
    path('forum/create/', views.create_thread, name='create_thread'),
    path('forum/thread/<int:thread_id>/', views.forum_thread_detail, name='forum_thread_detail'),

    path('profile/', views.profile, name='profile'),
    path('profile/delete/', views.delete_account, name='delete_account'),
    path('stats/', views.stats, name='stats'),

    path('forum/thread/<int:thread_id>/reply/', views.add_reply, name='add_reply'),
    path('forum/reply/<int:reply_id>/upvote/', views.upvote_reply, name='upvote_reply'),

    # =====================
    # Admin
    # =====================
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/add-problem/', views.add_problem, name='add_problem'),
    path('admin/add-contest/', views.add_contest, name='add_contest'),

    # =====================
    # Code Execution
    # =====================
    path('problem/<int:id>/submit/', views.submit_solution, name='submit_solution'),
    path('run/code/', views.run_code, name='run_code'),
]
