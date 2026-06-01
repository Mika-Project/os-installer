"""
Tests for PMParu and PMYay classes introduced in:
  - 0001-support-paru.patch
  - 0001-support-yay.patch

These classes are patches applied to calamares src/modules/packages/main.py.
Since the actual calamares source is not present in this repo (it is downloaded
and built by makepkg), the classes are replicated here with the libcalamares
framework replaced by mocks, so the command-building and retry logic can be
tested independently.
"""

import subprocess
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Minimal stubs for the calamares framework globals used by the patched code
# ---------------------------------------------------------------------------

class _MockJob:
    def __init__(self, config=None):
        self.configuration = config if config is not None else {}
        self.setprogress = MagicMock()


class _MockUtils:
    def __init__(self):
        self.target_env_process_output = MagicMock()
        self.debug = MagicMock()
        self.warning = MagicMock()


# Module-level globals mirrored from calamares packages/main.py
completed_packages = 3
total_packages = 10
custom_status_message = ""


# ---------------------------------------------------------------------------
# PMParu – replicated from 0001-support-paru.patch
# (logic is verbatim from the patch; only the framework dependencies are mocked)
# ---------------------------------------------------------------------------

class PackageManager:
    """Minimal base class (the real one is in calamares main.py)."""
    pass


def _make_pmparu_class(libcalamares_mock, subprocess_mod):
    """
    Build a PMParu class that uses the supplied libcalamares mock and
    subprocess module instead of the real ones, so tests can run without
    the calamares framework installed.
    """

    class PMParu(PackageManager):
        backend = "paru"

        def __init__(self):
            import re

            re.compile(r"^\((\d+)/(\d+)\)")  # progress_match (kept for fidelity)

            self.in_package_changes = False

            def line_cb(line):
                global custom_status_message
                if line.startswith(":: "):
                    self.in_package_changes = "package" in line or "hooks" in line
                else:
                    if self.in_package_changes and line.endswith("...\n"):
                        custom_status_message = "paru: " + line.strip()
                        libcalamares_mock.job.setprogress(self.progress_fraction)
                libcalamares_mock.utils.debug(line)

            self.line_cb = line_cb

            paru = libcalamares_mock.job.configuration.get("paru", None)
            if paru is None:
                paru = dict()
            if type(paru) is not dict:
                libcalamares_mock.utils.warning(
                    "Job configuration *paru* will be ignored."
                )
                paru = dict()
            self.paru_num_retries = paru.get("num_retries", 0)
            self.paru_disable_timeout = paru.get("disable_download_timeout", False)
            self.paru_needed_only = paru.get("needed_only", False)

        def reset_progress(self):
            self.in_package_changes = False
            self.progress_fraction = completed_packages * 1.0 / total_packages

        def run_paru(self, command, callback=False):
            paru_count = 0
            while paru_count <= self.paru_num_retries:
                paru_count += 1
                try:
                    if False:  # callback: (disabled in the patch)
                        libcalamares_mock.utils.target_env_process_output(
                            command, self.line_cb
                        )
                    else:
                        libcalamares_mock.utils.target_env_process_output(command)
                    return
                except subprocess_mod.CalledProcessError:
                    if paru_count <= self.paru_num_retries:
                        pass
                    else:
                        raise

        def install(self, pkgs, from_local=False):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            command = ["sudo", "-E", "-u", "nobody", "paru"]
            if from_local:
                command.append("-U")
            else:
                command.append("-S")
            command.append("--noconfirm")
            command.append("--noprogressbar")
            if self.paru_needed_only is True:
                command.append("--needed")
            if self.paru_disable_timeout is True:
                command.append("--disable-download-timeout")
            command += pkgs

            self.reset_progress()
            self.run_paru(command, True)

        def remove(self, pkgs):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            self.reset_progress()
            self.run_paru(
                ["sudo", "-E", "-u", "nobody", "paru", "-Rs", "--noconfirm"] + pkgs,
                True,
            )

        def update_db(self):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            self.run_paru(["sudo", "-E", "-u", "nobody", "paru", "-Sy"])

        def update_system(self):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            command = ["sudo", "-E", "-u", "nobody", "paru", "-Su", "--noconfirm"]
            if self.paru_disable_timeout is True:
                command.append("--disable-download-timeout")
            self.run_paru(command)

    return PMParu


