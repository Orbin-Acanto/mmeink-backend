from django.contrib import admin
from .models import DailyAgentMetrics, DailySystemMetrics, HourlySystemMetrics, ChatTag, ChatSessionTag

@admin.register(DailyAgentMetrics)
class DailyAgentMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'agent', 'date', 'total_chats', 'average_rating', 
        'average_chat_duration_minutes', 'total_online_minutes'
    ]
    list_filter = ['date', 'agent']
    search_fields = ['agent__username', 'agent__email']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']
    
    def average_chat_duration_minutes(self, obj):
        return f"{obj.average_chat_duration_seconds // 60} min"
    average_chat_duration_minutes.short_description = 'Avg Chat Duration'


@admin.register(DailySystemMetrics)
class DailySystemMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_chats', 'total_bot_handled', 'total_agent_handled', 
        'total_abandoned', 'average_rating', 'peak_hour'
    ]
    list_filter = ['date']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(HourlySystemMetrics)
class HourlySystemMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'hour', 'chats_started', 'chats_completed', 
        'agents_online', 'agents_available', 'average_wait_time_minutes'
    ]
    list_filter = ['timestamp', 'hour']
    date_hierarchy = 'timestamp'
    readonly_fields = ['created_at']
    
    def average_wait_time_minutes(self, obj):
        return f"{obj.average_wait_time_seconds // 60} min"
    average_wait_time_minutes.short_description = 'Avg Wait Time'


@admin.register(ChatTag)
class ChatTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_preview', 'usage_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['usage_count', 'created_at']
    
    def color_preview(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="background-color: {}; padding: 5px 15px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.name
        )
    color_preview.short_description = 'Color'


@admin.register(ChatSessionTag)
class ChatSessionTagAdmin(admin.ModelAdmin):
    list_display = ['session', 'tag', 'added_by', 'added_at']
    list_filter = ['tag', 'added_at']
    search_fields = ['session__customer_name', 'tag__name']
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'