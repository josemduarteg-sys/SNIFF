from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Rol, Usuario


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = [
            'id',
            'nombre',
            'descripcion',
            'estado',
            'fecha_creacion',
        ]


class UsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'nombre_completo',
            'correo',
            'email',
            'rol',
            'rol_nombre',
            'estado',
            'is_active',
            'is_staff',
            'is_superuser',
            'ultimo_acceso',
            'date_joined',
            'password',
        ]
        read_only_fields = [
            'id',
            'ultimo_acceso',
            'date_joined',
            'nombre_completo',
            'rol_nombre',
            'is_superuser',
        ]

    def get_nombre_completo(self, obj):
        nombre = obj.get_full_name()
        return nombre if nombre else obj.username

    def validate(self, attrs):
        correo = attrs.get('correo')
        email = attrs.get('email')

        if correo and not email:
            attrs['email'] = correo

        if email and not correo:
            attrs['correo'] = email

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)

        if not validated_data.get('email') and validated_data.get('correo'):
            validated_data['email'] = validated_data['correo']

        if not validated_data.get('correo') and validated_data.get('email'):
            validated_data['correo'] = validated_data['email']

        usuario = Usuario(**validated_data)

        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()

        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        if validated_data.get('correo') and not validated_data.get('email'):
            validated_data['email'] = validated_data['correo']

        if validated_data.get('email') and not validated_data.get('correo'):
            validated_data['correo'] = validated_data['email']

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UsuarioActualSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'nombre_completo',
            'correo',
            'email',
            'rol',
            'rol_nombre',
            'estado',
            'is_active',
            'is_staff',
            'is_superuser',
            'ultimo_acceso',
        ]
        read_only_fields = [
            'id',
            'username',
            'rol',
            'rol_nombre',
            'estado',
            'is_active',
            'is_staff',
            'is_superuser',
            'ultimo_acceso',
        ]

    def get_nombre_completo(self, obj):
        nombre = obj.get_full_name()
        return nombre if nombre else obj.username

    def validate(self, attrs):
        correo = attrs.get('correo')
        email = attrs.get('email')

        if correo and not email:
            attrs['email'] = correo

        if email and not correo:
            attrs['correo'] = email

        return attrs


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True)
    password_confirmacion = serializers.CharField(write_only=True)

    def validate(self, attrs):
        usuario = self.context['request'].user

        password_actual = attrs.get('password_actual')
        password_nuevo = attrs.get('password_nuevo')
        password_confirmacion = attrs.get('password_confirmacion')

        if not usuario.check_password(password_actual):
            raise serializers.ValidationError({
                'password_actual': 'La contraseña actual no es correcta.'
            })

        if password_nuevo != password_confirmacion:
            raise serializers.ValidationError({
                'password_confirmacion': 'La confirmación no coincide con la nueva contraseña.'
            })

        validate_password(password_nuevo, usuario)

        return attrs

    def save(self, **kwargs):
        usuario = self.context['request'].user
        usuario.set_password(self.validated_data['password_nuevo'])
        usuario.save()
        return usuario