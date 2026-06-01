"""
Tests for the patch files introduced in this PR:
  - 0001-support-paru.patch
  - 0001-support-yay.patch

Validates:
- Patch files exist and are non-empty
- Patch headers conform to git format-patch output
- Each patch targets the correct calamares source files
- Class definitions, backend attributes, and method signatures are present
- The correct AUR helper binary is referenced in commands
- packages.conf comment additions are present
- Structural symmetry between the paru and yay patches
"""

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARU_PATCH = os.path.join(REPO_ROOT, "0001-support-paru.patch")
YAY_PATCH = os.path.join(REPO_ROOT, "0001-support-yay.patch")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path):
    with open(path) as fh:
        return fh.read()


def _added_lines(patch_content):
    """Return only lines that the patch adds (lines starting with '+' but not '+++')."""
    return [
        line[1:]
        for line in patch_content.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


# ---------------------------------------------------------------------------
# Existence and basic structure
# ---------------------------------------------------------------------------

class TestPatchFilesExist(unittest.TestCase):
    def test_paru_patch_exists(self):
        self.assertTrue(os.path.isfile(PARU_PATCH), "0001-support-paru.patch not found")

    def test_yay_patch_exists(self):
        self.assertTrue(os.path.isfile(YAY_PATCH), "0001-support-yay.patch not found")

    def test_paru_patch_non_empty(self):
        self.assertGreater(os.path.getsize(PARU_PATCH), 0)

    def test_yay_patch_non_empty(self):
        self.assertGreater(os.path.getsize(YAY_PATCH), 0)


class TestPatchGitHeader(unittest.TestCase):
    """Verify git format-patch header fields."""

    def _check_from_header(self, content):
        self.assertRegex(
            content.splitlines()[0],
            r'^From [0-9a-f]{40} Mon Sep 17 00:00:00 2001$',
            "First line should be a git 'From' header",
        )

    def _check_from_email(self, content):
        self.assertIn("From:", content)

    def _check_subject(self, content):
        self.assertIn("Subject: [PATCH]", content)

    def _check_diff_header(self, content):
        self.assertIn("diff --git", content)

    def test_paru_patch_has_from_header(self):
        self._check_from_header(_read(PARU_PATCH))

    def test_yay_patch_has_from_header(self):
        self._check_from_header(_read(YAY_PATCH))

    def test_paru_patch_has_from_email(self):
        self._check_from_email(_read(PARU_PATCH))

    def test_yay_patch_has_from_email(self):
        self._check_from_email(_read(YAY_PATCH))

    def test_paru_patch_has_subject(self):
        self._check_subject(_read(PARU_PATCH))

    def test_yay_patch_has_subject(self):
        self._check_subject(_read(YAY_PATCH))

    def test_paru_patch_has_diff_header(self):
        self._check_diff_header(_read(PARU_PATCH))

    def test_yay_patch_has_diff_header(self):
        self._check_diff_header(_read(YAY_PATCH))


# ---------------------------------------------------------------------------
# Target files within the patches
# ---------------------------------------------------------------------------

class TestPatchTargetFiles(unittest.TestCase):
    def test_paru_patch_targets_main_py(self):
        content = _read(PARU_PATCH)
        self.assertIn("src/modules/packages/main.py", content)

    def test_paru_patch_targets_packages_conf(self):
        content = _read(PARU_PATCH)
        self.assertIn("src/modules/packages/packages.conf", content)

    def test_yay_patch_targets_main_py(self):
        content = _read(YAY_PATCH)
        self.assertIn("src/modules/packages/main.py", content)

    def test_yay_patch_targets_packages_conf(self):
        content = _read(YAY_PATCH)
        self.assertIn("src/modules/packages/packages.conf", content)

    def test_paru_patch_two_files_changed(self):
        content = _read(PARU_PATCH)
        # The stat summary line: "2 files changed"
        self.assertIn("2 files changed", content)

    def test_yay_patch_two_files_changed(self):
        content = _read(YAY_PATCH)
        self.assertIn("2 files changed", content)


# ---------------------------------------------------------------------------
# PMParu class in paru patch
# ---------------------------------------------------------------------------

class TestParuPatchClassDefinition(unittest.TestCase):
    def setUp(self):
        self.content = _read(PARU_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_class_pmparu_defined(self):
        self.assertIn("class PMParu(PackageManager):", self.added)

    def test_backend_is_paru(self):
        self.assertIn('backend = "paru"', self.added)

    def test_init_method_present(self):
        self.assertIn("def __init__(self):", self.added)

    def test_reset_progress_method_present(self):
        self.assertIn("def reset_progress(self):", self.added)

    def test_run_paru_method_present(self):
        self.assertIn("def run_paru(self, command, callback=False):", self.added)

    def test_install_method_present(self):
        self.assertIn("def install(self, pkgs, from_local=False):", self.added)

    def test_remove_method_present(self):
        self.assertIn("def remove(self, pkgs):", self.added)

    def test_update_db_method_present(self):
        self.assertIn("def update_db(self):", self.added)

    def test_update_system_method_present(self):
        self.assertIn("def update_system(self):", self.added)


class TestParuPatchCommandConstruction(unittest.TestCase):
    def setUp(self):
        self.content = _read(PARU_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_uses_paru_binary(self):
        self.assertIn('"paru"', self.added)

    def test_install_uses_noconfirm(self):
        self.assertIn('"--noconfirm"', self.added)

    def test_install_uses_noprogressbar(self):
        self.assertIn('"--noprogressbar"', self.added)

    def test_install_remote_flag_is_S(self):
        self.assertIn('"-S"', self.added)

    def test_install_local_flag_is_U(self):
        self.assertIn('"-U"', self.added)

    def test_remove_uses_rs(self):
        self.assertIn('"-Rs"', self.added)

    def test_update_db_uses_sy(self):
        self.assertIn('"-Sy"', self.added)

    def test_update_system_uses_su(self):
        self.assertIn('"-Su"', self.added)

    def test_runs_as_nobody(self):
        self.assertIn('"nobody"', self.added)

    def test_uses_sudo(self):
        self.assertIn('"sudo"', self.added)

    def test_disable_download_timeout_flag(self):
        self.assertIn('"--disable-download-timeout"', self.added)

    def test_needed_flag(self):
        self.assertIn('"--needed"', self.added)

    def test_env_vars_set_to_var_cache(self):
        self.assertIn('"/var/cache"', self.added)


class TestParuPatchConfigKeys(unittest.TestCase):
    def setUp(self):
        self.content = _read(PARU_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_num_retries_config_key(self):
        self.assertIn('"num_retries"', self.added)

    def test_disable_download_timeout_config_key(self):
        self.assertIn('"disable_download_timeout"', self.added)

    def test_needed_only_config_key(self):
        self.assertIn('"needed_only"', self.added)

    def test_paru_config_section_name(self):
        self.assertIn('"paru"', self.added)


class TestParuPatchPackagesConf(unittest.TestCase):
    def setUp(self):
        self.content = _read(PARU_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_paru_comment_added_to_conf(self):
        self.assertIn("paru", self.added)

    def test_paru_described_as_aur_package_manager(self):
        self.assertIn("AUR", self.added)


# ---------------------------------------------------------------------------
# PMYay class in yay patch
# ---------------------------------------------------------------------------

class TestYayPatchClassDefinition(unittest.TestCase):
    def setUp(self):
        self.content = _read(YAY_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_class_pmyay_defined(self):
        self.assertIn("class PMYay(PackageManager):", self.added)

    def test_backend_is_yay(self):
        self.assertIn('backend = "yay"', self.added)

    def test_init_method_present(self):
        self.assertIn("def __init__(self):", self.added)

    def test_reset_progress_method_present(self):
        self.assertIn("def reset_progress(self):", self.added)

    def test_run_yay_method_present(self):
        self.assertIn("def run_yay(self, command, callback=False):", self.added)

    def test_install_method_present(self):
        self.assertIn("def install(self, pkgs, from_local=False):", self.added)

    def test_remove_method_present(self):
        self.assertIn("def remove(self, pkgs):", self.added)

    def test_update_db_method_present(self):
        self.assertIn("def update_db(self):", self.added)

    def test_update_system_method_present(self):
        self.assertIn("def update_system(self):", self.added)


class TestYayPatchCommandConstruction(unittest.TestCase):
    def setUp(self):
        self.content = _read(YAY_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_uses_yay_binary(self):
        self.assertIn('"yay"', self.added)

    def test_install_uses_noconfirm(self):
        self.assertIn('"--noconfirm"', self.added)

    def test_install_uses_noprogressbar(self):
        self.assertIn('"--noprogressbar"', self.added)

    def test_install_remote_flag_is_S(self):
        self.assertIn('"-S"', self.added)

    def test_install_local_flag_is_U(self):
        self.assertIn('"-U"', self.added)

    def test_remove_uses_rs(self):
        self.assertIn('"-Rs"', self.added)

    def test_update_db_uses_sy(self):
        self.assertIn('"-Sy"', self.added)

    def test_update_system_uses_su(self):
        self.assertIn('"-Su"', self.added)

    def test_runs_as_nobody(self):
        self.assertIn('"nobody"', self.added)

    def test_uses_sudo(self):
        self.assertIn('"sudo"', self.added)

    def test_disable_download_timeout_flag(self):
        self.assertIn('"--disable-download-timeout"', self.added)

    def test_needed_flag(self):
        self.assertIn('"--needed"', self.added)

    def test_env_vars_set_to_var_cache(self):
        self.assertIn('"/var/cache"', self.added)


class TestYayPatchConfigKeys(unittest.TestCase):
    def setUp(self):
        self.content = _read(YAY_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_num_retries_config_key(self):
        self.assertIn('"num_retries"', self.added)

    def test_disable_download_timeout_config_key(self):
        self.assertIn('"disable_download_timeout"', self.added)

    def test_needed_only_config_key(self):
        self.assertIn('"needed_only"', self.added)

    def test_yay_config_section_name(self):
        self.assertIn('"yay"', self.added)


class TestYayPatchPackagesConf(unittest.TestCase):
    def setUp(self):
        self.content = _read(YAY_PATCH)
        self.added = "\n".join(_added_lines(self.content))

    def test_yay_comment_added_to_conf(self):
        self.assertIn("yay", self.added)

    def test_yay_described_as_aur_package_manager(self):
        self.assertIn("AUR", self.added)


# ---------------------------------------------------------------------------
# Cross-patch consistency: paru and yay patches should not cross-contaminate
# ---------------------------------------------------------------------------

class TestPatchIsolation(unittest.TestCase):
    def setUp(self):
        self.paru_added = "\n".join(_added_lines(_read(PARU_PATCH)))
        self.yay_added = "\n".join(_added_lines(_read(YAY_PATCH)))

    def test_paru_patch_does_not_add_pmyay(self):
        self.assertNotIn("class PMYay", self.paru_added)

    def test_yay_patch_does_not_add_pmparu(self):
        self.assertNotIn("class PMParu", self.yay_added)

    def test_paru_patch_backend_is_not_yay(self):
        self.assertNotIn('backend = "yay"', self.paru_added)

    def test_yay_patch_backend_is_not_paru(self):
        self.assertNotIn('backend = "paru"', self.yay_added)

    def test_paru_patch_run_method_is_run_paru_not_run_yay(self):
        self.assertIn("def run_paru", self.paru_added)
        self.assertNotIn("def run_yay", self.paru_added)

    def test_yay_patch_run_method_is_run_yay_not_run_paru(self):
        self.assertIn("def run_yay", self.yay_added)
        self.assertNotIn("def run_paru", self.yay_added)

    def test_paru_patch_status_message_prefix(self):
        self.assertIn('"paru: "', self.paru_added)
        self.assertNotIn('"yay: "', self.paru_added)

    def test_yay_patch_status_message_prefix(self):
        self.assertIn('"yay: "', self.yay_added)
        self.assertNotIn('"paru: "', self.yay_added)


# ---------------------------------------------------------------------------
# Regression: both patches must retain the same commit hash (same base)
# ---------------------------------------------------------------------------

class TestPatchCommitHash(unittest.TestCase):
    EXPECTED_HASH = "e348a5424317b62dfa95bd88c85cb2da0f95571c"

    def test_paru_patch_commit_hash(self):
        content = _read(PARU_PATCH)
        self.assertIn(self.EXPECTED_HASH, content)

    def test_yay_patch_commit_hash(self):
        content = _read(YAY_PATCH)
        self.assertIn(self.EXPECTED_HASH, content)

    def test_both_patches_share_same_base_commit(self):
        paru = _read(PARU_PATCH)
        yay = _read(YAY_PATCH)
        paru_hash = re.search(r'^From ([0-9a-f]{40})', paru).group(1)
        yay_hash = re.search(r'^From ([0-9a-f]{40})', yay).group(1)
        self.assertEqual(
            paru_hash,
            yay_hash,
            "Both patches should share the same base commit hash",
        )


if __name__ == "__main__":
    unittest.main()