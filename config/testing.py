from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import override_settings
from django.test.runner import DiscoverRunner
from django.db import connections


class IsolatedMediaDiscoverRunner(DiscoverRunner):
    """Aislar medios y bases SQLite de pruebas en un directorio temporal.

    Una base SQLite en archivo permite probar escritores concurrentes con
    conexiones independientes y su espera real, sin usar datos operativos.
    La limpieza se ejecuta incluso si la suite falla.
    """

    def setup_test_environment(self, **kwargs):
        self._media_directory = TemporaryDirectory(prefix="vimer-test-media-")
        self._media_override = override_settings(
            MEDIA_ROOT=Path(self._media_directory.name)
        )
        self._media_override.enable()
        self._sqlite_test_names = {}
        for alias in connections:
            database = connections[alias].settings_dict
            if database["ENGINE"] == "django.db.backends.sqlite3" and not database["TEST"]["NAME"]:
                self._sqlite_test_names[alias] = database["TEST"]["NAME"]
                database["TEST"]["NAME"] = str(Path(self._media_directory.name) / f"{alias}.sqlite3")
        try:
            return super().setup_test_environment(**kwargs)
        except Exception:
            for alias, name in self._sqlite_test_names.items():
                connections[alias].settings_dict["TEST"]["NAME"] = name
            self._media_override.disable()
            self._media_directory.cleanup()
            raise

    def teardown_test_environment(self, **kwargs):
        try:
            return super().teardown_test_environment(**kwargs)
        finally:
            for alias, name in self._sqlite_test_names.items():
                connections[alias].settings_dict["TEST"]["NAME"] = name
            self._media_override.disable()
            self._media_directory.cleanup()