def _make_pmyay_class(libcalamares_mock, subprocess_mod):
    """
    Build a PMYay class that uses the supplied libcalamares mock and
    subprocess module instead of the real ones.
    """

    class PMYay(PackageManager):
        backend = "yay"

        def __init__(self):
            import re

            re.compile(r"^\((\d+)/(\d+)\)")  # progress_match (kept for fidelity)

            self.in_package_changes = False

            def line_cb(line):
                global custom_status_message
                if line.startswith(":: "):
                    self.in_package_changes = "package" in line or "hooks" in line
                else:
                    if self.in_package_changes and line.endswith("...\n"):
                        custom_status_message = "yay: " + line.strip()
                        libcalamares_mock.job.setprogress(self.progress_fraction)
                libcalamares_mock.utils.debug(line)

            self.line_cb = line_cb

            yay = libcalamares_mock.job.configuration.get("yay", None)
            if yay is None:
                yay = dict()
            if type(yay) is not dict:
                libcalamares_mock.utils.warning(
                    "Job configuration *yay* will be ignored."
                )
                yay = dict()
            self.yay_num_retries = yay.get("num_retries", 0)
            self.yay_disable_timeout = yay.get("disable_download_timeout", False)
            self.yay_needed_only = yay.get("needed_only", False)

        def reset_progress(self):
            self.in_package_changes = False
            self.progress_fraction = completed_packages * 1.0 / total_packages

        def run_yay(self, command, callback=False):
            yay_count = 0
            while yay_count <= self.yay_num_retries:
                yay_count += 1
                try:
                    if False:  # callback: (disabled in the patch)
                        libcalamares_mock.utils.target_env_process_output(
                            command, self.line_cb
                        )
                    else:
                        libcalamares_mock.utils.target_env_process_output(command)
                    return
                except subprocess_mod.CalledProcessError:
                    if yay_count <= self.yay_num_retries:
                        pass
                    else:
                        raise

        def install(self, pkgs, from_local=False):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            command = ["sudo", "-E", "-u", "nobody", "yay"]
            if from_local:
                command.append("-U")
            else:
                command.append("-S")
            command.append("--noconfirm")
            command.append("--noprogressbar")
            if self.yay_needed_only is True:
                command.append("--needed")
            if self.yay_disable_timeout is True:
                command.append("--disable-download-timeout")
            command += pkgs

            self.reset_progress()
            self.run_yay(command, True)

        def remove(self, pkgs):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            self.reset_progress()
            self.run_yay(
                ["sudo", "-E", "-u", "nobody", "yay", "-Rs", "--noconfirm"] + pkgs,
                True,
            )

        def update_db(self):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            self.run_yay(["sudo", "-E", "-u", "nobody", "yay", "-Sy"])

        def update_system(self):
            import os
            os.environ["PWD"] = "/var/cache"
            os.environ["XDG_CACHE_HOME"] = "/var/cache"

            command = ["sudo", "-E", "-u", "nobody", "yay", "-Su", "--noconfirm"]
            if self.yay_disable_timeout is True:
                command.append("--disable-download-timeout")
            self.run_yay(command)

    return PMYay


# ---------------------------------------------------------------------------
# Helper to build a libcalamares mock with a given job configuration dict
# ---------------------------------------------------------------------------

def _make_libcalamares(config=None):
    lc = MagicMock()
    lc.job = _MockJob(config if config is not None else {})
    lc.utils = _MockUtils()
    return lc


# ---------------------------------------------------------------------------
# Tests – PMParu
# ---------------------------------------------------------------------------

class TestPMParuBackend(unittest.TestCase):
    def test_backend_attribute(self):
        lc = _make_libcalamares()
        PMParu = _make_pmparu_class(lc, subprocess)
        self.assertEqual(PMParu.backend, "paru")


