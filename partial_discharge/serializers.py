# serializers.py
from rest_framework import serializers
from .models import dynamic_routes

class RoutesSerializer(serializers.ModelSerializer):
    class Meta:
        model = dynamic_routes
        fields = ['id', 'path', 'component', 'children_path','children_component','children_name','children_meta_title','children_meta_icon']
