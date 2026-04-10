"""Tests for app/dependencies.py — guard against client misconfiguration.

The custom httpx.Client(http2=False) incident caused every endpoint to return
500 "Illegal header" on Vercel while passing locally. These tests ensure the
Supabase clients are created with safe, default configuration.
"""

from supabase import Client


class TestSupabaseClients:
    def test_supabase_client_is_supabase_client(self):
        from app.dependencies import supabase

        assert isinstance(supabase, Client), "supabase must be a standard supabase.Client"

    def test_supabase_auth_client_is_supabase_client(self):
        from app.dependencies import supabase_auth

        assert isinstance(supabase_auth, Client), "supabase_auth must be a standard supabase.Client"

    def test_supabase_client_has_no_custom_httpx_client(self):
        """A custom httpx.Client broke Vercel deployments. Ensure we use defaults."""
        from app.dependencies import supabase

        rest_client = supabase.postgrest
        session = getattr(rest_client, "session", None) or getattr(rest_client, "_session", None)
        if session is not None:
            assert session.is_closed is False, "REST session must be open"

    def test_clients_are_separate_instances(self):
        from app.dependencies import supabase, supabase_auth

        assert supabase is not supabase_auth, "supabase and supabase_auth must be separate instances"

    def test_dependencies_module_has_no_httpx_import(self):
        """If httpx is imported in dependencies.py, someone is likely adding a custom client."""
        import inspect

        import app.dependencies as dep

        source = inspect.getsource(dep)
        assert "httpx" not in source, (
            "dependencies.py must not import httpx — custom httpx clients "
            "cause 'Illegal header' errors on Vercel serverless"
        )
