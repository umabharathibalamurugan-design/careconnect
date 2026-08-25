from pathlib import Path
from django.http import FileResponse
from django.conf import settings


def service_worker(request):
    path = Path(settings.BASE_DIR) / 'frontend' / 'service-worker.js'
    return FileResponse(open(path, 'rb'), content_type='application/javascript')
