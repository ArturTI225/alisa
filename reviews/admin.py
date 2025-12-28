from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("booking", "ad", "from_user", "to_user", "rating", "created_at")
    list_filter = ("rating", "to_user")
