from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Payment, Withdrawal, Transaction, Coupon, CouponUsage, PaymentGatewayConfig
from apps.accounts.serializers import UserBasicSerializer

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""

    user_username = serializers.CharField(source='user.username', read_only=True)
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'user', 'user_username',
            'payment_type', 'amount', 'fee', 'final_amount',
            'status', 'gateway', 'gateway_transaction_id',
            'gateway_tracking_code', 'gateway_response',
            'tournament', 'tournament_title',
            'card_number', 'card_holder_name',
            'description', 'admin_note', 'ip_address',
            'retry_count', 'created_at', 'updated_at',
            'completed_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'status', 'gateway_transaction_id',
            'gateway_tracking_code', 'gateway_response', 'gateway_callback_data',
            'card_number', 'card_holder_name', 'retry_count',
            'created_at', 'updated_at', 'completed_at'
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """Minimal serializer for payment listings"""

    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'user', 'user_username',
            'payment_type', 'amount', 'status', 'gateway',
            'created_at', 'completed_at'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a payment"""

    class Meta:
        model = Payment
        fields = [
            'payment_type', 'amount', 'gateway', 'tournament', 'description'
        ]

    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError('مبلغ باید بیشتر از صفر باشد')
        return value


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for Withdrawal model"""

    user_username = serializers.CharField(source='user.username', read_only=True)
    processed_by_username = serializers.CharField(source='processed_by.username', read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            'id', 'user', 'user_username', 'amount', 'fee', 'final_amount',
            'status', 'bank_name', 'bank_account_number',
            'bank_card_number', 'account_holder_name', 'sheba_number',
            'tracking_code', 'reference_number',
            'user_note', 'admin_note', 'rejection_reason',
            'processed_by', 'processed_by_username', 'payment',
            'created_at', 'processed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'tracking_code', 'reference_number',
            'admin_note', 'rejection_reason', 'processed_by',
            'payment', 'processed_at', 'completed_at', 'created_at'
        ]


class WithdrawalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a withdrawal request"""

    class Meta:
        model = Withdrawal
        fields = [
            'amount', 'bank_name', 'bank_account_number',
            'bank_card_number', 'account_holder_name',
            'sheba_number', 'user_note'
        ]

    def validate_amount(self, value):
        """Validate withdrawal amount"""
        if value < 10000:
            raise serializers.ValidationError('حداقل مبلغ برداشت 10,000 تومان است')
        return value

    def validate_bank_card_number(self, value):
        """Validate card number"""
        if value and len(value) != 16:
            raise serializers.ValidationError('شماره کارت باید 16 رقم باشد')
        if value and not value.isdigit():
            raise serializers.ValidationError('شماره کارت فقط باید شامل اعداد باشد')
        return value

    def validate_sheba_number(self, value):
        """Validate sheba number"""
        if value:
            if not value.startswith('IR'):
                raise serializers.ValidationError('شماره شبا باید با IR شروع شود')
            if len(value) != 26:
                raise serializers.ValidationError('شماره شبا باید 26 کاراکتر باشد')
        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""

    user_username = serializers.CharField(source='user.username', read_only=True)
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'user_username', 'transaction_type',
            'amount', 'balance_before', 'balance_after',
            'description', 'payment', 'tournament', 'tournament_title',
            'created_at'
        ]
        read_only_fields = ['id', 'balance_before', 'balance_after', 'created_at']


class CouponSerializer(serializers.ModelSerializer):
    """Serializer for Coupon model"""

    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'discount_type', 'discount_value',
            'max_discount', 'min_purchase', 'max_uses',
            'max_uses_per_user', 'current_uses', 'usage_count',
            'valid_from', 'valid_until', 'first_purchase_only',
            'status', 'description', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_uses', 'created_at', 'updated_at']

    def get_usage_count(self, obj):
        """Get number of times coupon was used"""
        return obj.current_uses


class CouponValidateSerializer(serializers.Serializer):
    """Serializer for validating a coupon"""

    code = serializers.CharField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=0, required=False)
    tournament_id = serializers.IntegerField(required=False)


class CouponUsageSerializer(serializers.ModelSerializer):
    """Serializer for CouponUsage model"""

    coupon_code = serializers.CharField(source='coupon.code', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon', 'coupon_code', 'user', 'user_username',
            'payment', 'discount_amount', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


class PaymentGatewayConfigSerializer(serializers.ModelSerializer):
    """Serializer for PaymentGatewayConfig model"""

    class Meta:
        model = PaymentGatewayConfig
        fields = [
            'id', 'gateway', 'is_active', 'min_amount', 'max_amount',
            'fee_percentage', 'fixed_fee', 'priority', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
