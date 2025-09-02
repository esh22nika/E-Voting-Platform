# Clean version of views.py with proper imports and function order

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, models
from django.db.models import Count
from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta
import json
import logging
import hashlib
import time,random
import asyncio
from decimal import Decimal
import uuid
import csv

# Import Django Channels libraries
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Try to import optional dependencies
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
except ImportError:
    redis_client = None

try:
    from celery import shared_task
except ImportError:
    def shared_task(func):
        return func

from .models import (
    CustomUser, Voter, Election, Candidate, Vote,
    VoteConsensusLog, ElectionNode, AuditLog, VoterSession
)

# Set up logging
logger = logging.getLogger(__name__)

# Add the missing DistributedElectionManager.sync_election_time method
class DistributedElectionManager:
    """Manage distributed election operations"""

    @staticmethod
    def create_consensus_round(vote):
        """Create consensus round for vote verification"""
        nodes = ElectionNode.objects.filter(
            election=vote.election,
            status='active'
        )[:vote.required_confirmations]

        for node in nodes:
            VoteConsensusLog.objects.create(
                vote=vote,
                node_id=node.node_id,
                consensus_round=1,
                status='pending',
                signature=f"sig_{vote.vote_hash}_{node.node_id}"
            )

        return nodes.count()

    @staticmethod
    def achieve_consensus(vote_id):
        """Check if consensus is achieved for a vote"""
        vote = Vote.objects.get(id=vote_id)
        confirmed_logs = VoteConsensusLog.objects.filter(
            vote=vote,
            status='confirmed'
        ).count()

        if confirmed_logs >= vote.required_confirmations:
            vote.status = 'finalized'
            vote.confirmation_count = confirmed_logs
            vote.save()
            return True
        return False

    @staticmethod
    def sync_election_time(election):
        """Synchronize election timing across nodes using NTP"""
        try:
            # In a real implementation, this would sync with NTP servers
            # For demo purposes, we'll use current time with small adjustments
            current_time = timezone.now()

            # Cache synchronized time for all nodes
            cache_key = f"election_sync_{election.id}"
            sync_data = {
                'start_time': election.start_date.isoformat(),
                'end_time': election.end_date.isoformat(),
                'sync_timestamp': current_time.isoformat(),
                'ntp_server': election.ntp_server
            }

            cache.set(cache_key, sync_data, timeout=3600)  # Cache for 1 hour

            election.synchronized_start_time = election.start_date
            election.synchronized_end_time = election.end_date
            election.save()

            return True
        except Exception as e:
            logger.error(f"Time synchronization failed for election {election.id}: {e}")
            return False

def create_audit_log(log_type, user=None, election=None, details=None, request=None):
    """Create audit log entry with hash chain"""
    # Get previous hash for chain integrity
    last_log = AuditLog.objects.order_by('-timestamp').first()
    previous_hash = last_log.hash_chain if last_log else ""

    # Extract request details
    ip_address = None
    user_agent = ""
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

    log_entry = AuditLog.objects.create(
        log_type=log_type,
        user=user,
        election=election,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        previous_hash=previous_hash
    )

    return log_entry

# Celery tasks
@shared_task
def process_vote_consensus(vote_id):
    """Background task to process vote consensus"""
    try:
        vote = Vote.objects.get(id=vote_id)
        time.sleep(2)  # Simulate processing time

        # Create consensus logs
        node_count = DistributedElectionManager.create_consensus_round(vote)

        # Simulate consensus achievement
        if node_count >= vote.required_confirmations:
            # Update consensus logs to confirmed
            VoteConsensusLog.objects.filter(vote=vote).update(status='confirmed')
            DistributedElectionManager.achieve_consensus(vote_id)
            cache.delete(f"vote_status_{vote_id}")
            
            # Notify via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"vote_{vote_id}",
                {
                    "type": "send_vote_update",
                    "data": {"status": "finalized", "message": "Your vote has been verified."}
                }
            )

        return f"Consensus achieved for vote {vote_id}"

    except Exception as e:
        logger.error(f"Error in vote consensus processing: {e}")
        return f"Error processing vote consensus: {e}"

