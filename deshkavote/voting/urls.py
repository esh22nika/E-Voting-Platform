from django.urls import path
from . import views
from . import consumers

# app_name = 'voting'  # Optional: but good practice

urlpatterns = [
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
    path('api/reconsider-voter/', views.reconsider_voter, name='reconsider_voter'),
    path('api/voter-details/<int:voter_id>/', views.get_voter_details, name='get_voter_details'),
    path('api/download-voters-list/', views.download_voters_list, name='download_voters_list'),


    # Election management APIs
    path('api/create-election/', views.create_election, name='create_election'),
    path('api/add-candidate/', views.add_candidate, name='add_candidate'),
    path('api/cast-vote/', views.cast_vote, name='cast_vote'),
    path('api/start-election/', views.start_election, name='start_election'),
    path('api/end-election/', views.end_election, name='end_election'),
    path('api/verify-candidate/', views.verify_candidate, name='verify_candidate'),


    # Real-time monitoring & stats APIs
    path('api/admin-stats/', views.admin_stats, name='admin_stats'),
    path('api/election-statistics/', views.get_election_statistics, name='election_statistics'),
    path('api/election-results/<uuid:election_id>/', views.get_election_results, name='get_election_results'),
    path('api/election-details/<uuid:election_id>/', views.get_election_details, name='get_election_details'),
    path('api/candidate-details/<uuid:candidate_id>/', views.get_candidate_details, name='get_candidate_details'),
    path('api/finalize-election-results/<uuid:election_id>/', views.finalize_election_results, name='finalize_election_results'),

    path('api/vote-queue-status/', views.get_vote_queue_status, name='get_vote_queue_status'),
    path('api/node-performance/', views.get_node_performance, name='get_node_performance'),
    path('api/consensus-status/', views.get_consensus_status, name='get_consensus_status'),
    
    path('api/audit-logs/', views.get_audit_logs, name='get_audit_logs'),
    path('api/export-audit-logs/', views.export_audit_logs, name='export_audit_logs'),

    path('api/election-status/<uuid:election_id>/', views.get_election_status, name='election_status'),
    path('api/vote-status/<uuid:vote_id>/', views.get_vote_status, name='vote_status'),
    path('api/candidates/<uuid:election_id>/', views.get_candidates, name='get_candidates'),
]

websocket_urlpatterns = [
    path('ws/election/<uuid:election_id>/', consumers.ElectionConsumer.as_asgi(), name='ws_election'),
    path('ws/vote/<uuid:vote_id>/', consumers.VoteConsumer.as_asgi(), name='ws_vote'),
    path('ws/admin/', consumers.AdminConsumer.as_asgi(), name='ws_admin'),
    path('ws/voter/', consumers.VoterConsumer.as_asgi(), name='ws_voter'),
]