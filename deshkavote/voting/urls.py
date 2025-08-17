from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing'),
    path('login/', views.auth_page, name='login'),
    path('register/', views.register_voter, name='register'),
    path('login_user/', views.login_user, name='login_user'),
    path('admin-login/', views.admin_login_page, name='admin_login'),
    path('admin-auth/', views.admin_auth, name='admin_auth'),
    path('voter/', views.voter_dashboard, name='voter_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('results/', views.results_page, name='results'),
    path('contact/', views.contact_page, name='contact'),
    path('logout/', views.logout_user, name='logout'),
    # New approval endpoints
    path('api/approve-voter/', views.approve_voter, name='approve_voter'),
    path('api/reject-voter/', views.reject_voter, name='reject_voter'),
]