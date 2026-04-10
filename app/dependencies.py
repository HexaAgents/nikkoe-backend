import httpx

from app.config import settings
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

_http_client = httpx.Client(http2=False, timeout=120, limits=httpx.Limits(max_connections=20))
_options = SyncClientOptions(httpx_client=_http_client)

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, options=_options)
supabase_auth: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
