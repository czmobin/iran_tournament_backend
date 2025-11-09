from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView,
    UserProfileView, ChangePasswordView, UserStatsView,
    UpdateProfileView, UploadProfilePictureView, SendOTPView,
    ValidateOTPView, VerifyPhoneView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # JWT Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/update/', UpdateProfileView.as_view(), name='profile_update'),
    path('profile/picture/', UploadProfilePictureView.as_view(), name='profile_picture'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('stats/', UserStatsView.as_view(), name='stats'),
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('validate-otp/', ValidateOTPView.as_view(), name='validate_otp'),
    path('verify/', VerifyPhoneView.as_view(), name='verify'),
]