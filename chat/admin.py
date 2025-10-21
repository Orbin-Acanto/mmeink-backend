from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import (
    CustomerInfo, ChatSession, Message, ChatTransfer, 
    ChatHold, ChatNote, ChatQueue, ChatRating, 
    CannedResponse, ChatTranscript
)

@admin.register(CustomerInfo)
class CustomerInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'total_chats', 'last_chat_date', 'created_at']
    list_filter = ['last_chat_date', 'created_at']
    search_fields = ['name', 'email', 'phone', 'company']
    readonly_fields = ['total_chats', 'last_chat_date', 'created_at', 'updated_at']
    date_hierarchy = 'last_chat_date'


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['sender_type', 'sender_name', 'message', 'is_read', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False


class ChatNoteInline(admin.TabularInline):
    model = ChatNote
    extra = 0
    fields = ['agent', 'note', 'is_important', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'customer_name', 'customer_email', 
        'status_badge', 'priority', 'assigned_agent', 
        'message_count', 'wait_time_minutes', 'created_at'
    ]
    list_filter = ['status', 'priority', 'is_abandoned', 'created_at']
    search_fields = ['customer_name', 'customer_email', 'id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'first_response_at', 
        'closed_at', 'wait_time_seconds', 'response_time_seconds', 
        'total_duration_seconds', 'message_count'
    ]
    date_hierarchy = 'created_at'
    inlines = [MessageInline, ChatNoteInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'customer_name', 'customer_email', 'customer_phone')
        }),
        ('Session Details', {
            'fields': ('id', 'status', 'priority', 'assigned_agent')
        }),
        ('Metadata', {
            'fields': ('user_ip', 'user_agent', 'referrer_url', 'browser_info', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Flags', {
            'fields': ('is_abandoned', 'is_resumed', 'requires_followup'),
        }),
        ('Resume Token', {
            'fields': ('resume_token', 'resume_token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'first_response_at', 'closed_at')
        }),
        ('Metrics', {
            'fields': ('wait_time_seconds', 'response_time_seconds', 'total_duration_seconds', 'message_count')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'bot': 'blue',
            'waiting': 'orange',
            'assigned': 'cyan',
            'active': 'green',
            'on_hold': 'purple',
            'abandoned': 'red',
            'closed': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def wait_time_minutes(self, obj):
        if obj.wait_time_seconds:
            return f"{obj.wait_time_seconds // 60} min"
        return "-"
    wait_time_minutes.short_description = 'Wait Time'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'sender_type', 'sender_name', 'message_preview', 'is_read', 'created_at']
    list_filter = ['sender_type', 'is_read', 'delivery_status', 'created_at']
    search_fields = ['message', 'sender_name', 'session__customer_name']
    readonly_fields = ['id', 'created_at', 'read_at']
    date_hierarchy = 'created_at'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(ChatTransfer)
class ChatTransferAdmin(admin.ModelAdmin):
    list_display = ['session', 'from_agent', 'to_agent', 'transferred_at', 'accepted_at']
    list_filter = ['transferred_at', 'accepted_at']
    search_fields = ['session__customer_name', 'from_agent__username', 'to_agent__username']
    readonly_fields = ['transferred_at', 'accepted_at']
    date_hierarchy = 'transferred_at'


@admin.register(ChatHold)
class ChatHoldAdmin(admin.ModelAdmin):
    list_display = ['session', 'agent', 'reason', 'held_at', 'resumed_at', 'hold_duration_minutes']
    list_filter = ['reason', 'held_at', 'resumed_at']
    search_fields = ['session__customer_name', 'agent__username', 'notes']
    readonly_fields = ['held_at', 'resumed_at', 'hold_duration_seconds']
    date_hierarchy = 'held_at'
    
    def hold_duration_minutes(self, obj):
        if obj.hold_duration_seconds:
            return f"{obj.hold_duration_seconds // 60} min"
        return "-"
    hold_duration_minutes.short_description = 'Hold Duration'


@admin.register(ChatNote)
class ChatNoteAdmin(admin.ModelAdmin):
    list_display = ['session', 'agent', 'note_preview', 'is_important', 'created_at']
    list_filter = ['is_important', 'created_at']
    search_fields = ['note', 'session__customer_name', 'agent__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = 'Note'


@admin.register(ChatQueue)
class ChatQueueAdmin(admin.ModelAdmin):
    list_display = ['queue_position', 'session', 'priority', 'status', 'wait_time_minutes', 'entered_queue_at']
    list_filter = ['status', 'priority', 'entered_queue_at']
    search_fields = ['session__customer_name', 'session__customer_email']
    readonly_fields = ['entered_queue_at', 'assigned_at', 'wait_time_seconds']
    date_hierarchy = 'entered_queue_at'
    
    def wait_time_minutes(self, obj):
        if obj.wait_time_seconds:
            return f"{obj.wait_time_seconds // 60} min"
        return "-"
    wait_time_minutes.short_description = 'Wait Time'


@admin.register(ChatRating)
class ChatRatingAdmin(admin.ModelAdmin):
    list_display = ['session', 'agent', 'rating_stars', 'response_time_rating', 'helpfulness_rating', 'professionalism_rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['session__customer_name', 'agent__username', 'feedback']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def rating_stars(self, obj):
        return '⭐' * obj.rating
    rating_stars.short_description = 'Rating'


@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'shortcut', 'is_global', 'usage_count', 'created_by']
    list_filter = ['category', 'is_global', 'created_at']
    search_fields = ['title', 'message', 'shortcut']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']


@admin.register(ChatTranscript)
class ChatTranscriptAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'customer_name', 'customer_email', 'agent_name', 'total_messages', 'rating', 'chat_started_at']
    list_filter = ['chat_started_at', 'archived_at', 'rating']
    search_fields = ['customer_name', 'customer_email', 'agent_name', 'session_id']
    readonly_fields = ['session_id', 'chat_started_at', 'chat_ended_at', 'archived_at']
    date_hierarchy = 'chat_started_at'