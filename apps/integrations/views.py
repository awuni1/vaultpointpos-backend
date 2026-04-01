from .models import generate_api_key
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin
from .models import APIKey, Webhook, WebhookDelivery
from .serializers import APIKeySerializer, WebhookSerializer, WebhookDeliverySerializer
from .services import WebhookService


class APIKeyListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        keys = APIKey.objects.filter(owner=request.user)
        return Response(APIKeySerializer(keys, many=True).data)

    def post(self, request):
        serializer = APIKeySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class APIKeyDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return APIKey.objects.get(pk=pk, owner=self.request.user)
        except APIKey.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(APIKeySerializer(obj).data)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class APIKeyRotateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            api_key = APIKey.objects.get(pk=pk, owner=request.user)
        except APIKey.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        api_key.key = generate_api_key()
        api_key.save(update_fields=['key'])
        return Response(APIKeySerializer(api_key).data)


class WebhookListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(WebhookSerializer(Webhook.objects.all(), many=True).data)

    def post(self, request):
        serializer = WebhookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WebhookDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Webhook.objects.get(pk=pk)
        except Webhook.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(WebhookSerializer(obj).data)

    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = WebhookSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookDeliveryListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        deliveries = WebhookDelivery.objects.filter(webhook_id=pk)
        return Response(WebhookDeliverySerializer(deliveries[:100], many=True).data)


class WebhookTestView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            webhook = Webhook.objects.get(pk=pk)
        except Webhook.DoesNotExist:
            return Response({'error': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        test_payload = {'event': 'test.ping', 'message': 'SwiftPOS webhook test', 'webhook_id': pk}
        # Temporarily add 'test.ping' to dispatch
        original_events = webhook.events
        webhook.events = ['test.ping']
        webhook.save(update_fields=['events'])
        WebhookService.dispatch('test.ping', test_payload)
        webhook.events = original_events
        webhook.save(update_fields=['events'])

        return Response({'message': 'Test ping sent.'})
