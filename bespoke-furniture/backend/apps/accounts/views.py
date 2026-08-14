from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        self._link_matching_guest_customer(request.user)
        return Response(UserSerializer(request.user).data)

    def _link_matching_guest_customer(self, user):
        """
        If this account has no linked Customer profile yet, but a guest
        Customer record exists with the same email (from an order placed
        before registering/logging in), link it so their order history
        becomes visible without needing to place a new order.
        """
        from apps.customers.models import Customer

        if hasattr(user, "customer_profile"):
            return
        guest_customer = Customer.objects.filter(email=user.email, user__isnull=True).first()
        if guest_customer:
            guest_customer.user = user
            guest_customer.save(update_fields=["user"])