class TestPMParuInit(unittest.TestCase):
    """Tests for PMParu.__init__ configuration parsing."""

    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        return PMParu(), lc

    def test_default_config_when_key_absent(self):
        pm, _ = self._make({})
        self.assertEqual(pm.paru_num_retries, 0)
        self.assertFalse(pm.paru_disable_timeout)
        self.assertFalse(pm.paru_needed_only)

    def test_default_config_when_key_is_none(self):
        # configuration.get("paru") returns None → treated same as missing key
        pm, _ = self._make({"paru": None})
        self.assertEqual(pm.paru_num_retries, 0)
        self.assertFalse(pm.paru_disable_timeout)
        self.assertFalse(pm.paru_needed_only)

    def test_non_dict_paru_config_is_ignored_with_warning(self):
        pm, lc = self._make({"paru": "bad-value"})
        lc.utils.warning.assert_called_once()
        warning_msg = lc.utils.warning.call_args[0][0]
        self.assertIn("paru", warning_msg)
        # Falls back to defaults
        self.assertEqual(pm.paru_num_retries, 0)
        self.assertFalse(pm.paru_disable_timeout)
        self.assertFalse(pm.paru_needed_only)

    def test_custom_num_retries(self):
        pm, _ = self._make({"paru": {"num_retries": 3}})
        self.assertEqual(pm.paru_num_retries, 3)

    def test_disable_download_timeout(self):
        pm, _ = self._make({"paru": {"disable_download_timeout": True}})
        self.assertTrue(pm.paru_disable_timeout)

    def test_needed_only(self):
        pm, _ = self._make({"paru": {"needed_only": True}})
        self.assertTrue(pm.paru_needed_only)

    def test_in_package_changes_initialised_false(self):
        pm, _ = self._make()
        self.assertFalse(pm.in_package_changes)

    def test_line_cb_is_callable(self):
        pm, _ = self._make()
        self.assertTrue(callable(pm.line_cb))


