import os
from typing import Union

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound


def swagger_yaml(
    request: HttpRequest,
) -> Union[HttpResponse, HttpResponseNotFound]:
    with open(
        os.path.join(settings.BASE_DIR, "wallets/docs/swagger.yml"), "r"
    ) as yaml_file:
        return HttpResponse(yaml_file.read(), content_type="application/yaml")
