from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404

from .models import Payment, Withdrawal, Transaction, Coupon, CouponUsage, PaymentGatewayConfig
from .serializers import (
    PaymentSerializer, PaymentListSerializer, PaymentCreateSerializer,
    WithdrawalSerializer, WithdrawalCreateSerializer,
    TransactionSerializer, CouponSerializer, CouponValidateSerializer,
    CouponUsageSerializer, PaymentGatewayConfigSerializer
)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments"""

    queryset = Payment.objects.select_related('user', 'tournament')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['payment_type', 'status', 'gateway', 'user']
    search_fields = ['transaction_id', 'gateway_tracking_code', 'user__username']
    ordering_fields = ['created_at', 'amount', 'completed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'list':
            return PaymentListSerializer
        elif self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Non-admin users see only their own payments
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset

    def perform_create(self, serializer):
        """Create a new payment"""
        # Set user to current user
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed payment"""
        payment = self.get_object()

        # Check if user owns this payment
        if payment.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'شما مجاز به این عملیات نیستید'},
                status=status.HTTP_403_FORBIDDEN
            )

        if payment.retry():
            return Response({
                'message': 'پرداخت برای تلاش مجدد آماده شد',
                'payment': PaymentSerializer(payment).data
            })
        else:
            return Response(
                {'error': 'این پرداخت قابل تلاش مجدد نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_completed(self, request, pk=None):
        """Mark payment as completed (admin only)"""
        payment = self.get_object()
        tracking_code = request.data.get('tracking_code', '')

        if payment.mark_as_completed(tracking_code=tracking_code):
            return Response({
                'message': 'پرداخت به عنوان موفق علامت خورد',
                'payment': PaymentSerializer(payment).data
            })
        else:
            return Response(
                {'error': 'پرداخت قبلاً تکمیل شده است'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def mark_failed(self, request, pk=None):
        """Mark payment as failed (admin only)"""
        payment = self.get_object()
        reason = request.data.get('reason', '')

        if payment.mark_as_failed(reason=reason):
            return Response({
                'message': 'پرداخت به عنوان ناموفق علامت خورد',
                'payment': PaymentSerializer(payment).data
            })
        else:
            return Response(
                {'error': 'این پرداخت قابل علامت‌گذاری به عنوان ناموفق نیست'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def refund(self, request, pk=None):
        """Refund a payment (admin only)"""
        payment = self.get_object()
        reason = request.data.get('reason', '')

        try:
            payment.refund(reason=reason, admin_user=request.user)
            return Response({
                'message': 'پرداخت بازگشت داده شد',
                'payment': PaymentSerializer(payment).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WithdrawalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing withdrawals"""

    queryset = Withdrawal.objects.select_related('user', 'processed_by', 'payment')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'user']
    ordering_fields = ['created_at', 'amount', 'processed_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'create':
            return WithdrawalCreateSerializer
        return WithdrawalSerializer

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Non-admin users see only their own withdrawals
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset

    def perform_create(self, serializer):
        """Create a new withdrawal request"""
        # Calculate fee (2% by default)
        amount = serializer.validated_data['amount']
        fee = int(amount * 0.02)  # 2% withdrawal fee

        # Set user to current user
        serializer.save(user=self.request.user, fee=fee)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        """Approve withdrawal request (admin only)"""
        withdrawal = self.get_object()
        tracking_code = request.data.get('tracking_code', '')

        try:
            withdrawal.approve(request.user, tracking_code=tracking_code)
            return Response({
                'message': 'درخواست برداشت تایید شد',
                'withdrawal': WithdrawalSerializer(withdrawal).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None):
        """Reject withdrawal request (admin only)"""
        withdrawal = self.get_object()
        reason = request.data.get('reason', '')

        if not reason:
            return Response(
                {'error': 'دلیل رد الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            withdrawal.reject(request.user, reason=reason)
            return Response({
                'message': 'درخواست برداشت رد شد',
                'withdrawal': WithdrawalSerializer(withdrawal).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        """Complete withdrawal (admin only)"""
        withdrawal = self.get_object()
        reference_number = request.data.get('reference_number', '')

        try:
            withdrawal.complete(reference_number=reference_number)
            return Response({
                'message': 'برداشت تکمیل شد',
                'withdrawal': WithdrawalSerializer(withdrawal).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel withdrawal"""
        withdrawal = self.get_object()

        # Check if user owns this withdrawal or is admin
        if withdrawal.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'شما مجاز به این عملیات نیستید'},
                status=status.HTTP_403_FORBIDDEN
            )

        reason = request.data.get('reason', '')

        try:
            withdrawal.cancel(by_admin=request.user.is_staff, reason=reason)
            return Response({
                'message': 'درخواست برداشت لغو شد',
                'withdrawal': WithdrawalSerializer(withdrawal).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing transaction history"""

    queryset = Transaction.objects.select_related('user', 'payment', 'tournament')
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['transaction_type', 'user']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Non-admin users see only their own transactions
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary for current user"""
        user = request.user
        transactions = Transaction.objects.filter(user=user)

        total_credits = transactions.filter(transaction_type='credit').aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_debits = transactions.filter(transaction_type='debit').aggregate(
            total=Sum('amount')
        )['total'] or 0

        return Response({
            'total_credits': total_credits,
            'total_debits': total_debits,
            'current_balance': user.wallet_balance,
            'transaction_count': transactions.count()
        })


class CouponViewSet(viewsets.ModelViewSet):
    """ViewSet for managing coupons"""

    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'discount_type']
    search_fields = ['code', 'description']
    ordering_fields = ['created_at', 'valid_until']
    ordering = ['-created_at']

    def get_permissions(self):
        """Only admins can create, update, delete coupons"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Create a new coupon"""
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def validate_coupon(self, request):
        """Validate a coupon code"""
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        amount = serializer.validated_data.get('amount', 0)
        tournament_id = serializer.validated_data.get('tournament_id')

        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return Response(
                {'error': 'کوپن یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get tournament if provided
        tournament = None
        if tournament_id:
            from apps.tournaments.models import Tournament
            tournament = get_object_or_404(Tournament, id=tournament_id)

        # Check if user can use coupon
        can_use, message = coupon.can_use(request.user, tournament, amount)

        if not can_use:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )

        discount = coupon.calculate_discount(amount) if amount else 0

        return Response({
            'valid': True,
            'discount_amount': discount,
            'final_amount': amount - discount if amount else 0,
            'coupon': CouponSerializer(coupon).data
        })


class CouponUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing coupon usage history"""

    queryset = CouponUsage.objects.select_related('coupon', 'user', 'payment')
    serializer_class = CouponUsageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['coupon', 'user']
    ordering_fields = ['used_at']
    ordering = ['-used_at']

    def get_queryset(self):
        """Filter queryset based on user"""
        user = self.request.user
        queryset = super().get_queryset()

        # Non-admin users see only their own coupon usages
        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset
