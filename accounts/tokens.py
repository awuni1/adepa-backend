from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class AdepaTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["org"] = str(user.organisation_id) if user.organisation_id else None
        token["name"] = user.get_full_name()
        return token
