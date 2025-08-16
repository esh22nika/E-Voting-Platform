from django.shortcuts import render, redirect
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
    """Handle voter registration"""
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
            
            # Create user
            user = CustomUser.objects.create_user(
                username=data['voterId'],
                password=data['password'],
                role='voter'
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
                pan_number=data['panNumber']
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Registration successful! Please login with your credentials.'
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
    """Handle voter login"""
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
            
            user = authenticate(request, username=voter_id, password=password)
            
            if user is not None:
                if user.role == 'voter':
                    login(request, user)
                    logger.info(f"Successful login for voter: {voter_id}")
                    return JsonResponse({
                        'success': True, 
                        'message': 'Login successful',
                        'redirect_url': '/voter/'
                    })
                else:
                    logger.warning(f"Non-voter attempted login: {voter_id}")
                    return JsonResponse({
                        'success': False, 
                        'message': 'Invalid Voter ID or password'
                    })
            else:
                logger.warning(f"Failed login attempt for voter: {voter_id}")
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
    """Voter dashboard view"""
    if request.user.role != 'voter':
        return redirect('landing')
    
    try:
        voter = Voter.objects.get(user=request.user)
        elections = Election.objects.all().order_by('-created_at')
        
        context = {
            'voter': voter,
            'elections': elections,
        }
        return render(request, 'voter.html', context)
    except Voter.DoesNotExist:
        messages.error(request, 'Voter profile not found')
        return redirect('landing')

@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    if not (request.user.is_staff or request.user.role == 'admin'):
        return redirect('landing')
    
    voters = Voter.objects.all().order_by('-created_at')
    elections = Election.objects.all().order_by('-created_at')
    candidates = Candidate.objects.all().order_by('-created_at')
    
    context = {
        'admin_username': request.user.username,
        'is_superuser': request.user.is_superuser,
        'django_admin_url': '/admin/',
        'voters': voters,
        'elections': elections,
        'candidates': candidates,
    }
    return render(request, 'admin.html', context)

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