class TestPMParuResetProgress(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        return PMParu(), lc

    def test_resets_in_package_changes(self):
        pm, _ = self._make()
        pm.in_package_changes = True
        pm.reset_progress()
        self.assertFalse(pm.in_package_changes)

    def test_sets_progress_fraction(self):
        pm, _ = self._make()
        pm.reset_progress()
        expected = completed_packages / total_packages
        self.assertAlmostEqual(pm.progress_fraction, expected)


class TestPMParuRunParu(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        return PMParu(), lc

    def test_calls_target_env_process_output(self):
        pm, lc = self._make()
        pm.run_paru(["paru", "-S", "foo"])
        lc.utils.target_env_process_output.assert_called_once_with(["paru", "-S", "foo"])

    def test_no_retry_on_success(self):
        pm, lc = self._make({"paru": {"num_retries": 5}})
        pm.run_paru(["paru", "-S", "foo"])
        # Should only have been called once even though retries are allowed
        self.assertEqual(lc.utils.target_env_process_output.call_count, 1)

    def test_reraises_when_no_retries(self):
        pm, lc = self._make()  # num_retries=0
        lc.utils.target_env_process_output.side_effect = subprocess.CalledProcessError(
            1, "paru"
        )
        with self.assertRaises(subprocess.CalledProcessError):
            pm.run_paru(["paru", "-S", "foo"])
        self.assertEqual(lc.utils.target_env_process_output.call_count, 1)

    def test_retries_up_to_num_retries(self):
        pm, lc = self._make({"paru": {"num_retries": 2}})
        lc.utils.target_env_process_output.side_effect = subprocess.CalledProcessError(
            1, "paru"
        )
        with self.assertRaises(subprocess.CalledProcessError):
            pm.run_paru(["paru", "-S", "foo"])
        # 1 initial attempt + 2 retries = 3 total calls
        self.assertEqual(lc.utils.target_env_process_output.call_count, 3)

    def test_succeeds_on_second_attempt(self):
        pm, lc = self._make({"paru": {"num_retries": 1}})
        lc.utils.target_env_process_output.side_effect = [
            subprocess.CalledProcessError(1, "paru"),
            None,  # success on 2nd call
        ]
        pm.run_paru(["paru", "-S", "foo"])  # should not raise
        self.assertEqual(lc.utils.target_env_process_output.call_count, 2)


class TestPMParuInstall(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        pm = PMParu()
        return pm, lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_install_remote_uses_dash_s(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("-S", cmd)
        self.assertNotIn("-U", cmd)

    def test_install_local_uses_dash_u(self):
        pm, lc = self._make()
        pm.install(["vim.pkg.tar.zst"], from_local=True)
        cmd = self._captured_command(lc)
        self.assertIn("-U", cmd)
        self.assertNotIn("-S", cmd)

    def test_install_includes_noconfirm(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_install_includes_noprogressbar(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noprogressbar", cmd)

    def test_install_excludes_needed_by_default(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertNotIn("--needed", cmd)

    def test_install_includes_needed_when_configured(self):
        pm, lc = self._make({"paru": {"needed_only": True}})
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--needed", cmd)

    def test_install_excludes_disable_download_timeout_by_default(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertNotIn("--disable-download-timeout", cmd)

    def test_install_includes_disable_download_timeout_when_configured(self):
        pm, lc = self._make({"paru": {"disable_download_timeout": True}})
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--disable-download-timeout", cmd)

    def test_install_appends_packages(self):
        pm, lc = self._make()
        pm.install(["vim", "git", "curl"])
        cmd = self._captured_command(lc)
        self.assertIn("vim", cmd)
        self.assertIn("git", cmd)
        self.assertIn("curl", cmd)

    def test_install_command_starts_with_sudo_paru(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertEqual(cmd[:5], ["sudo", "-E", "-u", "nobody", "paru"])

    def test_install_sets_env_vars(self):
        import os
        pm, lc = self._make()
        pm.install(["vim"])
        self.assertEqual(os.environ["PWD"], "/var/cache")
        self.assertEqual(os.environ["XDG_CACHE_HOME"], "/var/cache")

    def test_install_empty_package_list(self):
        # Edge case: installing zero packages should still run without error
        pm, lc = self._make()
        pm.install([])
        lc.utils.target_env_process_output.assert_called_once()


class TestPMParuRemove(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        pm = PMParu()
        return pm, lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_remove_uses_rs_flags(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("-Rs", cmd)

    def test_remove_includes_noconfirm(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_remove_appends_packages(self):
        pm, lc = self._make()
        pm.remove(["vim", "git"])
        cmd = self._captured_command(lc)
        self.assertIn("vim", cmd)
        self.assertIn("git", cmd)

    def test_remove_command_starts_with_sudo_paru(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertEqual(cmd[:5], ["sudo", "-E", "-u", "nobody", "paru"])


class TestPMParuUpdateDb(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        pm = PMParu()
        return pm, lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_update_db_uses_sy(self):
        pm, lc = self._make()
        pm.update_db()
        cmd = self._captured_command(lc)
        self.assertIn("-Sy", cmd)

    def test_update_db_command_contains_paru(self):
        pm, lc = self._make()
        pm.update_db()
        cmd = self._captured_command(lc)
        self.assertIn("paru", cmd)


class TestPMParuUpdateSystem(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        pm = PMParu()
        return pm, lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_update_system_uses_su(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("-Su", cmd)

    def test_update_system_includes_noconfirm(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_update_system_excludes_disable_download_timeout_by_default(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertNotIn("--disable-download-timeout", cmd)

    def test_update_system_includes_disable_download_timeout_when_configured(self):
        pm, lc = self._make({"paru": {"disable_download_timeout": True}})
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("--disable-download-timeout", cmd)


class TestPMParuLineCb(unittest.TestCase):
    """Tests for the line_cb closure inside PMParu.__init__."""

    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMParu = _make_pmparu_class(lc, subprocess)
        pm = PMParu()
        return pm, lc

    def test_line_starting_with_colons_sets_in_package_changes_true_for_package(self):
        pm, lc = self._make()
        pm.line_cb(":: Processing package changes...\n")
        self.assertTrue(pm.in_package_changes)

    def test_line_starting_with_colons_sets_in_package_changes_true_for_hooks(self):
        pm, lc = self._make()
        pm.line_cb(":: Running hooks...\n")
        self.assertTrue(pm.in_package_changes)

    def test_line_starting_with_colons_sets_in_package_changes_false_for_other(self):
        pm, lc = self._make()
        pm.in_package_changes = True
        pm.line_cb(":: Downloading...\n")
        self.assertFalse(pm.in_package_changes)

    def test_non_colon_line_does_not_change_in_package_changes_flag(self):
        pm, lc = self._make()
        pm.in_package_changes = True
        pm.line_cb("some random output\n")
        self.assertTrue(pm.in_package_changes)

    def test_line_cb_always_calls_debug(self):
        pm, lc = self._make()
        pm.line_cb("some output\n")
        lc.utils.debug.assert_called_once_with("some output\n")


# ---------------------------------------------------------------------------
# Tests – PMYay
# ---------------------------------------------------------------------------

class TestPMYayBackend(unittest.TestCase):
    def test_backend_attribute(self):
        lc = _make_libcalamares()
        PMYay = _make_pmyay_class(lc, subprocess)
        self.assertEqual(PMYay.backend, "yay")


class TestPMYayInit(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def test_default_config_when_key_absent(self):
        pm, _ = self._make({})
        self.assertEqual(pm.yay_num_retries, 0)
        self.assertFalse(pm.yay_disable_timeout)
        self.assertFalse(pm.yay_needed_only)

    def test_default_config_when_key_is_none(self):
        pm, _ = self._make({"yay": None})
        self.assertEqual(pm.yay_num_retries, 0)
        self.assertFalse(pm.yay_disable_timeout)
        self.assertFalse(pm.yay_needed_only)

    def test_non_dict_yay_config_is_ignored_with_warning(self):
        pm, lc = self._make({"yay": 42})
        lc.utils.warning.assert_called_once()
        warning_msg = lc.utils.warning.call_args[0][0]
        self.assertIn("yay", warning_msg)
        self.assertEqual(pm.yay_num_retries, 0)

    def test_custom_num_retries(self):
        pm, _ = self._make({"yay": {"num_retries": 5}})
        self.assertEqual(pm.yay_num_retries, 5)

    def test_disable_download_timeout(self):
        pm, _ = self._make({"yay": {"disable_download_timeout": True}})
        self.assertTrue(pm.yay_disable_timeout)

    def test_needed_only(self):
        pm, _ = self._make({"yay": {"needed_only": True}})
        self.assertTrue(pm.yay_needed_only)

    def test_in_package_changes_initialised_false(self):
        pm, _ = self._make()
        self.assertFalse(pm.in_package_changes)


class TestPMYayRunYay(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def test_calls_target_env_process_output(self):
        pm, lc = self._make()
        pm.run_yay(["yay", "-S", "foo"])
        lc.utils.target_env_process_output.assert_called_once_with(["yay", "-S", "foo"])

    def test_reraises_when_no_retries(self):
        pm, lc = self._make()
        lc.utils.target_env_process_output.side_effect = subprocess.CalledProcessError(
            1, "yay"
        )
        with self.assertRaises(subprocess.CalledProcessError):
            pm.run_yay(["yay", "-S", "foo"])
        self.assertEqual(lc.utils.target_env_process_output.call_count, 1)

    def test_retries_up_to_num_retries(self):
        pm, lc = self._make({"yay": {"num_retries": 2}})
        lc.utils.target_env_process_output.side_effect = subprocess.CalledProcessError(
            1, "yay"
        )
        with self.assertRaises(subprocess.CalledProcessError):
            pm.run_yay(["yay", "-S", "foo"])
        self.assertEqual(lc.utils.target_env_process_output.call_count, 3)

    def test_succeeds_on_second_attempt(self):
        pm, lc = self._make({"yay": {"num_retries": 1}})
        lc.utils.target_env_process_output.side_effect = [
            subprocess.CalledProcessError(1, "yay"),
            None,
        ]
        pm.run_yay(["yay", "-S", "foo"])
        self.assertEqual(lc.utils.target_env_process_output.call_count, 2)


class TestPMYayInstall(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_install_remote_uses_dash_s(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("-S", cmd)
        self.assertNotIn("-U", cmd)

    def test_install_local_uses_dash_u(self):
        pm, lc = self._make()
        pm.install(["vim.pkg.tar.zst"], from_local=True)
        cmd = self._captured_command(lc)
        self.assertIn("-U", cmd)
        self.assertNotIn("-S", cmd)

    def test_install_includes_noconfirm(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_install_includes_noprogressbar(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noprogressbar", cmd)

    def test_install_includes_needed_when_configured(self):
        pm, lc = self._make({"yay": {"needed_only": True}})
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--needed", cmd)

    def test_install_includes_disable_download_timeout_when_configured(self):
        pm, lc = self._make({"yay": {"disable_download_timeout": True}})
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--disable-download-timeout", cmd)

    def test_install_appends_packages(self):
        pm, lc = self._make()
        pm.install(["vim", "git"])
        cmd = self._captured_command(lc)
        self.assertIn("vim", cmd)
        self.assertIn("git", cmd)

    def test_install_command_starts_with_sudo_yay(self):
        pm, lc = self._make()
        pm.install(["vim"])
        cmd = self._captured_command(lc)
        self.assertEqual(cmd[:5], ["sudo", "-E", "-u", "nobody", "yay"])


class TestPMYayRemove(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_remove_uses_rs_flags(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("-Rs", cmd)

    def test_remove_includes_noconfirm(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_remove_command_starts_with_sudo_yay(self):
        pm, lc = self._make()
        pm.remove(["vim"])
        cmd = self._captured_command(lc)
        self.assertEqual(cmd[:5], ["sudo", "-E", "-u", "nobody", "yay"])

    def test_remove_appends_multiple_packages(self):
        pm, lc = self._make()
        pm.remove(["a", "b", "c"])
        cmd = self._captured_command(lc)
        self.assertIn("a", cmd)
        self.assertIn("b", cmd)
        self.assertIn("c", cmd)


class TestPMYayUpdateDb(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_update_db_uses_sy(self):
        pm, lc = self._make()
        pm.update_db()
        cmd = self._captured_command(lc)
        self.assertIn("-Sy", cmd)

    def test_update_db_command_contains_yay(self):
        pm, lc = self._make()
        pm.update_db()
        cmd = self._captured_command(lc)
        self.assertIn("yay", cmd)


class TestPMYayUpdateSystem(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def _captured_command(self, lc):
        return lc.utils.target_env_process_output.call_args[0][0]

    def test_update_system_uses_su(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("-Su", cmd)

    def test_update_system_includes_noconfirm(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("--noconfirm", cmd)

    def test_update_system_excludes_disable_download_timeout_by_default(self):
        pm, lc = self._make()
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertNotIn("--disable-download-timeout", cmd)

    def test_update_system_includes_disable_download_timeout_when_configured(self):
        pm, lc = self._make({"yay": {"disable_download_timeout": True}})
        pm.update_system()
        cmd = self._captured_command(lc)
        self.assertIn("--disable-download-timeout", cmd)


class TestPMYayLineCb(unittest.TestCase):
    def _make(self, config=None):
        lc = _make_libcalamares(config)
        PMYay = _make_pmyay_class(lc, subprocess)
        return PMYay(), lc

    def test_line_starting_with_colons_sets_in_package_changes_true_for_package(self):
        pm, _ = self._make()
        pm.line_cb(":: Processing package changes...\n")
        self.assertTrue(pm.in_package_changes)

    def test_line_starting_with_colons_sets_in_package_changes_true_for_hooks(self):
        pm, _ = self._make()
        pm.line_cb(":: Running hooks...\n")
        self.assertTrue(pm.in_package_changes)

    def test_line_starting_with_colons_false_for_irrelevant_prefix(self):
        pm, _ = self._make()
        pm.in_package_changes = True
        pm.line_cb(":: Downloading...\n")
        self.assertFalse(pm.in_package_changes)

    def test_line_cb_calls_debug(self):
        pm, lc = self._make()
        pm.line_cb("output line\n")
        lc.utils.debug.assert_called_once_with("output line\n")


# ---------------------------------------------------------------------------
# Cross-cutting: verify PMParu and PMYay are separate backends
# ---------------------------------------------------------------------------

class TestPMParuVsPMYayAreDistinct(unittest.TestCase):
    def test_backends_differ(self):
        lc_paru = _make_libcalamares()
        lc_yay = _make_libcalamares()
        PMParu = _make_pmparu_class(lc_paru, subprocess)
        PMYay = _make_pmyay_class(lc_yay, subprocess)
        self.assertNotEqual(PMParu.backend, PMYay.backend)

    def test_install_commands_differ(self):
        lc_paru = _make_libcalamares()
        lc_yay = _make_libcalamares()
        PMParu = _make_pmparu_class(lc_paru, subprocess)
        PMYay = _make_pmyay_class(lc_yay, subprocess)
        pm_paru = PMParu()
        pm_yay = PMYay()
        pm_paru.install(["vim"])
        pm_yay.install(["vim"])
        cmd_paru = lc_paru.utils.target_env_process_output.call_args[0][0]
        cmd_yay = lc_yay.utils.target_env_process_output.call_args[0][0]
        self.assertIn("paru", cmd_paru)
        self.assertIn("yay", cmd_yay)
        self.assertNotIn("yay", cmd_paru)
        self.assertNotIn("paru", cmd_yay)


if __name__ == "__main__":
    unittest.main()
