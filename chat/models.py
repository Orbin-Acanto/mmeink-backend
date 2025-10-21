from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import secrets

class CustomerInfo(models.Model):
    """
    Store persistent customer information
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Additional fields
    company = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Metadata
    total_chats = models.IntegerField(default=0)
    last_chat_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_chat_date']
        verbose_name_plural = 'Customer Info'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['last_chat_date']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email})"


class ChatSession(models.Model):
    """
    Main chat session model
    """
    STATUS_CHOICES = (
        ('bot', 'Bot Handling'),
        ('waiting', 'Waiting for Agent'),
        ('assigned', 'Assigned to Agent'),
        ('active', 'Active with Agent'),
        ('on_hold', 'On Hold'),
        ('abandoned', 'Abandoned'),
        ('closed', 'Closed'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Customer Information
    customer = models.ForeignKey(
        CustomerInfo, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='chat_sessions'
    )
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField(db_index=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Session Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='bot', db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Agent Assignment
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_chats'
    )
    
    # Session Metadata
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer_url = models.URLField(blank=True, null=True)
    browser_info = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional custom data
    
    # Chat Resume Token (for email links)
    resume_token = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)
    resume_token_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Flags
    is_abandoned = models.BooleanField(default=False)
    is_resumed = models.BooleanField(default=False)
    requires_followup = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    first_response_at = models.DateTimeField(null=True, blank=True)  # When agent first responded
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Metrics
    wait_time_seconds = models.IntegerField(null=True, blank=True)  # Time in waiting queue
    response_time_seconds = models.IntegerField(null=True, blank=True)  # Time to first agent response
    total_duration_seconds = models.IntegerField(null=True, blank=True)  # Total chat duration
    message_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_agent', 'status']),
            models.Index(fields=['customer_email']),
            models.Index(fields=['is_abandoned', 'status']),
            models.Index(fields=['resume_token']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def generate_resume_token(self):
        """Generate secure token for chat resume"""
        self.resume_token = secrets.token_urlsafe(32)
        self.resume_token_expires_at = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['resume_token', 'resume_token_expires_at'])
        return self.resume_token
    
    def is_resume_token_valid(self):
        """Check if resume token is still valid"""
        if not self.resume_token or not self.resume_token_expires_at:
            return False
        return timezone.now() < self.resume_token_expires_at
    
    def mark_abandoned(self):
        """Mark session as abandoned"""
        if self.status == 'waiting':
            self.is_abandoned = True
            self.status = 'abandoned'
            self.save(update_fields=['is_abandoned', 'status'])
    
    def calculate_wait_time(self):
        """Calculate time spent in waiting queue"""
        if self.first_response_at and self.status in ['assigned', 'active', 'closed']:
            delta = self.first_response_at - self.created_at
            self.wait_time_seconds = int(delta.total_seconds())
            self.save(update_fields=['wait_time_seconds'])
    
    def close_session(self):
        """Close the session and calculate metrics"""
        self.status = 'closed'
        self.closed_at = timezone.now()
        
        # Calculate total duration
        if self.created_at:
            delta = self.closed_at - self.created_at
            self.total_duration_seconds = int(delta.total_seconds())
        
        self.save(update_fields=['status', 'closed_at', 'total_duration_seconds'])
        
        # Decrement agent's chat count
        if self.assigned_agent:
            self.assigned_agent.decrement_chat_count()


class Message(models.Model):
    """
    Individual chat messages
    """
    SENDER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('bot', 'Bot'),
        ('agent', 'Agent'),
        ('system', 'System'),
    )
    
    DELIVERY_STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', db_index=True)
    
    # Sender Information
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES, db_index=True)
    sender_name = models.CharField(max_length=255)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_messages'
    )
    
    # Message Content
    message = models.TextField()
    attachments = models.JSONField(default=list, blank=True)  # Store file URLs/metadata
    
    # Message Status
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='sent')
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    is_internal = models.BooleanField(default=False)  # Internal agent notes
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['sender_type', 'created_at']),
            models.Index(fields=['is_read', 'sender_type']),
        ]
    
    def __str__(self):
        return f"{self.sender_type}: {self.message[:50]}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.delivery_status = 'read'
            self.save(update_fields=['is_read', 'read_at', 'delivery_status'])


class ChatTransfer(models.Model):
    """
    Track chat transfers between agents
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='transfers')
    
    from_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_from'
    )
    to_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_to'
    )
    
    reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    transferred_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-transferred_at']
        indexes = [
            models.Index(fields=['session', 'transferred_at']),
        ]
    
    def __str__(self):
        return f"Transfer from {self.from_agent} to {self.to_agent} at {self.transferred_at}"


