from rest_framework import serializers
from .models import Tool, License, EnvConfig

class EnvConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvConfig
        fields = ['id','name','vars','is_default']

class ToolSerializer(serializers.ModelSerializer):
    envs = EnvConfigSerializer(many=True, read_only=True)
    class Meta:
        model = Tool
        fields = ['id','name','display_name','type','launcher_cmd','env_template','icon','license_server_id','envs']

class LicenseSerializer(serializers.ModelSerializer):
    holders = serializers.SerializerMethodField()
    class Meta:
        model = License
        fields = ['id','tool','license_key','pool_size','expiry_date','server_info','status','holders']

    def get_holders(self, obj):
        return [alloc.user.username for alloc in obj.allocations.filter(status='active') if alloc.user]
