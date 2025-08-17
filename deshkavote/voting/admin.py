from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Voter, Election, Candidate, Vote

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )

@admin.register(Voter)
class VoterAdmin(admin.ModelAdmin):
    list_display = ('voter_id', 'full_name', 'email', 'state', 'approval_status', 'is_fully_verified', 'created_at')
    list_filter = ('approval_status', 'state', 'gender', 'aadhar_verified', 'pan_verified', 'voter_id_verified', 'created_at')
    search_fields = ('voter_id', 'first_name', 'last_name', 'email', 'mobile')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'mobile', 'date_of_birth', 'gender')
        }),
        ('Address Information', {
            'fields': ('street_address', 'city', 'state', 'pincode', 'place_of_birth')
        }),
        ('Identity Information', {
            'fields': ('voter_id', 'aadhar_number', 'pan_number', 'parent_spouse_name')
        }),
        ('Approval Information', {
            'fields': ('approval_status', 'approved_by', 'approval_date', 'rejection_reason')
        }),
        ('Verification Status', {
            'fields': ('aadhar_verified', 'pan_verified', 'voter_id_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_voters', 'reject_voters']
    
    def approve_voters(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(approval_status='pending').update(
            approval_status='approved',
            approved_by=request.user,
            approval_date=timezone.now()
        )
        # Also activate the user accounts
        for voter in queryset.filter(approval_status='approved'):
            voter.user.is_active = True
            voter.user.save()
        
        self.message_user(request, f'{updated} voters approved successfully.')
    approve_voters.short_description = "Approve selected voters"
    
    def reject_voters(self, request, queryset):
        updated = queryset.filter(approval_status='pending').update(
            approval_status='rejected',
            rejection_reason='Rejected via admin action'
        )
        # Deactivate user accounts
        for voter in queryset.filter(approval_status='rejected'):
            voter.user.is_active = False
            voter.user.save()
        
        self.message_user(request, f'{updated} voters rejected.')
    reject_voters.short_description = "Reject selected voters"
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def is_fully_verified(self, obj):
        if obj.is_fully_verified:
            return format_html('<span style="color: green;">✓ Verified</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')
    is_fully_verified.short_description = 'Verification Status'

@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'election_type', 'year', 'start_date', 'end_date', 'is_active', 'created_at')
    list_filter = ('state', 'election_type', 'year', 'is_active', 'created_at')
    search_fields = ('name', 'state')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Election Information', {
            'fields': ('name', 'state', 'election_type', 'year')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'party', 'constituency', 'symbol', 'election', 'created_at')
    list_filter = ('party', 'election', 'created_at')
    search_fields = ('name', 'party', 'constituency')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Candidate Information', {
            'fields': ('name', 'party', 'constituency', 'symbol', 'education')
        }),
        ('Election', {
            'fields': ('election',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'election', 'candidate', 'timestamp')
    list_filter = ('election', 'timestamp')
    search_fields = ('voter__voter_id', 'voter__first_name', 'voter__last_name')
    readonly_fields = ('timestamp',)
    
    def has_change_permission(self, request, obj=None):
        # Votes should not be editable after creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Votes should not be deletable to maintain integrity
        return False

# Admin site customization
admin.site.site_header = "DeshKaVote Administration"
admin.site.site_title = "DeshKaVote Admin"
admin.site.index_title = "Welcome to DeshKaVote Administration"

# Register your models here.
