from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User, Notification
from config.observability import bind_log_context
from ads.models import Ad
from services.models import ServiceCategory
from .consumers import broadcast_message, group_name_for
from .models import ChatMessage, Conversation


class ConversationAPITests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client",
            password="pass123",
            role=User.Roles.CLIENT,
            city="Bucharest",
        )
        self.provider = User.objects.create_user(
            username="provider",
            password="pass123",
            role=User.Roles.PROVIDER,
            city="Bucharest",
        )
        category = ServiceCategory.objects.create(name="Electric", slug="electric")
        self.ad = Ad.objects.create(
            client=self.client_user,
            title="Reparatie",
            description="Lampa nu merge",
            category=category,
            city="Bucharest",
        )
        self.client.login(username="client", password="pass123")

    def test_create_conversation_and_message(self):
        convo_url = reverse("v1:conversation-list")
        resp = self.client.post(
            convo_url,
            {"ad": self.ad.id, "participant_ids": [self.provider.id]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        convo_id = resp.data["id"]
        msg_url = reverse("v1:chatmessage-list")
        resp_msg = self.client.post(
            msg_url,
            {"conversation": convo_id, "text": "Salut"},
            format="json",
        )
        self.assertEqual(resp_msg.status_code, 201, resp_msg.data)
        # provider gets notification
        self.client.logout()
        self.client.login(username="provider", password="pass123")
        notifs = Notification.objects.filter(user=self.provider, type=Notification.Type.NEW_MESSAGE)
        self.assertTrue(notifs.exists())


class ConversationDetailViewTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="client_web",
            password="pass123",
            role=User.Roles.CLIENT,
        )
        self.provider = User.objects.create_user(
            username="provider_web",
            password="pass123",
            role=User.Roles.PROVIDER,
        )
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.client_user, self.provider)
        ChatMessage.objects.create(
            conversation=self.conversation,
            sender=self.provider,
            text="Salut din test",
        )

    def test_detail_view_renders_for_participant(self):
        self.client.login(username="client_web", password="pass123")

        response = self.client.get(
            reverse("chat:conversation_detail", args=[self.conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Salut din test")


class ChatObservabilityTests(TestCase):
    def test_broadcast_message_includes_explicit_request_id(self):
        layer = Mock()
        send_sync = Mock()

        with patch("channels.layers.get_channel_layer", return_value=layer), patch(
            "asgiref.sync.async_to_sync", return_value=send_sync
        ):
            broadcast_message(
                conversation_id=17,
                message_payload={"id": 101, "text": "Salut"},
                request_id="chat-explicit-123",
            )

        send_sync.assert_called_once_with(
            group_name_for(17),
            {
                "type": "chat.message",
                "message": {"id": 101, "text": "Salut"},
                "request_id": "chat-explicit-123",
            },
        )

    def test_broadcast_message_uses_context_request_id(self):
        layer = Mock()
        send_sync = Mock()

        with patch("channels.layers.get_channel_layer", return_value=layer), patch(
            "asgiref.sync.async_to_sync", return_value=send_sync
        ):
            with bind_log_context(request_id="chat-context-456"):
                broadcast_message(
                    conversation_id=21,
                    message_payload={"id": 202, "text": "Salut context"},
                )

        send_sync.assert_called_once_with(
            group_name_for(21),
            {
                "type": "chat.message",
                "message": {"id": 202, "text": "Salut context"},
                "request_id": "chat-context-456",
            },
        )
