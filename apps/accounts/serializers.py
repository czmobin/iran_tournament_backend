from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 
            'last_name', 'phone_number', 'profile_picture',
            'wallet_balance', 'clash_royale_tag', 'is_verified',
            'created_at'
        ]
        read_only_fields = ['id', 'wallet_balance', 'is_verified', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='تکرار رمز عبور'
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone_number'
        ]
    
    def validate(self, attrs):
        """Check that passwords match"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "رمز عبور و تکرار آن مطابقت ندارند."
            })
        return attrs
    
    def validate_email(self, value):
        """Check email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً استفاده شده است.")
        return value
    
    def validate_username(self, value):
        """Check username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("این نام کاربری قبلاً استفاده شده است.")
        return value
    
    def create(self, validated_data):
        """Create user"""
        validated_data.pop('password2')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', None)
        )
        
        # Create user stats
        from .models import UserStats
        UserStats.objects.create(user=user)
        
        # Create notification preferences
        from apps.notifications.models import NotificationPreference
        NotificationPreference.objects.create(user=user)
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate credentials"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Try to authenticate
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError(
                    'نام کاربری یا رمز عبور اشتباه است.',
                    code='authorization'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'حساب کاربری شما غیرفعال است.',
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                'لطفاً نام کاربری و رمز عبور را وارد کنید.',
                code='authorization'
            )
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate passwords"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "رمز عبور جدید و تکرار آن مطابقت ندارند."
            })
        return attrs
    
    def validate_old_password(self, value):
        """Check old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("رمز عبور فعلی اشتباه است.")
        return value
    
    def save(self, **kwargs):
        """Change password"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with stats"""
    
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'wallet_balance',
            'clash_royale_tag', 'is_verified', 'created_at',
            'stats'
        ]
        read_only_fields = ['id', 'username', 'wallet_balance', 'is_verified', 'created_at']
    
    def get_stats(self, obj):
        """Get user statistics"""
        if hasattr(obj, 'stats'):
            return {
                'tournaments_played': obj.stats.tournaments_played,
                'tournaments_won': obj.stats.tournaments_won,
                'total_matches': obj.stats.total_matches,
                'matches_won': obj.stats.matches_won,
                'win_rate': float(obj.stats.win_rate),
                'total_earnings': float(obj.stats.total_earnings),
                'ranking': obj.stats.ranking
            }
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number',
            'clash_royale_tag', 'profile_picture'
        ]
    
    def validate_phone_number(self, value):
        if value:
            # Check format
            import re
            if not re.match(r'^09\d{9}$', value):
                raise serializers.ValidationError("شماره موبایل باید به فرمت 09123456789 باشد")
            
            # Check uniqueness (exclude current user)
            user = self.context['request'].user
            if User.objects.exclude(id=user.id).filter(phone_number=value).exists():
                raise serializers.ValidationError("این شماره موبایل قبلاً استفاده شده است")
        
        return value
    
    def validate_clash_royale_tag(self, value):
        if value:
            # Remove # if exists
            value = value.replace('#', '')
            
            # Check format (letters and numbers)
            import re
            if not re.match(r'^[A-Z0-9]{3,15}$', value.upper()):
                raise serializers.ValidationError("تگ کلش رویال نامعتبر است")
            
            # Add # back
            value = f"#{value.upper()}"
            
            # Check uniqueness
            user = self.context['request'].user
            if User.objects.exclude(id=user.id).filter(clash_royale_tag=value).exists():
                raise serializers.ValidationError("این تگ قبلاً استفاده شده است")
        
        return value