from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import generic
from rest_framework import permissions, viewsets

from accounts.models import Notification
from accounts.utils import notify_user
from .forms import MessageForm
from .models import ChatMessage, Conversation
from .serializers import ChatMessageSerializer, ConversationSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(participants=user)
            .select_related("ad", "booking")
            .prefetch_related("participants")
        )

    def perform_create(self, serializer):
        convo = serializer.save()
        convo.participants.add(self.request.user)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatMessage.objects.filter(
            conversation__participants=user
        ).select_related("conversation", "sender", "booking")

    def perform_create(self, serializer):
        convo = serializer.validated_data["conversation"]
        if not convo.participants.filter(pk=self.request.user.pk).exists():
            convo.participants.add(self.request.user)
        booking = convo.booking if convo else None
        message = serializer.save(sender=self.request.user, booking=booking)
        recipients = convo.participants.exclude(pk=self.request.user.pk)
        for user in recipients:
                notify_user(
                    user=user,
                    notif_type=Notification.Type.NEW_MESSAGE,
                    title="Mesaj nou",
                    body=message.text[:140],
                    link=f"/chat/{convo.pk}/",
                )
        return message


class ConversationListView(LoginRequiredMixin, generic.ListView):
    template_name = "chat/conversations.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants=self.request.user)
            .select_related("ad", "booking")
            .prefetch_related("participants")
            .order_by("-created_at")
        )


class ConversationDetailView(LoginRequiredMixin, generic.DetailView):
    template_name = "chat/detail.html"
    model = Conversation
    context_object_name = "conversation"

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants=self.request.user)
            .select_related("ad", "booking")
            .prefetch_related("participants", "messages__sender")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = MessageForm()
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = ChatMessage.objects.create(
                conversation=self.object,
                booking=self.object.booking,
                sender=request.user,
                text=form.cleaned_data.get("text", ""),
                attachment=form.cleaned_data.get("attachment"),
            )
            for user in self.object.participants.exclude(pk=request.user.pk):
                notify_user(
                    user=user,
                    notif_type=Notification.Type.NEW_MESSAGE,
                    title="Mesaj nou",
                    body=msg.text[:140],
                    link=reverse("chat:conversation_detail", args=[self.object.pk]),
                )
        return redirect("chat:conversation_detail", pk=self.object.pk)
