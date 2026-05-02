from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import signup_view, login_view, logout_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('evaluate/', views.evaluate, name='evaluate'),
    path("result/", views.result, name="result"),
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('report/<int:record_id>/',views.evaluation_report,name='evaluation_report'),
    path('download-report/', views.download_report, name='download_report'),

    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),

    path("toggle-user/<int:user_id>/", views.toggle_user_status, name="toggle_user"),
    path("delete-user/<int:user_id>/", views.delete_user, name="delete_user"),
    
    
 
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)