# View functions
def landing_page(request):
    """Enhanced landing page with real-time election stats"""
    stats = cache.get('election_stats')
    if not stats:
        stats = {
            'total_elections': Election.objects.count(),
            'active_elections': Election.objects.filter(status='active').count(),
            'total_voters': Voter.objects.filter(approval_status='approved').count(),
            'total_votes': Vote.objects.filter(status='finalized').count(),
        }
        cache.set('election_stats', stats, timeout=300)

    return render(request, 'landing_page.html', {'stats': stats})

def auth_page(request):
    """Login/Register page view"""
    return render(request, 'auth.html')

@csrf_exempt
def register_voter(request):
    """Enhanced voter registration with security features"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Handle both FormData and JSON
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                else:
                    data = {
                        'firstName': request.POST.get('firstName'),
                        'lastName': request.POST.get('lastName'),
                        'email': request.POST.get('email'),
                        'mobile': request.POST.get('mobile'),
                        'dob': request.POST.get('dob'),
                        'gender': request.POST.get('gender'),
                        'parentSpouseName': request.POST.get('parentSpouseName'),
                        'streetAddress': request.POST.get('streetAddress'),
                        'city': request.POST.get('city'),
                        'state': request.POST.get('state'),
                        'pincode': request.POST.get('pincode'),
                        'placeOfBirth': request.POST.get('placeOfBirth'),
                        'voterId': request.POST.get('voterId'),
                        'aadharNumber': request.POST.get('aadharNumber'),
                        'panNumber': request.POST.get('panNumber'),
                        'password': request.POST.get('password'),
                        'constituency': request.POST.get('constituency', ''),
                        'district': request.POST.get('district', ''),
                    }

                # Enhanced validation
                if Voter.objects.filter(voter_id=data['voterId']).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Voter ID already exists'
                    })

                if CustomUser.objects.filter(username=data['voterId']).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'User already exists'
                    })

                # Validate age (must be 18+)
                dob = datetime.strptime(data['dob'], '%Y-%m-%d').date()
                today = timezone.now().date()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                if age < 18:
                    return JsonResponse({
                        'success': False,
                        'message': 'You must be 18 years or older to register'
                    })

                # Create user
                user = CustomUser.objects.create_user(
                    username=data['voterId'],
                    password=data['password'],
                    role='voter',
                    is_active=False,
                    mobile=data['mobile']
                )

                # Create voter profile
                voter = Voter.objects.create(
                    user=user,
                    first_name=data['firstName'],
                    last_name=data['lastName'],
                    email=data['email'],
                    mobile=data['mobile'],
                    date_of_birth=dob,
                    gender=data['gender'],
                    parent_spouse_name=data['parentSpouseName'],
                    street_address=data['streetAddress'],
                    city=data['city'],
                    state=data['state'],
                    pincode=data['pincode'],
                    place_of_birth=data['placeOfBirth'],
                    voter_id=data['voterId'],
                    aadhar_number=data['aadharNumber'],
                    pan_number=data['panNumber'],
                    constituency=data.get('constituency', ''),
                    district=data.get('district', ''),
                    approval_status='pending'
                )

                # Create audit log
                create_audit_log(
                    'voter_registration',
                    user=user,
                    details={'voter_id': data['voterId'], 'city': data['city'], 'state': data['state']},
                    request=request
                )
                
                # Notify admin via websockets
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard", {
                        "type": "send_admin_update",
                        "data": {
                            "type": "new_registration",
                            "message": f"New voter registration: {voter.full_name}"
                        }
                    }
                )

                cache.delete('election_stats')

                return JsonResponse({
                    'success': True,
                    'message': 'Registration successful! Your account is pending approval. You will be notified once approved.'
                })

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Registration failed: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
def login_user(request):
    """Enhanced voter login with security features"""
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                voter_id = data.get('voterId')
                password = data.get('password')
            else:
                voter_id = (request.POST.get('voter_id') or
                           request.POST.get('voterId') or
                           request.POST.get('username'))
                password = request.POST.get('password')

            logger.info(f"Login attempt for voter ID: {voter_id}")

            if not voter_id or not password:
                return JsonResponse({
                    'success': False,
                    'message': 'Voter ID and password are required'
                })

            try:
                user = CustomUser.objects.get(username=voter_id)
                
                # Lockout mechanism
                if user.is_locked and user.lock_time and timezone.now() < user.lock_time + timedelta(minutes=15):
                     return JsonResponse({
                        'success': False,
                        'message': 'Account is temporarily locked. Please try again later.'
                    })

                if user.check_password(password) and user.role == 'voter':
                    user.failed_login_attempts = 0
                    user.is_locked = False
                    user.last_login_ip = request.META.get('REMOTE_ADDR')
                    user.save()

                    try:
                        voter = Voter.objects.get(user=user)
                        if voter.approval_status == 'pending':
                            return JsonResponse({
                                'success': False,
                                'message': 'Your account is pending approval. Please wait for admin approval.',
                                'pending_approval': True
                            })
                        elif voter.approval_status == 'rejected':
                            return JsonResponse({
                                'success': False,
                                'message': f'Your account has been rejected. Reason: {voter.rejection_reason or "Contact admin for details"}'
                            })
                        elif voter.approval_status == 'approved' and user.is_active:
                            login(request, user)

                            # Create voter session
                            if not request.session.session_key:
                                request.session.create()
                            
                            session_key = request.session.session_key
                            device_fingerprint = hashlib.md5(request.META.get('HTTP_USER_AGENT', '').encode()).hexdigest()
                            
                            VoterSession.objects.create(
                                voter=voter,
                                session_key=session_key,
                                ip_address=user.last_login_ip,
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                device_fingerprint=device_fingerprint
                            )

                            create_audit_log(
                                'voter_login',
                                user=user,
                                details={'voter_id': voter_id, 'session_id': VoterSession.objects.latest('created_at').id},
                                request=request
                            )

                            logger.info(f"Successful login for voter: {voter_id}")
                            return JsonResponse({
                                'success': True,
                                'message': 'Login successful',
                                'redirect_url': '/voter/'
                            })
                        else:
                            return JsonResponse({
                                'success': False,
                                'message': 'Account not activated. Please contact admin.'
                            })
                    except Voter.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'message': 'Voter profile not found'
                        })
                else:
                    user.failed_login_attempts += 1
                    if user.failed_login_attempts >= 5:
                        user.is_locked = True
                        user.lock_time = timezone.now()
                    user.save()
                    
                    logger.warning(f"Invalid credentials for voter: {voter_id}")
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid Voter ID or password'
                    })
            except CustomUser.DoesNotExist:
                logger.warning(f"User not found: {voter_id}")
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid Voter ID or password'
                })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Login failed: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
def admin_login_page(request):
    """Admin login page view"""
    return render(request, 'admin_login.html')

@csrf_exempt
def admin_auth(request):
    """Enhanced admin authentication"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None and (user.is_staff or user.role == 'admin'):
                login(request, user)
                
                # Log the admin login
                create_audit_log(
                    'admin_action',
                    user=user,
                    details={'action': 'admin_login', 'admin_username': username},
                    request=request
                )
                
                logger.info(f"Admin '{username}' logged in.")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Admin login successful',
                    'redirect_url': '/admin-dashboard/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid admin credentials'
                })

        except Exception as e:
            logger.error(f"Admin login failed: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Login failed: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def voter_dashboard(request):
    """Enhanced voter dashboard with eligible elections"""
    if request.user.role != 'voter':
        return redirect('landing')

    try:
        voter = Voter.objects.get(user=request.user)

        if voter.approval_status != 'approved':
            context = {
                'voter': voter,
                'approval_status': voter.approval_status,
                'rejection_reason': voter.rejection_reason if voter.approval_status == 'rejected' else None
            }
            return render(request, 'voter.html', context)

        # Get eligible elections
        cache_key = f"voter_elections_{voter.id}"
        elections_data = cache.get(cache_key)
        
        if not elections_data:
            eligible_elections = voter.get_eligible_elections()
            voted_elections = Vote.objects.filter(voter=voter).values_list('election_id', flat=True)

            elections_data = []
            for election in eligible_elections:
                candidates = Candidate.objects.filter(election=election, is_verified=True)
                has_voted = election.id in voted_elections

                elections_data.append({
                    'election': election,
                    'candidates': candidates,
                    'has_voted': has_voted,
                    'is_active': election.status == 'active' and not has_voted
                })
            
            cache.set(cache_key, elections_data, timeout=600)

        context = {
            'voter': voter,
            'elections_data': elections_data,
            'approval_status': 'approved'
        }
        return render(request, 'voter.html', context)

    except Voter.DoesNotExist:
        messages.error(request, 'Voter profile not found')
        return redirect('landing')

@login_required
def admin_dashboard(request):
    """Enhanced admin dashboard with comprehensive voter management"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return redirect('landing')

    pending_voters = Voter.objects.filter(approval_status='pending').order_by('-created_at')
    approved_voters = Voter.objects.filter(approval_status='approved').order_by('-approval_date')
    rejected_voters = Voter.objects.filter(approval_status='rejected').order_by('-updated_at')
    elections = Election.objects.all().order_by('-created_at')
    candidates = Candidate.objects.all().order_by('-created_at')
    
    # Calculate vote counts and leading candidate for each election
    for election in elections:
        if election.status in ['active', 'completed']:
            vote_counts = Vote.objects.filter(
                election=election,
                status='finalized'  # Important: Only count verified votes
            ).values(
                'candidate__name', 
                'candidate__party'
            ).annotate(
                vote_count=Count('id')
            ).order_by('-vote_count')

            if vote_counts:
                leading_candidate_data = vote_counts[0]
                election.leading_candidate = {
                    'name': leading_candidate_data['candidate__name'],
                    'party': leading_candidate_data['candidate__party']
                }
                election.leading_votes = leading_candidate_data['vote_count']
            else:
                election.leading_candidate = None
                election.leading_votes = 0

    stats = {
        'pending_count': pending_voters.count(),
        'approved_count': approved_voters.count(),
        'rejected_count': rejected_voters.count(),
        'total_elections': elections.count(),
        'active_elections': elections.filter(status='active').count(),
        'total_candidates': candidates.count(),
        'active_nodes': ElectionNode.objects.filter(status='active').count(),
        'total_nodes': ElectionNode.objects.count(),
        'system_health': 99.8, # Placeholder
    }

    context = {
        'admin_username': request.user.username,
        'is_superuser': request.user.is_superuser,
        'django_admin_url': '/admin/',
        'pending_voters': pending_voters,
        'approved_voters': approved_voters,
        'rejected_voters': rejected_voters,
        'elections': elections,
        'candidates': candidates,
        'stats': stats,
    }
    return render(request, 'admin.html', context)

@require_GET
def get_candidates(request, election_id):
    """Return candidates for a given election."""
    try:
        election = Election.objects.get(id=election_id)
        candidates = Candidate.objects.filter(election=election)
        data = [
            {
                'id': str(candidate.id),
                'name': candidate.name,
                'party': candidate.party,
                'constituency': candidate.constituency,
                'symbol': candidate.symbol,
                'is_verified': candidate.is_verified,
            }
            for candidate in candidates
        ]
        return JsonResponse({'success': True, 'candidates': data})
    except Election.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Election not found'})
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

@csrf_exempt
@login_required
def cast_vote(request):
    """Enhanced vote casting with distributed consensus"""
    if request.user.role != 'voter':
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                logger.info(f"Vote casting attempt by {request.user.username}: {data}")

                voter = get_object_or_404(Voter, user=request.user)
                candidate = get_object_or_404(Candidate, id=data['candidate_id'])
                election = candidate.election

                # Validate voting eligibility
                if election.status != 'active':
                    return JsonResponse({
                        'success': False,
                        'message': 'Election is not currently active'
                    })
                
                eligible_elections_ids = [e.id for e in voter.get_eligible_elections()]
                if election.id not in eligible_elections_ids:
                    return JsonResponse({
                        'success': False,
                        'message': 'You are not eligible to vote in this election'
                    })

                # Check if voter has already voted
                if Vote.objects.filter(voter=voter, election=election).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'You have already voted in this election'
                    })

                # Create vote
                vote = Vote.objects.create(
                    voter=voter,
                    candidate=candidate,
                    election=election,
                    status='pending',
                    required_confirmations=3
                )

                logger.info(f"Vote created: {vote.id}")

                # Start consensus process
                process_vote_consensus.delay(str(vote.id))

                # Create audit log
                create_audit_log(
                    'vote_cast',
                    user=request.user,
                    election=election,
                    details={
                        'voter_id': voter.voter_id,
                        'candidate_name': candidate.name,
                        'vote_hash': vote.vote_hash
                    },
                    request=request
                )

                cache.delete(f"voter_elections_{voter.id}")
                cache.delete('election_stats')
                
                # Notify admin dashboard via websockets
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard", {
                        "type": "send_admin_update",
                        "data": {
                            "type": "new_vote",
                            "message": f"New vote cast in {election.name}"
                        }
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': 'Vote cast successfully! Your vote is being verified through our distributed consensus system.',
                    'vote_id': str(vote.id)
                })

        except Exception as e:
            logger.error(f"Error casting vote: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error casting vote: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# --- NEW API VIEWS START HERE ---

@require_GET
@login_required
def admin_stats(request):
    stats = {
        'pending_count': Voter.objects.filter(approval_status='pending').count(),
        'approved_count': Voter.objects.filter(approval_status='approved').count(),
        'rejected_count': Voter.objects.filter(approval_status='rejected').count(),
        'active_elections': Election.objects.filter(status='active').count(),
        'system_health': 99.8,  # Placeholder
        'active_nodes': ElectionNode.objects.filter(status='active').count(),
        'total_nodes': ElectionNode.objects.count(),
    }
    return JsonResponse({'success': True, 'stats': stats})

@require_GET
@login_required
def get_audit_logs(request):
    log_type = request.GET.get('type')
    date = request.GET.get('date')
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    if log_type:
        logs = logs.filter(log_type=log_type)
    if date:
        logs = logs.filter(timestamp__date=date)
        
    data = [{
        'timestamp': log.timestamp,
        'log_type': log.log_type,
        'user': log.user.username if log.user else 'System',
        'details': json.dumps(log.details),
        'ip_address': log.ip_address,
        'hash_chain': log.hash_chain,
    } for log in logs[:100]] # Limit to 100 most recent
    
    return JsonResponse({'success': True, 'logs': data})

@require_GET
@login_required
def export_audit_logs(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Type', 'User', 'Details', 'IP Address', 'Hash'])
    
    logs = AuditLog.objects.all().order_by('-timestamp')
    for log in logs:
        writer.writerow([
            log.timestamp,
            log.log_type,
            log.user.username if log.user else 'System',
            json.dumps(log.details),
            log.ip_address,
            log.hash_chain
        ])
        
    return response

@require_GET
@login_required
def get_election_statistics(request):
    stats = {
        'active': Election.objects.filter(status='active').count(),
        'upcoming': Election.objects.filter(status='upcoming').count(),
        'completed': Election.objects.filter(status='completed').count(),
    }
    return JsonResponse({'success': True, 'stats': stats})

@require_GET
@login_required
def get_voter_details(request, voter_id):
    voter = get_object_or_404(Voter, id=voter_id)
    data = {
        'voter_id': voter.voter_id,
        'full_name': voter.full_name,
        'email': voter.email,
        'mobile': voter.mobile,
        'date_of_birth': voter.date_of_birth,
        'gender': voter.gender,
        'street_address': voter.street_address,
        'city': voter.city,
        'state': voter.state,
        'pincode': voter.pincode,
        'approval_status': voter.approval_status,
    }
    return JsonResponse({'success': True, 'voter': data})

@require_GET
@login_required
def get_candidate_details(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    data = {
        'name': candidate.name,
        'party': candidate.party,
        'constituency': candidate.constituency,
        'symbol': candidate.symbol,
        'education': candidate.education,
        'is_verified': candidate.is_verified,
        'election_name': candidate.election.name,
    }
    return JsonResponse({'success': True, 'candidate': data})

@require_GET
@login_required
def get_election_details(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    data = {
        'name': election.name,
        'election_type': election.election_type,
        'state': election.state,
        'status': election.status,
        'start_date': election.start_date,
        'end_date': election.end_date,
        'candidates_count': election.candidates.count(),
        'total_votes': Vote.objects.filter(election=election, status='finalized').count(),
    }
    return JsonResponse({'success': True, 'election': data})

@require_GET
@login_required
def get_election_results(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    vote_counts = Vote.objects.filter(
        election=election,
        status='finalized'
    ).values(
        'candidate__name', 
        'candidate__party'
    ).annotate(
        vote_count=Count('id')
    ).order_by('-vote_count')
    
    return JsonResponse({'success': True, 'results': list(vote_counts)})

@csrf_exempt
@login_required
def finalize_election_results(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    vote_counts = Vote.objects.filter(election=election, status='finalized').values('candidate__name').annotate(vote_count=Count('id')).order_by('-vote_count')
    
    winner = "N/A"
    winning_votes = 0
    if vote_counts:
        winner = vote_counts[0]['candidate__name']
        winning_votes = vote_counts[0]['vote_count']

    return JsonResponse({'success': True, 'winner': winner, 'winning_votes': winning_votes})

@csrf_exempt
@login_required
def verify_candidate(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        candidate = get_object_or_404(Candidate, id=candidate_id)
        candidate.is_verified = True
        candidate.save()
        return JsonResponse({'success': True, 'candidate_name': candidate.name})
    return JsonResponse({'success': False, 'message': 'Invalid request'})
    
@require_GET
@login_required
def download_voters_list(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="voters_list.csv"'

    writer = csv.writer(response)
    writer.writerow(['Voter ID', 'Name', 'Email', 'State', 'City', 'Status'])
    
    voters = Voter.objects.all()
    # Optional filtering can be added here based on GET params
    
    for voter in voters:
        writer.writerow([
            voter.voter_id,
            voter.full_name,
            voter.email,
            voter.state,
            voter.city,
            voter.approval_status
        ])
        
    return response

# Placeholder views for real-time charts, returning random data for now
def get_vote_queue_status(request):
    import random
    return JsonResponse({'success': True, 'queue_size': random.randint(0, 50)})

def get_node_performance(request):
    nodes = [
        {'node_id': 'Node-1', 'response_time': random.randint(50, 150)},
        {'node_id': 'Node-2', 'response_time': random.randint(50, 150)},
        {'node_id': 'Node-3', 'response_time': random.randint(50, 150)},
    ]
    return JsonResponse({'success': True, 'nodes': nodes})

def get_consensus_status(request):
    processes = [
        {'election_name': 'Trial Election', 'consensus_round': 1, 'progress': random.randint(10, 100), 'status': 'active'},
    ]
    return JsonResponse({'success': True, 'processes': processes})
    
# --- END OF NEW API VIEWS ---

@csrf_exempt
@login_required
def approve_voter(request):
    """Enhanced voter approval with audit logging"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                voter_id = data.get('voter_id')

                voter = get_object_or_404(Voter, id=voter_id)

                # Update approval status
                voter.approval_status = 'approved'
                voter.approved_by = request.user
                voter.approval_date = timezone.now()
                voter.save()

                # Activate user account
                voter.user.is_active = True
                voter.user.save()

                # Create audit log
                create_audit_log(
                    'voter_approved',
                    user=request.user,
                    details={
                        'voter_id': voter.voter_id,
                        'approved_voter_name': voter.full_name,
                        'admin_id': request.user.id
                    },
                    request=request
                )

                # Clear relevant caches
                cache.delete('election_stats')
                cache.delete(f"voter_elections_{voter.id}")
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "voter_approval_update", "action": "approved", "voter_id": voter.id, "voter_name": voter.full_name}
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Voter {voter.voter_id} approved successfully'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error approving voter: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def reject_voter(request):
    """Enhanced voter rejection with audit logging"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                voter_id = data.get('voter_id')
                reason = data.get('reason', 'No reason provided')

                voter = get_object_or_404(Voter, id=voter_id)

                # Update approval status
                voter.approval_status = 'rejected'
                voter.rejection_reason = reason
                voter.save()

                # Deactivate user account
                voter.user.is_active = False
                voter.user.save()

                # Create audit log
                create_audit_log(
                    'voter_rejected',
                    user=request.user,
                    details={
                        'voter_id': voter.voter_id,
                        'rejected_voter_name': voter.full_name,
                        'rejection_reason': reason,
                        'admin_id': request.user.id
                    },
                    request=request
                )

                # Clear relevant caches
                cache.delete('election_stats')
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "voter_approval_update", "action": "rejected", "voter_id": voter.id, "voter_name": voter.full_name}
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Voter {voter.voter_id} rejected successfully'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error rejecting voter: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def reconsider_voter(request):
    """Admin action to move a rejected voter back to pending status"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            voter_id = data.get('voter_id')
            voter = get_object_or_404(Voter, id=voter_id)

            if voter.approval_status == 'rejected':
                voter.approval_status = 'pending'
                voter.rejection_reason = None
                voter.save()
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "voter_approval_update", "action": "reconsidered", "voter_id": voter.id, "voter_name": voter.full_name}
                    }
                )
                
                return JsonResponse({'success': True, 'message': f'Voter {voter.voter_id} moved to pending status.'})
            else:
                return JsonResponse({'success': False, 'message': 'Voter is not in a rejected state.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def create_election(request):
    """Create new election with distributed systems support"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                
                # Lamport Clock-like timestamp for event ordering
                lamport_timestamp = time.time() * 1000  # Milliseconds since epoch

                # Validate dates
                start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))

                if start_date >= end_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'End date must be after start date'
                    })

                # Create election
                election = Election.objects.create(
                    name=data['name'],
                    state=data['state'],
                    city=data.get('city', ''),
                    district=data.get('district', ''),
                    election_type=data['election_type'],
                    year=data['year'],
                    start_date=start_date,
                    end_date=end_date,
                    status='upcoming',
                    primary_server=request.META.get('HTTP_HOST'),
                    backup_servers=data.get('backup_servers', []),
                    replication_factor=data.get('replication_factor', 3)
                )

                # Initialize distributed nodes
                for i in range(election.replication_factor):
                    ElectionNode.objects.create(
                        node_id=str(uuid.uuid4()),
                        ip_address=f"192.168.1.{100+i}",  # Example IPs
                        port=8000 + i,
                        election=election
                    )

                # Create audit log
                create_audit_log(
                    'election_created',
                    user=request.user,
                    election=election,
                    details={
                        'election_name': election.name,
                        'election_type': election.election_type,
                        'state': election.state,
                        'lamport_timestamp': lamport_timestamp
                    },
                    request=request
                )
                
                # Notify all users/admins that a new election was created
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "new_election", "message": f"New election created: {election.name}"}
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Election "{election.name}" created successfully',
                    'election_id': str(election.id)
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error creating election: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def add_candidate(request):
    """Add candidate to election"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)

                election = get_object_or_404(Election, id=data['election_id'])

                candidate = Candidate.objects.create(
                    name=data['name'],
                    party=data['party'],
                    constituency=data['constituency'],
                    symbol=data['symbol'],
                    education=data.get('education', ''),
                    manifesto=data.get('manifesto', ''),
                    age=data.get('age'),
                    criminal_cases=data.get('criminal_cases', 0),
                    assets_value=Decimal(str(data.get('assets_value', 0))),
                    election=election,
                    is_verified=True  # Auto-verify admin-added candidates
                )

                # Create audit log
                create_audit_log(
                    'candidate_added',
                    user=request.user,
                    election=election,
                    details={
                        'candidate_name': candidate.name,
                        'party': candidate.party,
                        'constituency': candidate.constituency
                    },
                    request=request
                )
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "new_candidate", "message": f"New candidate '{candidate.name}' added to {election.name}"}
                    }
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Candidate "{candidate.name}" added successfully'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error adding candidate: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def start_election(request):
    """Admin action to start an upcoming election"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            election_id = data.get('election_id')
            election = get_object_or_404(Election, id=election_id)
            
            if election.status == 'upcoming':
                election.status = 'active'
                election.save()
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "election_status_update", "election_id": str(election.id), "status": "active", "message": f"Election '{election.name}' is now active."}
                    }
                )
                
                return JsonResponse({'success': True, 'message': f'Election "{election.name}" started successfully.'})
            else:
                return JsonResponse({'success': False, 'message': 'Election is not in a starting state.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def end_election(request):
    """Admin action to end an active election"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            election_id = data.get('election_id')
            election = get_object_or_404(Election, id=election_id)
            
            if election.status == 'active':
                election.status = 'completed'
                election.save()
                
                # Notify front-end via WebSocket
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "admin_dashboard",
                    {
                        "type": "send_admin_update",
                        "data": {"type": "election_status_update", "election_id": str(election.id), "status": "completed", "message": f"Election '{election.name}' has ended."}
                    }
                )
                
                return JsonResponse({'success': True, 'message': f'Election "{election.name}" ended successfully.'})
            else:
                return JsonResponse({'success': False, 'message': 'Election is not in an active state.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def get_election_status(request, election_id):
    """Get real-time election status"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    try:
        election = get_object_or_404(Election, id=election_id)

        # Get node statuses
        nodes = ElectionNode.objects.filter(election=election)
        node_statuses = [
            {
                'node_id': node.node_id,
                'status': node.status,
                'last_heartbeat': node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                'response_time': node.response_time,
                'uptime_percentage': node.uptime_percentage
            }
            for node in nodes
        ]

        # Get vote statistics
        total_votes = Vote.objects.filter(election=election).count()
        verified_votes = Vote.objects.filter(election=election, status='finalized').count()
        pending_votes = Vote.objects.filter(election=election, status='pending').count()

        data = {
            'election': {
                'id': str(election.id),
                'name': election.name,
                'status': election.status,
                'consensus_status': election.consensus_status,
                'start_date': election.start_date.isoformat(),
                'end_date': election.end_date.isoformat()
            },
            'nodes': node_statuses,
            'votes': {
                'total': total_votes,
                'verified': verified_votes,
                'pending': pending_votes
            }
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def get_vote_status(request, vote_id):
    """Get real-time vote verification status"""
    try:
        vote = get_object_or_404(Vote, id=vote_id)

        # Check if user is authorized to view this vote
        if request.user.role == 'voter' and vote.voter.user != request.user:
            return JsonResponse({'success': False, 'message': 'Unauthorized'})

        if not (request.user.is_staff or request.user.role == 'admin' or vote.voter.user == request.user):
            return JsonResponse({'success': False, 'message': 'Unauthorized'})

        # Get consensus logs
        consensus_logs = VoteConsensusLog.objects.filter(vote=vote).order_by('-timestamp')
        logs_data = [
            {
                'node_id': log.node_id,
                'status': log.status,
                'timestamp': log.timestamp.isoformat(),
                'consensus_round': log.consensus_round
            }
            for log in consensus_logs
        ]

        data = {
            'vote_id': str(vote.id),
            'status': vote.status,
            'confirmation_count': vote.confirmation_count,
            'required_confirmations': vote.required_confirmations,
            'consensus_logs': logs_data,
            'vote_hash': vote.vote_hash,
            'timestamp': vote.timestamp.isoformat()
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@shared_task
def sync_election_across_nodes(election_id):
    """Background task to synchronize election across distributed nodes"""
    try:
        election = Election.objects.get(id=election_id)

        # Sync time across nodes
        DistributedElectionManager.sync_election_time(election)

        # Replicate election data to backup nodes
        for backup_server in election.backup_servers:
            # In real implementation, send data to backup servers
            cache.set(f"election_backup_{backup_server}_{election_id}",
                      election.name, timeout=86400)

        # Notify admins via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "admin_dashboard",
            {
                "type": "send_admin_update",
                "data": {"type": "election_update", "message": f"Election {election_id} synchronized."}
            }
        )

        return f"Election {election_id} synchronized across nodes"

    except Exception as e:
        logger.error(f"Error synchronizing election: {e}")
        return f"Error: {e}"

def results_page(request):
    """Results page"""
    completed_elections = Election.objects.filter(status='completed').order_by('-end_date')
    results_data = []
    
    for election in completed_elections:
        candidates_with_votes = []
        for candidate in election.candidates.all():
            vote_count = Vote.objects.filter(
                candidate=candidate,
                election=election,
                status='finalized'
            ).count()
            candidates_with_votes.append({
                'candidate': candidate,
                'votes': vote_count
            })
        
        candidates_with_votes.sort(key=lambda x: x['votes'], reverse=True)
        total_votes = sum(c['votes'] for c in candidates_with_votes)
        
        results_data.append({
            'election': election,
            'candidates_with_votes': candidates_with_votes,
            'total_votes': total_votes,
            'winner': candidates_with_votes[0] if candidates_with_votes else None
        })
    
    return render(request, 'results.html', {'results_data': results_data})

def contact_page(request):
    """Contact page"""
    return render(request, 'contact.html')

def logout_user(request):
    """Enhanced user logout with session cleanup"""
    if request.user.is_authenticated:
        # Log the logout action
        create_audit_log(
            'user_logout',
            user=request.user,
            details={'user_role': request.user.role},
            request=request
        )

        # Invalidate the voter session if the user is a voter
        if request.user.role == 'voter':
            try:
                voter_session = VoterSession.objects.get(
                    voter__user=request.user,
                    session_key=request.session.session_key,
                    is_active=True
                )
                voter_session.is_active = False
                voter_session.save()
            except VoterSession.DoesNotExist:
                pass  # Session might have already expired or been invalidated
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('landing')