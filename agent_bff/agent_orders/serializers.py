from rest_framework import serializers


class AssignOrderSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=64, required=True)
    agent_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    actor_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class StartProcessingSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateStatusSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(
        choices=['ASSIGNED', 'PROCESSING', 'COMPLETED', 'CANCELLED'],
        required=True
    )
    actor_id = serializers.CharField(max_length=64, required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CompleteOrderSerializer(serializers.Serializer):
    agent_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

