from django.urls import path, include
from django.contrib import admin
from . import views
from . import consumers

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),

    # Basic pages
    path('', views.landing_page, name='landing'),
    path('login/', views.auth_page, name='login'),
    path('register/', views.register_voter, name='register'),
    path('contact/', views.contact_page, name='contact'),
    path('results/', views.results_page, name='results'),

    # Authentication
    path('login_user/', views.login_user, name='login_user'),
    path('admin-login/', views.admin_login_page, name='admin_login'),
    path('admin-auth/', views.admin_auth, name='admin_auth'),
    path('logout/', views.logout_user, name='logout'),

    # Dashboards
    path('voter/', views.voter_dashboard, name='voter_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Voter management APIs
    path('api/approve-voter/', views.approve_voter, name='approve_voter'),
    path('api/reject-voter/', views.reject_voter, name='reject_voter'),
    path('api/reconsider-voter/', views.reconsider_voter, name='reconsider_voter'), # New API

    # Election management APIs
    path('api/create-election/', views.create_election, name='create_election'),
    path('api/add-candidate/', views.add_candidate, name='add_candidate'),
    path('api/cast-vote/', views.cast_vote, name='cast_vote'),
    path('api/start-election/', views.start_election, name='start_election'), # New API
    path('api/end-election/', views.end_election, name='end_election'), # New API

    # Real-time monitoring APIs
    path('api/election-status/<uuid:election_id>/', views.get_election_status, name='election_status'),
    path('api/vote-status/<uuid:vote_id>/', views.get_vote_status, name='vote_status'),
    path('api/candidates/<uuid:election_id>/', views.get_candidates, name='get_candidates'), # New API
]

websocket_urlpatterns = [
    path('ws/election/<uuid:election_id>/', consumers.ElectionConsumer.as_asgi(), name='ws_election'),
    path('ws/vote/<uuid:vote_id>/', consumers.VoteConsumer.as_asgi(), name='ws_vote'),
    path('ws/admin/', consumers.AdminConsumer.as_asgi(), name='ws_admin'),
    path('ws/voter/', consumers.VoterConsumer.as_asgi(), name='ws_voter'),  # Add this line
]