import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from .models import Election, Vote, VoteConsensusLog, ElectionNode, Voter, CustomUser
import logging

logger = logging.getLogger(__name__)

class ElectionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time election monitoring"""

    async def connect(self):
        self.election_id = self.scope['url_route']['kwargs']['election_id']
        self.election_group_name = f'election_{self.election_id}'

        # Check if user is authenticated and authorized
        user = self.scope.get('user')
        if user is None or isinstance(user, AnonymousUser):
            await self.close()
            return

        # Check authorization (only admins/observers can monitor)
        is_authorized = await self.check_authorization(user, self.election_id)
        if not is_authorized:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.election_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.election_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        logger.info(f"Received message from WebSocket: {message}")
        await self.send(text_data=json.dumps({'message': message}))

    @database_sync_to_async
    def check_authorization(self, user, election_id):
        """Check if the user is authorized to view this election"""
        try:
            election = Election.objects.get(id=election_id)
            return user.is_staff or user.role in ['admin', 'observer']
        except Election.DoesNotExist:
            return False

    async def send_election_update(self, event):
        """Send a real-time election update to the group"""
        await self.send(text_data=json.dumps({
            'type': 'election_update',
            'data': event['data']
        }))

class VoteConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time vote status updates"""

    async def connect(self):
        self.vote_id = self.scope['url_route']['kwargs']['vote_id']
        self.vote_group_name = f'vote_{self.vote_id}'

        user = self.scope.get('user')
        if user is None or isinstance(user, AnonymousUser):
            await self.close()
            return

        is_authorized = await self.check_authorization(user, self.vote_id)
        if not is_authorized:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.vote_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.vote_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def check_authorization(self, user, vote_id):
        """Check if the user is authorized to view this vote's status"""
        try:
            vote = Vote.objects.get(id=vote_id)
            return user.is_staff or user.role in ['admin', 'observer'] or vote.voter.user == user
        except Vote.DoesNotExist:
            return False

    async def send_vote_update(self, event):
        """Send a real-time vote update to the group"""
        await self.send(text_data=json.dumps({
            'type': 'vote_update',
            'data': event['data']
        }))

class VoterConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for general voter notifications"""

    async def connect(self):
        user = self.scope.get('user')
        if user is None or isinstance(user, AnonymousUser):
            await self.close()
            return

        # Check if user is a voter
        if user.role != 'voter':
            await self.close()
            return

        # Get voter instance
        try:
            voter = await self.get_voter(user)
            if not voter:
                await self.close()
                return
        except Exception:
            await self.close()
            return

        self.voter_group_name = f'voter_{user.id}'

        await self.channel_layer.group_add(
            self.voter_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'message': 'Connected to voter updates'
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'voter_group_name'):
            await self.channel_layer.group_discard(
                self.voter_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')
            
            # Echo back the message for testing
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'message': f'Received: {message}'
            }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON received'
            }))

    @database_sync_to_async
    def get_voter(self, user):
        """Get voter instance for the user"""
        try:
            return Voter.objects.get(user=user)
        except Voter.DoesNotExist:
            return None

    async def send_voter_notification(self, event):
        """Send notification to voter"""
        await self.send(text_data=json.dumps({
            'type': 'voter_notification',
            'data': event['data']
        }))

    async def send_vote_update(self, event):
        """Send vote update to voter"""
        await self.send(text_data=json.dumps({
            'type': 'vote_update',
            'data': event['data']
        }))

class AdminConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time admin dashboard updates"""

    async def connect(self):
        self.admin_group_name = 'admin_dashboard'

        user = self.scope.get('user')
        if user is None or isinstance(user, AnonymousUser) or not (user.is_staff or user.role == 'admin'):
            await self.close()
            return

        await self.channel_layer.group_add(
            self.admin_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.admin_group_name,
            self.channel_name
        )

    async def send_admin_update(self, event):
        """Send a real-time update to the admin dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'admin_update',
            'data': event['data']
        }))