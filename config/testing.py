from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import override_settings
from django.test.runner import DiscoverRunner


class IsolatedMediaDiscoverRunner(DiscoverRunner):
    """Route every test upload to a disposable directory.

    Individual test classes no longer need to remember to protect the
    operational ``media/`` tree. Cleanup runs even when the suite fails.
    """

    def setup_test_environment(self, **kwargs):
        self._media_directory = TemporaryDirectory(prefix="vimer-test-media-")
        self._media_override = override_settings(
            MEDIA_ROOT=Path(self._media_directory.name)
        )
        self._media_override.enable()
        try:
            return super().setup_test_environment(**kwargs)
        except Exception:
            self._media_override.disable()
            self._media_directory.cleanup()
            raise

    def teardown_test_environment(self, **kwargs):
        try:
            return super().teardown_test_environment(**kwargs)
        finally:
            self._media_override.disable()
            self._media_directory.cleanup()
