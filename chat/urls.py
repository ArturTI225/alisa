from django.urls import path

from .views import ConversationListView, ConversationDetailView


app_name = "chat"

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation_list"),
    path("<int:pk>/", ConversationDetailView.as_view(), name="conversation_detail"),
]
