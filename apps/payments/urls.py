from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet, WithdrawalViewSet, TransactionViewSet,
    CouponViewSet, CouponUsageViewSet
)

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawal')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'coupons', CouponViewSet, basename='coupon')
router.register(r'coupon-usages', CouponUsageViewSet, basename='coupon-usage')

urlpatterns = router.urls
