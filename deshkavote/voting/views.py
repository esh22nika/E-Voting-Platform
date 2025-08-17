from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
import json
import logging

from .models import CustomUser, Voter, Election, Candidate, Vote

# Set up logging
logger = logging.getLogger(__name__)

def landing_page(request):
    """Landing page view"""
    return render(request, 'landing_page.html')

def auth_page(request):
    """Login/Register page view"""
    return render(request, 'auth.html')

@csrf_exempt
def register_voter(request):
    """Handle voter registration with approval system"""
    if request.method == 'POST':
        try:
            # Handle both FormData and JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Handle FormData
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
                }
            
            # Check if voter ID already exists
            if Voter.objects.filter(voter_id=data['voterId']).exists():
                return JsonResponse({
                    'success': False, 
                    'message': 'Voter ID already exists'
                })
            
            # Check if username already exists
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
            
            # Create user with is_active=False for approval workflow
            user = CustomUser.objects.create_user(
                username=data['voterId'],
                password=data['password'],
                role='voter',
                is_active=False  # User inactive until approved
            )
            
            # Create voter profile with pending approval status
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
                approval_status='pending'  # Set approval status to pending
            )
            
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
    """Handle voter login with approval check"""
    if request.method == 'POST':
        try:
            # Handle both FormData and JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                voter_id = data.get('voterId')
                password = data.get('password')
            else:
                # Handle FormData - check multiple possible field names
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
            
            # Try to authenticate user (this will work even if account is inactive)
            try:
                user = CustomUser.objects.get(username=voter_id)
                if user.check_password(password) and user.role == 'voter':
                    # Check approval status
                    try:
                        voter = Voter.objects.get(user=user)
                        if voter.approval_status == 'pending':
                            return JsonResponse({
                                'success': False,
                                'message': 'Your account is pending approval. Please wait for admin approval.',
                                'status': 'pending_approval'
                            })
                        elif voter.approval_status == 'rejected':
                            return JsonResponse({
                                'success': False,
                                'message': 'Your account has been rejected. Please contact admin.',
                                'status': 'rejected'
                            })
                        elif voter.approval_status == 'approved' and user.is_active:
                            # Approved and active - allow login
                            login(request, user)
                            logger.info(f"Successful login for voter: {voter_id}")
                            return JsonResponse({
                                'success': True, 
                                'message': 'Login successful',
                                'redirect_url': '/voter/'
                            })
                        else:
                            return JsonResponse({
                                'success': False,
                                'message': 'Account not activated. Please contact admin.',
                                'status': 'not_activated'
                            })
                    except Voter.DoesNotExist:
                        return JsonResponse({
                            'success': False, 
                            'message': 'Voter profile not found'
                        })
                else:
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
            logger.error("JSON decode error in login")
            return JsonResponse({
                'success': False, 
                'message': 'Invalid JSON data'
            })
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
    """Handle admin authentication"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data['username']
            password = data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None and (user.is_staff or user.role == 'admin'):
                login(request, user)
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
            return JsonResponse({
                'success': False, 
                'message': f'Login failed: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def voter_dashboard(request):
    """Voter dashboard view with approval status check"""
    if request.user.role != 'voter':
        return redirect('landing')
    
    try:
        voter = Voter.objects.get(user=request.user)
        
        # Check approval status
        if voter.approval_status != 'approved':
            context = {
                'voter': voter,
                'approval_status': voter.approval_status,
                'rejection_reason': voter.rejection_reason if voter.approval_status == 'rejected' else None
            }
            return render(request, 'voter.html', context)
        
        # If approved, show full dashboard
        elections = Election.objects.filter(is_active=True).order_by('-created_at')
        
        context = {
            'voter': voter,
            'elections': elections,
            'approval_status': 'approved'
        }
        return render(request, 'voter.html', context)
    except Voter.DoesNotExist:
        messages.error(request, 'Voter profile not found')
        return redirect('landing')

@login_required
def admin_dashboard(request):
    """Admin dashboard view with voter approval management"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return redirect('landing')
    
    # Get voters by approval status
    pending_voters = Voter.objects.filter(approval_status='pending').order_by('-created_at')
    approved_voters = Voter.objects.filter(approval_status='approved').order_by('-approval_date')
    rejected_voters = Voter.objects.filter(approval_status='rejected').order_by('-updated_at')
    
    elections = Election.objects.all().order_by('-created_at')
    candidates = Candidate.objects.all().order_by('-created_at')
    
    context = {
        'admin_username': request.user.username,
        'is_superuser': request.user.is_superuser,
        'django_admin_url': '/admin/',
        'pending_voters': pending_voters,
        'approved_voters': approved_voters,
        'rejected_voters': rejected_voters,
        'elections': elections,
        'candidates': candidates,
        'pending_count': pending_voters.count(),
        'approved_count': approved_voters.count(),
        'rejected_count': rejected_voters.count(),
    }
    return render(request, 'admin.html', context)

@csrf_exempt
@login_required
def approve_voter(request):
    """Handle voter approval"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    if request.method == 'POST':
        try:
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
    """Handle voter rejection"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    if request.method == 'POST':
        try:
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

def results_page(request):
    """Results page view"""
    return render(request, 'results.html')

def contact_page(request):
    """Contact page view"""
    return render(request, 'contact.html')

def logout_user(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('landing')


