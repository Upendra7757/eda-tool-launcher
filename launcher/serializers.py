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

from rest_framework import serializers
from .models import SlideItem, RunArtifact


class SlideItemCreateSerializer(serializers.ModelSerializer):
    artifact_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = SlideItem
        fields = [
            "artifact_id",
            "item_type",
            "config",
        ]

    def validate(self, data):
        slide = self.context["slide"]
        artifact_id = data["artifact_id"]

        try:
            artifact = RunArtifact.objects.get(id=artifact_id)
        except RunArtifact.DoesNotExist:
            raise serializers.ValidationError("Invalid artifact")

        # 🔒 IMPORTANT: enforce same ToolRun
        if artifact.run_id != slide.presentation.run_id:
            raise serializers.ValidationError(
                "Artifact does not belong to this presentation's run"
            )

        data["artifact"] = artifact
        return data

    def create(self, validated_data):
        validated_data.pop("artifact_id")

        slide = self.context["slide"]
        request = self.context["request"]

        return SlideItem.objects.create(
            slide=slide,
            added_by=request.user if request.user.is_authenticated else None,
            **validated_data
        )
