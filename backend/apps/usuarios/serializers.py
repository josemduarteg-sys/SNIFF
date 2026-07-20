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
        read_only_fields = ['id', 'fecha_creacion']


class UsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(
        source='rol.nombre',
        read_only=True
    )

    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'correo',
            'email',
            'rol',
            'rol_nombre',
            'estado',
            'is_active',
            'is_staff',
            'ultimo_acceso',
            'date_joined',
        ]
        read_only_fields = [
            'id',
            'ultimo_acceso',
            'date_joined',
        ]


class UsuarioCrearSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'correo',
            'email',
            'rol',
            'estado',
            'is_active',
            'is_staff',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance
    
