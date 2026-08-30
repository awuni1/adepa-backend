from accounts.permissions import IsHRorAdmin
from accounts.views import OrgScopedViewSet

from .models import Person
from .serializers import PersonSerializer


class PersonViewSet(OrgScopedViewSet):
    """Read/administer the shared Person record. Recruitment, employees,
    attendance, payroll and performance all reference this queryset directly
    rather than duplicating it (§1)."""

    serializer_class = PersonSerializer
    permission_classes = [IsHRorAdmin]
    queryset = Person.objects.all()
    filterset_fields = ["lifecycle_stage"]
    search_fields = ["first_name", "last_name", "email"]
