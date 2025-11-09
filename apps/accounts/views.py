from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.core.cache import cache

from .tasks import send_sms_otp
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    ChangePasswordSerializer, UserProfileSerializer,
    UpdateProfileSerializer
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    User Registration
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'ثبت‌نام با موفقیت انجام شد.'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    User Login
    POST /api/auth/login/
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'ورود با موفقیت انجام شد.'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    User Logout
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'خروج با موفقیت انجام شد.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'خطا در خروج از سیستم.'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get/Update User Profile
    GET/PUT/PATCH /api/auth/profile/
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    Change Password
    POST /api/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'رمز عبور با موفقیت تغییر کرد.'
        }, status=status.HTTP_200_OK)


class UserStatsView(APIView):
    """
    Get User Statistics
    GET /api/auth/stats/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if not hasattr(user, 'stats'):
            from .models import UserStats
            UserStats.objects.create(user=user)
        
        stats = user.stats
        
        return Response({
            'tournaments_played': stats.tournaments_played,
            'tournaments_won': stats.tournaments_won,
            'total_matches': stats.total_matches,
            'matches_won': stats.matches_won,
            'win_rate': float(stats.win_rate),
            'total_earnings': float(stats.total_earnings),
            'ranking': stats.ranking
        })

class UpdateProfileView(generics.UpdateAPIView):
    """
    Update User Profile
    PUT/PATCH /api/auth/profile/update/
    """
    serializer_class = UpdateProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'user': UserProfileSerializer(instance).data,
            'message': 'پروفایل با موفقیت بروزرسانی شد.'
        })


class UploadProfilePictureView(APIView):
    """
    Upload Profile Picture
    POST /api/auth/profile/picture/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if 'profile_picture' not in request.FILES:
            return Response({
                'error': 'تصویر انتخاب نشده است.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_picture = request.FILES['profile_picture']
        
        # Validate file size (max 5MB)
        if profile_picture.size > 5 * 1024 * 1024:
            return Response({
                'error': 'حجم تصویر نباید بیشتر از 5 مگابایت باشد.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file type
        if not profile_picture.content_type.startswith('image/'):
            return Response({
                'error': 'فایل باید از نوع تصویر باشد.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete old picture if exists
        if user.profile_picture:
            user.profile_picture.delete(save=False)
        
        # Save new picture
        user.profile_picture = profile_picture
        user.save()
        
        return Response({
            'profile_picture': user.profile_picture.url,
            'message': 'تصویر پروفایل با موفقیت آپلود شد.'
        })


class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get("phone_number")

        if not phone_number:
            return Response({
                'error': "شماره تلفن وارد نشده است."
            }, status=status.HTTP_400_BAD_REQUEST)

        if cache.get(f"otp_cooldown_{phone_number}"):
            return Response({
                'error': "لطفاً چند ثانیه صبر کنید و دوباره تلاش کنید."
            }, status=status.HTTP_400_BAD_REQUEST)

        task = send_sms_otp.delay(phone_number)
        cache.set(f"otp_task_{phone_number}", task.id, timeout=120)
        cache.set(f"otp_cooldown_{phone_number}", True, timeout=5)


        return Response({
            'task_id': task.id,
            'message': 'کد ورود در حال ارسال است، لطفاً چند لحظه صبر کنید.'
        })

class ValidateOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get("phone_number")
        otp = request.data.get("otp")

        if not phone_number or not otp:
            return Response({
                'error': "شماره تلفن یا کد OTP وارد نشده است."
            }, status=status.HTTP_400_BAD_REQUEST)

        task_id = cache.get(f"otp_task_{phone_number}")
        if not task_id:
            return Response({
                'error': "کد OTP یافت نشد. لطفاً مجدداً درخواست دهید."
                }, status=status.HTTP_400_BAD_REQUEST)
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)

        if not task_result.ready():
            return Response({
                'error': "کد هنوز آماده نیست، لطفاً چند لحظه دیگر دوباره امتحان کنید."
                }, status=status.HTTP_400_BAD_REQUEST)
        
        otp_response = task_result.result

        if not otp_response or otp_response["status_code"] != 200:
            return Response({
                'error': "خطایی در SMS Provider رخ داده است."
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
        otp_code = otp_response["response"]["code"]

        if otp_code != otp:
            return Response({
                'error': "کد OTP نادرست است."
                }, status=status.HTTP_400_BAD_REQUEST)

        cache.set(f"otp_valid_{phone_number}", True, timeout=300)

        return Response({
            'is_valid': True,
            'message': 'کد صحیح است.'
        })

class VerifyPhoneView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get("phone_number")

        if not phone_number:
            return Response({
                'error': "شماره تلفن وارد نشده است."
            }, status=status.HTTP_400_BAD_REQUEST)

        task_id = cache.get(f"otp_valid_{phone_number}")
        if not task_id:
            return Response({
                'error': "کد OTP یافت نشد. لطفاً مجدداً درخواست دهید."
                }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(phone_number=phone_number)
        user.is_verified = True
        user.save()

        return Response({
            'is_verified': True,
            'message': 'کد صحیح است.'
        })
