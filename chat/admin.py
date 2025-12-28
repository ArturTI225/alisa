from django.contrib import admin

from .models import ChatMessage, Conversation


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "booking", "sender", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("text", "sender__username")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "booking", "created_at")
    search_fields = ("ad__title", "booking__id")
    filter_horizontal = ("participants",)
