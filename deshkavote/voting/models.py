from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings

class CustomUser(AbstractUser):
    USER_ROLES = (
        ('voter', 'Voter'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=USER_ROLES, default='voter')
    mobile = models.CharField(max_length=10, validators=[RegexValidator(r'^\d{10}$')])
    is_verified = models.BooleanField(default=False)
    # Changed default to False for approval workflow
    is_active = models.BooleanField(default=False)

class Voter(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    )
    
    APPROVAL_STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    mobile = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    parent_spouse_name = models.CharField(max_length=100)
    street_address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=6)
    place_of_birth = models.CharField(max_length=50)
    voter_id = models.CharField(max_length=20, unique=True)
    aadhar_number = models.CharField(max_length=12)
    pan_number = models.CharField(max_length=10)
    
    # Approval system fields
    approval_status = models.CharField(
        max_length=10, 
        choices=APPROVAL_STATUS_CHOICES, 
        default='pending'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_voters'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Verification status
    aadhar_verified = models.BooleanField(default=False)
    pan_verified = models.BooleanField(default=False)
    voter_id_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_fully_verified(self):
        return self.aadhar_verified and self.pan_verified and self.voter_id_verified
    
    def __str__(self):
        return f"{self.voter_id} - {self.first_name} {self.last_name}"

class Election(models.Model):
    ELECTION_TYPES = (
        ('General Election', 'General Election'),
        ('State Assembly', 'State Assembly'),
        ('Municipal', 'Municipal'),
        ('Panchayat', 'Panchayat'),
        ('By-Election', 'By-Election'),
    )
    
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    )
    
    name = models.CharField(max_length=200)
    state = models.CharField(max_length=50)
    election_type = models.CharField(max_length=50, choices=ELECTION_TYPES)
    year = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Candidate(models.Model):
    PARTY_CHOICES = (
        ('BJP', 'BJP'),
        ('Congress', 'Congress'),
        ('AAP', 'AAP'),
        ('Left Front', 'Left Front'),
        ('Independent', 'Independent'),
        ('Other', 'Other'),
    )
    
    name = models.CharField(max_length=100)
    party = models.CharField(max_length=50, choices=PARTY_CHOICES)
    constituency = models.CharField(max_length=100)
    symbol = models.CharField(max_length=50)
    education = models.CharField(max_length=200, blank=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.party}"

class Vote(models.Model):
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('voter', 'election')  # One vote per voter per election
    
    def __str__(self):
        return f"{self.voter.voter_id} voted for {self.candidate.name}"