from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, AgentBreak

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'username', 'get_full_name', 'role', 
        'status_badge', 'current_chats_count', 'average_rating', 
        'total_chats_handled', 'last_activity'
    ]
    list_filter = ['role', 'status', 'is_available', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {
            'fields': ('role', 'phone', 'avatar', 'bio')
        }),
        ('Agent Status', {
            'fields': ('status', 'is_available', 'current_chats_count', 'max_concurrent_chats')
        }),
        ('Metrics', {
            'fields': ('total_chats_handled', 'average_rating', 'total_ratings')
        }),
        ('Timestamps', {
            'fields': ('last_activity', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_activity', 'total_chats_handled', 'average_rating', 'total_ratings']
    
    def status_badge(self, obj):
        colors = {
            'online': 'green',
            'offline': 'gray',
            'busy': 'orange',
            'break': 'blue'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(AgentBreak)
class AgentBreakAdmin(admin.ModelAdmin):
    list_display = ['agent', 'break_type', 'start_time', 'end_time', 'duration_minutes']
    list_filter = ['break_type', 'start_time']
    search_fields = ['agent__username', 'agent__email', 'reason']
    date_hierarchy = 'start_time'
    readonly_fields = ['start_time', 'duration_minutes']