from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class DailyAgentMetrics(models.Model):
    """
    Daily aggregated metrics per agent
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_metrics')
    date = models.DateField(db_index=True)
    
    # Chat metrics
    total_chats = models.IntegerField(default=0)
    total_messages_sent = models.IntegerField(default=0)
    total_chat_duration_seconds = models.IntegerField(default=0)
    average_chat_duration_seconds = models.IntegerField(default=0)
    
    # Response metrics
    average_first_response_seconds = models.IntegerField(default=0)
    average_response_time_seconds = models.IntegerField(default=0)
    
    # Quality metrics
    total_ratings_received = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    
    # Transfer metrics
    chats_transferred_out = models.IntegerField(default=0)
    chats_transferred_in = models.IntegerField(default=0)
    
    # Availability
    total_online_minutes = models.IntegerField(default=0)
    total_break_minutes = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'agent']
        unique_together = ['agent', 'date']
        indexes = [
            models.Index(fields=['agent', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.agent.username} - {self.date}"


class DailySystemMetrics(models.Model):
    """
    Daily system-wide metrics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True, db_index=True)
    
    # Chat volume
    total_chats = models.IntegerField(default=0)
    total_bot_handled = models.IntegerField(default=0)
    total_agent_handled = models.IntegerField(default=0)
    total_abandoned = models.IntegerField(default=0)
    
    # Wait time metrics
    average_wait_time_seconds = models.IntegerField(default=0)
    max_wait_time_seconds = models.IntegerField(default=0)
    
    # Response time metrics
    average_first_response_seconds = models.IntegerField(default=0)
    
    # Customer satisfaction
    total_ratings = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    
    # Peak hours
    peak_hour = models.IntegerField(null=True, blank=True)  # Hour of day (0-23)
    peak_hour_chat_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"System Metrics - {self.date}"


class HourlySystemMetrics(models.Model):
    """
    Hourly system metrics for detailed analysis
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(db_index=True)
    hour = models.IntegerField()  # 0-23
    
    # Chat counts
    chats_started = models.IntegerField(default=0)
    chats_completed = models.IntegerField(default=0)
    chats_in_queue = models.IntegerField(default=0)
    
    # Agent availability
    agents_online = models.IntegerField(default=0)
    agents_available = models.IntegerField(default=0)
    agents_busy = models.IntegerField(default=0)
    
    # Performance
    average_wait_time_seconds = models.IntegerField(default=0)
    average_response_time_seconds = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['hour']),
        ]
    
    def __str__(self):
        return f"Hourly Metrics - {self.timestamp}"


class ChatTag(models.Model):
    """
    Tags for categorizing chats
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#808080')
    description = models.TextField(blank=True, null=True)
    
    # Usage
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ChatSessionTag(models.Model):
    """
    Many-to-many relationship between ChatSession and ChatTag
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey('chat.ChatSession', on_delete=models.CASCADE, related_name='session_tags')
    tag = models.ForeignKey(ChatTag, on_delete=models.CASCADE, related_name='tagged_sessions')
    
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_tags'
    )
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['session', 'tag']
        ordering = ['added_at']
    
    def __str__(self):
        return f"{self.session.customer_name} - {self.tag.name}"