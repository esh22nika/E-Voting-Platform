from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings
from django.utils import timezone
import hashlib
import uuid
import json

class CustomUser(AbstractUser):
    USER_ROLES = (
        ('voter', 'Voter'),
        ('admin', 'Admin'),
        ('observer', 'Observer'),  # For monitoring elections
    )
    role = models.CharField(max_length=10, choices=USER_ROLES, default='voter')
    mobile = models.CharField(max_length=10, validators=[RegexValidator(r'^\d{10}$')])
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    lock_time = models.DateTimeField(null=True, blank=True)

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

    # Enhanced location data for election eligibility
    constituency = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=50, blank=True)
    assembly_constituency = models.CharField(max_length=100, blank=True)
    parliamentary_constituency = models.CharField(max_length=100, blank=True)

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
    face_recognition_verified = models.BooleanField(default=False)

    # Biometric data (for enhanced security)
    face_encoding = models.TextField(blank=True)  # Store face recognition data

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_fully_verified(self):
        return (self.aadhar_verified and self.pan_verified and
                self.voter_id_verified and self.face_recognition_verified)

    def get_eligible_elections(self):
        """Get elections this voter is eligible for based on location"""
        eligible_elections = []

        # National elections - all voters eligible
        national_elections = Election.objects.filter(
            election_type='General Election',
            status='active'
        )
        eligible_elections.extend(national_elections)

        # State elections - voters from same state
        state_elections = Election.objects.filter(
            election_type='State Assembly',
            state=self.state,
            status='active'
        )
        eligible_elections.extend(state_elections)

        # Municipal elections - voters from same city
        municipal_elections = Election.objects.filter(
            election_type='Municipal',
            state=self.state,
            city=self.city,
            status='active'
        )
        eligible_elections.extend(municipal_elections)

        # Panchayat elections - voters from same district
        panchayat_elections = Election.objects.filter(
            election_type='Panchayat',
            state=self.state,
            district=self.district,
            status='active'
        )
        eligible_elections.extend(panchayat_elections)

        return eligible_elections

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
        ('suspended', 'Suspended'),  # For handling issues
    )

    CONSENSUS_STATUS_CHOICES = (
        ('pending', 'Pending Consensus'),
        ('achieved', 'Consensus Achieved'),
        ('failed', 'Consensus Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50, blank=True)  # For municipal elections
    district = models.CharField(max_length=50, blank=True)  # For panchayat elections
    election_type = models.CharField(max_length=50, choices=ELECTION_TYPES)
    year = models.IntegerField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_active = models.BooleanField(default=True)

    # Distributed systems fields
    consensus_status = models.CharField(
        max_length=20,
        choices=CONSENSUS_STATUS_CHOICES,
        default='pending'
    )
    block_hash = models.CharField(max_length=64, blank=True)  # For blockchain-style integrity
    previous_block_hash = models.CharField(max_length=64, blank=True)
    merkle_root = models.CharField(max_length=64, blank=True)  # For vote verification

    # Clock synchronization
    synchronized_start_time = models.DateTimeField(null=True, blank=True)
    synchronized_end_time = models.DateTimeField(null=True, blank=True)
    ntp_server = models.CharField(max_length=100, default='pool.ntp.org')

    # Fault tolerance
    primary_server = models.CharField(max_length=100, blank=True)
    backup_servers = models.JSONField(default=list)
    replication_factor = models.IntegerField(default=3)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_block_hash(self):
        """Generate blockchain-style hash for election integrity"""
        data = f"{self.id}{self.name}{self.start_date}{self.end_date}{self.previous_block_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.block_hash:
            self.block_hash = self.generate_block_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Candidate(models.Model):
    PARTY_CHOICES = (
        ('BJP', 'BJP'),
        ('Congress', 'Congress'),
        ('AAP', 'AAP'),
        ('Left Front', 'Left Front'),
        ('BSP', 'BSP'),
        ('SP', 'SP'),
        ('TMC', 'TMC'),
        ('JDU', 'JDU'),
        ('RJD', 'RJD'),
        ('Independent', 'Independent'),
        ('Other', 'Other'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    party = models.CharField(max_length=50, choices=PARTY_CHOICES)
    constituency = models.CharField(max_length=100)
    symbol = models.CharField(max_length=50)
    education = models.CharField(max_length=200, blank=True)
    manifesto = models.TextField(blank=True)

    # Additional candidate information
    age = models.IntegerField(null=True, blank=True)
    criminal_cases = models.IntegerField(default=0)
    assets_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    created_at = models.DateTimeField(auto_now_add=True)

    # Distributed verification
    verification_hash = models.CharField(max_length=64, blank=True)
    is_verified = models.BooleanField(default=False)

    def generate_verification_hash(self):
        """Generate verification hash for candidate integrity"""
        data = f"{self.name}{self.party}{self.constituency}{self.election.id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.verification_hash:
            self.verification_hash = self.generate_verification_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.party}"

class Vote(models.Model):
    VOTE_STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('consensus_pending', 'Awaiting Consensus'),
        ('finalized', 'Finalized'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Distributed systems fields
    vote_hash = models.CharField(max_length=64, unique=True)
    previous_vote_hash = models.CharField(max_length=64, blank=True)
    nonce = models.CharField(max_length=32)  # For proof-of-work style verification
    status = models.CharField(max_length=20, choices=VOTE_STATUS_CHOICES, default='pending')

    # Consensus tracking
    node_confirmations = models.JSONField(default=list)  # Track which nodes confirmed this vote
    confirmation_count = models.IntegerField(default=0)
    required_confirmations = models.IntegerField(default=3)

    # Fault tolerance
    backup_nodes = models.JSONField(default=list)
    is_replicated = models.BooleanField(default=False)

    # Privacy protection
    encrypted_vote_data = models.TextField(blank=True)  # For zero-knowledge proofs

    class Meta:
        unique_together = ('voter', 'election')

    def generate_vote_hash(self):
        """Generate blockchain-style hash for vote integrity"""
        data = f"{self.voter.voter_id}{self.candidate.id}{self.election.id}{self.timestamp}{self.nonce}"
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_nonce(self):
        """Generate random nonce for vote verification"""
        return uuid.uuid4().hex[:32]

    def save(self, *args, **kwargs):
        if not self.nonce:
            self.nonce = self.generate_nonce()
        if not self.vote_hash:
            self.vote_hash = self.generate_vote_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.voter.voter_id} voted for {self.candidate.name}"

class VoteConsensusLog(models.Model):
    """Track consensus process for votes"""
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE, related_name='consensus_logs')
    node_id = models.CharField(max_length=100)
    consensus_round = models.IntegerField()
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    signature = models.TextField()  # Digital signature from node

    class Meta:
        unique_together = ('vote', 'node_id', 'consensus_round')

class ElectionNode(models.Model):
    """Track distributed nodes participating in election"""
    NODE_STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('faulty', 'Faulty'),
        ('byzantine', 'Byzantine Fault'),
    )

    node_id = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    port = models.IntegerField()
    status = models.CharField(max_length=20, choices=NODE_STATUS_CHOICES, default='active')
    last_heartbeat = models.DateTimeField(auto_now=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='nodes')

    # Performance metrics
    response_time = models.FloatField(default=0.0)
    uptime_percentage = models.FloatField(default=100.0)

    def __str__(self):
        return f"Node {self.node_id} - {self.status}"

class AuditLog(models.Model):
    """Comprehensive audit logging for transparency"""
    LOG_TYPES = (
        ('vote_cast', 'Vote Cast'),
        ('vote_verified', 'Vote Verified'),
        ('consensus_achieved', 'Consensus Achieved'),
        ('node_failure', 'Node Failure'),
        ('election_started', 'Election Started'),
        ('election_ended', 'Election Ended'),
        ('admin_action', 'Admin Action'),
        ('security_event', 'Security Event'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    election = models.ForeignKey(Election, on_delete=models.SET_NULL, null=True, blank=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Immutability protection
    hash_chain = models.CharField(max_length=64)
    previous_hash = models.CharField(max_length=64, blank=True)

    def generate_hash(self):
        """Generate hash for audit log integrity"""
        data = f"{self.log_type}{self.user_id}{self.timestamp}{self.details}{self.previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.hash_chain:
            self.hash_chain = self.generate_hash()
        super().save(*args, **kwargs)

class VoterSession(models.Model):
    """Track voter sessions for security"""
    voter = models.ForeignKey(Voter, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=128, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    # Security fields
    device_fingerprint = models.CharField(max_length=128, blank=True)
    location_hash = models.CharField(max_length=64, blank=True)