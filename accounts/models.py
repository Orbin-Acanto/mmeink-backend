from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class User(AbstractUser):
    """
    Extended User model for agents and admins
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('agent', 'Agent'),
        ('supervisor', 'Supervisor'),
    )
    
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
        ('break', 'On Break'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    
    # Agent Profile
    phone = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Agent Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    is_available = models.BooleanField(default=False)
    current_chats_count = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    max_concurrent_chats = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(20)])
    
    # Metrics
    total_chats_handled = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_ratings = models.IntegerField(default=0)
    
    # Timestamps
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['status', 'is_available']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
    
    def can_accept_chat(self):
        """Check if agent can accept more chats"""
        return (
            self.is_available and 
            self.status == 'online' and 
            self.current_chats_count < self.max_concurrent_chats
        )
    
    def increment_chat_count(self):
        """Increment current chats count"""
        self.current_chats_count += 1
        self.total_chats_handled += 1
        self.save(update_fields=['current_chats_count', 'total_chats_handled'])
    
    def decrement_chat_count(self):
        """Decrement current chats count"""
        if self.current_chats_count > 0:
            self.current_chats_count -= 1
            self.save(update_fields=['current_chats_count'])


class AgentBreak(models.Model):
    """
    Track agent break times
    """
    BREAK_TYPE_CHOICES = (
        ('lunch', 'Lunch Break'),
        ('short', 'Short Break'),
        ('meeting', 'Meeting'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='breaks')
    break_type = models.CharField(max_length=20, choices=BREAK_TYPE_CHOICES, default='short')
    reason = models.CharField(max_length=255, blank=True, null=True)
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['agent', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.agent.username} - {self.break_type} on {self.start_time.date()}"