class ChatHold(models.Model):
    """
    Track when chats are put on hold
    """
    HOLD_REASON_CHOICES = (
        ('research', 'Need to Research'),
        ('escalation', 'Escalating to Supervisor'),
        ('technical', 'Technical Issue'),
        ('customer_request', 'Customer Requested Hold'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='holds')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='held_chats'
    )
    
    reason = models.CharField(max_length=50, choices=HOLD_REASON_CHOICES)
    notes = models.TextField(blank=True, null=True)
    
    held_at = models.DateTimeField(auto_now_add=True)
    resumed_at = models.DateTimeField(null=True, blank=True)
    hold_duration_seconds = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-held_at']
        indexes = [
            models.Index(fields=['session', 'held_at']),
        ]
    
    def __str__(self):
        return f"Hold on {self.session.customer_name} - {self.reason}"
    
    def resume(self):
        """Resume the chat from hold"""
        self.resumed_at = timezone.now()
        if self.held_at:
            delta = self.resumed_at - self.held_at
            self.hold_duration_seconds = int(delta.total_seconds())
        self.save(update_fields=['resumed_at', 'hold_duration_seconds'])


class ChatNote(models.Model):
    """
    Internal notes that agents can add to chats (not visible to customers)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='notes')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chat_notes'
    )
    
    note = models.TextField()
    is_important = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        return f"Note by {self.agent} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ChatQueue(models.Model):
    """
    Manage priority queue for waiting chats
    """
    QUEUE_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('expired', 'Expired'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='queue_entry')
    
    priority = models.IntegerField(default=0)  # Higher number = higher priority
    queue_position = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=QUEUE_STATUS_CHOICES, default='pending')
    
    entered_queue_at = models.DateTimeField(auto_now_add=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    wait_time_seconds = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-priority', 'entered_queue_at']
        indexes = [
            models.Index(fields=['status', 'priority', 'entered_queue_at']),
        ]
    
    def __str__(self):
        return f"Queue #{self.queue_position} - {self.session.customer_name}"
    
    def calculate_wait_time(self):
        """Calculate current wait time"""
        if self.status == 'pending':
            delta = timezone.now() - self.entered_queue_at
            self.wait_time_seconds = int(delta.total_seconds())
            self.save(update_fields=['wait_time_seconds'])
            return self.wait_time_seconds
        return self.wait_time_seconds


class ChatRating(models.Model):
    """
    Customer ratings for completed chats
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='rating')
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_ratings'
    )
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.TextField(blank=True, null=True)
    
    # Rating categories (optional)
    response_time_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    helpfulness_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    professionalism_rating = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.rating}★ - {self.session.customer_name}"
    
    def save(self, *args, **kwargs):
        """Update agent's average rating when a rating is saved"""
        super().save(*args, **kwargs)
        
        if self.agent:
            # Recalculate agent's average rating
            ratings = ChatRating.objects.filter(agent=self.agent)
            total_ratings = ratings.count()
            avg_rating = ratings.aggregate(models.Avg('rating'))['rating__avg'] or 0
            
            self.agent.average_rating = round(avg_rating, 2)
            self.agent.total_ratings = total_ratings
            self.agent.save(update_fields=['average_rating', 'total_ratings'])


class CannedResponse(models.Model):
    """
    Pre-written responses that agents can use
    """
    CATEGORY_CHOICES = (
        ('greeting', 'Greeting'),
        ('closing', 'Closing'),
        ('common_issue', 'Common Issue'),
        ('escalation', 'Escalation'),
        ('hold', 'Hold Message'),
        ('custom', 'Custom'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='custom')
    message = models.TextField()
    shortcut = models.CharField(max_length=50, unique=True, blank=True, null=True)  # e.g., "/greeting"
    
    # Ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_responses'
    )
    is_global = models.BooleanField(default=False)  # Available to all agents
    
    # Usage stats
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'title']
        indexes = [
            models.Index(fields=['category', 'is_global']),
            models.Index(fields=['shortcut']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.category})"
    
    def increment_usage(self):
        """Increment usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class ChatTranscript(models.Model):
    """
    Archived chat transcripts for long-term storage
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.UUIDField(db_index=True)  # Reference to original session
    
    # Session snapshot
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    agent_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Full transcript
    messages_data = models.JSONField()  # Complete message history
    metadata = models.JSONField(default=dict)  # Session metadata snapshot
    
    # Metrics
    total_messages = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    rating = models.IntegerField(null=True, blank=True)
    
    # Timestamps
    chat_started_at = models.DateTimeField()
    chat_ended_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-chat_ended_at']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['customer_email']),
            models.Index(fields=['chat_started_at']),
        ]
    
    def __str__(self):
        return f"Transcript: {self.customer_name} - {self.chat_started_at.date()}"