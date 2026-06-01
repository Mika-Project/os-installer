"""
Tests for PKGBUILD and .SRCINFO consistency.

Validates that:
- PKGBUILD contains the required metadata fields
- .SRCINFO matches the values in PKGBUILD
- .nvchecker.toml is correctly configured
- Package version, dependencies, and checksums are consistent across files
"""

import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKGBUILD_PATH = os.path.join(REPO_ROOT, "PKGBUILD")
SRCINFO_PATH = os.path.join(REPO_ROOT, ".SRCINFO")
NVCHECKER_PATH = os.path.join(REPO_ROOT, ".nvchecker.toml")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path):
    with open(path) as fh:
        return fh.read()


def _pkgbuild_var(content, name):
    """Return the value of a simple shell variable assignment, e.g. pkgver=3.4.2."""
    m = re.search(rf'^{re.escape(name)}=["\']?([^"\'$\n]+)["\']?', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _pkgbuild_array(content, name):
    """
    Return a list of values from a bash array assignment, e.g.
        depends=(
          'foo'
          'bar'
        )
    Handles single-quoted and double-quoted entries.
    """
    m = re.search(
        rf'^{re.escape(name)}\s*=\s*\((.*?)\)',
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    inner = m.group(1)
    return re.findall(r"['\"]([^'\"]+)['\"]", inner)


def _srcinfo_values(content, key):
    """Return all values for a repeated key in .SRCINFO, e.g. all 'depends' entries."""
    return [
        m.group(1).strip()
        for m in re.finditer(rf'^\s+{re.escape(key)}\s*=\s*(.+)$', content, re.MULTILINE)
    ]


def _srcinfo_value(content, key):
    """Return the single value for a unique key in .SRCINFO."""
    m = re.search(rf'^\s+{re.escape(key)}\s*=\s*(.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# PKGBUILD tests
# ---------------------------------------------------------------------------

class TestPKGBUILDExists(unittest.TestCase):
    def test_pkgbuild_file_exists(self):
        self.assertTrue(os.path.isfile(PKGBUILD_PATH), "PKGBUILD not found")


class TestPKGBUILDFields(unittest.TestCase):
    def setUp(self):
        self.content = _read(PKGBUILD_PATH)

    def test_pkgver_present(self):
        self.assertIsNotNone(_pkgbuild_var(self.content, "pkgver"))

    def test_pkgver_value(self):
        self.assertEqual(_pkgbuild_var(self.content, "pkgver"), "3.4.2")

    def test_pkgrel_present(self):
        self.assertIsNotNone(_pkgbuild_var(self.content, "pkgrel"))

    def test_pkgrel_value(self):
        self.assertEqual(_pkgbuild_var(self.content, "pkgrel"), "2")

    def test_pkgname_present(self):
        # pkgname references _pkgname; the effective name should be calamares
        self.assertIn("calamares", self.content)

    def test_license_present(self):
        self.assertIn("GPL-3.0-or-later", self.content)

    def test_url_present(self):
        self.assertIn("https://codeberg.org/Calamares/calamares", self.content)

    def test_arch_includes_x86_64(self):
        self.assertIn("x86_64", self.content)

    def test_arch_includes_i686(self):
        self.assertIn("i686", self.content)

    def test_sha256sums_present(self):
        self.assertIn("sha256sums", self.content)

    def test_sha256sums_value(self):
        self.assertIn(
            "733bbbb00dc9f84874bd5c22960952f317ea2537565431179fa2152b2fbfdccc",
            self.content,
        )

    def test_build_function_present(self):
        self.assertIn("build()", self.content)

    def test_package_function_present(self):
        self.assertIn("package()", self.content)

    def test_cmake_build_type_release(self):
        self.assertIn("-DCMAKE_BUILD_TYPE=Release", self.content)

    def test_qt6_enabled(self):
        self.assertIn("-DWITH_QT6=ON", self.content)

    def test_install_config_enabled(self):
        self.assertIn("-DINSTALL_CONFIG=ON", self.content)

    def test_build_testing_disabled(self):
        self.assertIn("-DBUILD_TESTING=OFF", self.content)

    def test_ninja_generator(self):
        self.assertIn("-G Ninja", self.content)


class TestPKGBUILDDepends(unittest.TestCase):
    EXPECTED_DEPENDS = {
        "kcoreaddons",
        "kpmcore",
        "libpwquality",
        "qt6-declarative",
        "qt6-svg",
        "yaml-cpp",
    }
    EXPECTED_MAKEDEPENDS = {
        "extra-cmake-modules",
        "libglvnd",
        "ninja",
        "qt6-tools",
        "qt6-translations",
    }

    def setUp(self):
        self.content = _read(PKGBUILD_PATH)

    def test_all_depends_present(self):
        deps = _pkgbuild_array(self.content, "depends")
        for dep in self.EXPECTED_DEPENDS:
            self.assertIn(dep, deps, f"Missing dependency: {dep}")

    def test_all_makedepends_present(self):
        mdeps = _pkgbuild_array(self.content, "makedepends")
        for dep in self.EXPECTED_MAKEDEPENDS:
            self.assertIn(dep, mdeps, f"Missing makedepend: {dep}")

    def test_depends_count(self):
        deps = _pkgbuild_array(self.content, "depends")
        self.assertEqual(len(deps), 6, f"Expected 6 depends, got {len(deps)}: {deps}")

    def test_makedepends_count(self):
        mdeps = _pkgbuild_array(self.content, "makedepends")
        self.assertEqual(
            len(mdeps), 5, f"Expected 5 makedepends, got {len(mdeps)}: {mdeps}"
        )


class TestPKGBUILDSkipModules(unittest.TestCase):
    EXPECTED_SKIPPED = [
        "dracut",
        "dracutlukscfg",
        "dummycpp",
        "dummyprocess",
        "dummypython",
        "dummypythonqt",
        "initramfs",
        "initramfscfg",
        "interactiveterminal",
        "packagechooser",
        "packagechooserq",
        "services-openrc",
    ]

    def setUp(self):
        self.content = _read(PKGBUILD_PATH)

    def test_skip_modules_variable_present(self):
        self.assertIn("_skip_modules", self.content)

    def test_all_expected_modules_are_skipped(self):
        for module in self.EXPECTED_SKIPPED:
            self.assertIn(module, self.content, f"Module not skipped: {module}")

    def test_skip_modules_count(self):
        # Find the _skip_modules array
        m = re.search(
            r"_skip_modules\s*=\s*\((.*?)\)",
            self.content,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "_skip_modules array not found")
        modules = [w for w in m.group(1).split() if w]
        self.assertEqual(
            len(modules),
            12,
            f"Expected 12 skipped modules, got {len(modules)}: {modules}",
        )


# ---------------------------------------------------------------------------
# .SRCINFO tests
# ---------------------------------------------------------------------------

class TestSRCINFOExists(unittest.TestCase):
    def test_srcinfo_file_exists(self):
        self.assertTrue(os.path.isfile(SRCINFO_PATH), ".SRCINFO not found")


class TestSRCINFOFields(unittest.TestCase):
    def setUp(self):
        self.content = _read(SRCINFO_PATH)

    def test_pkgbase_is_calamares(self):
        m = re.search(r'^pkgbase\s*=\s*(.+)$', self.content, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "calamares")

    def test_pkgname_is_calamares(self):
        m = re.search(r'^pkgname\s*=\s*(.+)$', self.content, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), "calamares")

    def test_pkgver_value(self):
        self.assertEqual(_srcinfo_value(self.content, "pkgver"), "3.4.2")

    def test_pkgrel_value(self):
        self.assertEqual(_srcinfo_value(self.content, "pkgrel"), "2")

    def test_license(self):
        self.assertEqual(_srcinfo_value(self.content, "license"), "GPL-3.0-or-later")

    def test_url(self):
        self.assertIn(
            "https://codeberg.org/Calamares/calamares",
            _srcinfo_value(self.content, "url"),
        )

    def test_sha256sum_present(self):
        sha = _srcinfo_value(self.content, "sha256sums")
        self.assertIsNotNone(sha)
        self.assertEqual(
            sha, "733bbbb00dc9f84874bd5c22960952f317ea2537565431179fa2152b2fbfdccc"
        )

    def test_source_references_correct_version(self):
        src = _srcinfo_value(self.content, "source")
        self.assertIsNotNone(src)
        self.assertIn("3.4.2", src)

    def test_arch_includes_x86_64(self):
        arches = _srcinfo_values(self.content, "arch")
        self.assertIn("x86_64", arches)

    def test_arch_includes_i686(self):
        arches = _srcinfo_values(self.content, "arch")
        self.assertIn("i686", arches)


class TestSRCINFODepends(unittest.TestCase):
    EXPECTED_DEPENDS = {
        "kcoreaddons",
        "kpmcore",
        "libpwquality",
        "qt6-declarative",
        "qt6-svg",
        "yaml-cpp",
    }
    EXPECTED_MAKEDEPENDS = {
        "extra-cmake-modules",
        "libglvnd",
        "ninja",
        "qt6-tools",
        "qt6-translations",
    }

    def setUp(self):
        self.content = _read(SRCINFO_PATH)

    def test_all_depends_present(self):
        deps = _srcinfo_values(self.content, "depends")
        for dep in self.EXPECTED_DEPENDS:
            self.assertIn(dep, deps, f"Missing dependency in .SRCINFO: {dep}")

    def test_all_makedepends_present(self):
        mdeps = _srcinfo_values(self.content, "makedepends")
        for dep in self.EXPECTED_MAKEDEPENDS:
            self.assertIn(dep, mdeps, f"Missing makedepend in .SRCINFO: {dep}")


# ---------------------------------------------------------------------------
# PKGBUILD <-> .SRCINFO consistency tests
# ---------------------------------------------------------------------------

class TestPKGBUILDSRCINFOConsistency(unittest.TestCase):
    def setUp(self):
        self.pkgbuild = _read(PKGBUILD_PATH)
        self.srcinfo = _read(SRCINFO_PATH)

    def test_pkgver_matches(self):
        pkgver = _pkgbuild_var(self.pkgbuild, "pkgver")
        srcinfo_ver = _srcinfo_value(self.srcinfo, "pkgver")
        self.assertEqual(pkgver, srcinfo_ver, "pkgver mismatch between PKGBUILD and .SRCINFO")

    def test_pkgrel_matches(self):
        pkgrel = _pkgbuild_var(self.pkgbuild, "pkgrel")
        srcinfo_rel = _srcinfo_value(self.srcinfo, "pkgrel")
        self.assertEqual(pkgrel, srcinfo_rel, "pkgrel mismatch between PKGBUILD and .SRCINFO")

    def test_sha256sum_matches(self):
        expected_sha = "733bbbb00dc9f84874bd5c22960952f317ea2537565431179fa2152b2fbfdccc"
        self.assertIn(expected_sha, self.pkgbuild)
        self.assertIn(expected_sha, self.srcinfo)

    def test_depends_in_pkgbuild_are_in_srcinfo(self):
        pkgbuild_deps = set(_pkgbuild_array(self.pkgbuild, "depends"))
        srcinfo_deps = set(_srcinfo_values(self.srcinfo, "depends"))
        missing = pkgbuild_deps - srcinfo_deps
        self.assertEqual(missing, set(), f"Deps in PKGBUILD but not .SRCINFO: {missing}")

    def test_makedepends_in_pkgbuild_are_in_srcinfo(self):
        pkgbuild_mdeps = set(_pkgbuild_array(self.pkgbuild, "makedepends"))
        srcinfo_mdeps = set(_srcinfo_values(self.srcinfo, "makedepends"))
        missing = pkgbuild_mdeps - srcinfo_mdeps
        self.assertEqual(missing, set(), f"makedepends in PKGBUILD but not .SRCINFO: {missing}")

    def test_url_matches(self):
        url = "https://codeberg.org/Calamares/calamares"
        self.assertIn(url, self.pkgbuild)
        self.assertIn(url, self.srcinfo)

    def test_source_url_contains_pkgver(self):
        pkgver = _pkgbuild_var(self.pkgbuild, "pkgver")
        srcinfo_source = _srcinfo_value(self.srcinfo, "source")
        self.assertIn(pkgver, srcinfo_source)


# ---------------------------------------------------------------------------
# .nvchecker.toml tests
# ---------------------------------------------------------------------------

class TestNVCheckerExists(unittest.TestCase):
    def test_nvchecker_file_exists(self):
        self.assertTrue(os.path.isfile(NVCHECKER_PATH), ".nvchecker.toml not found")


class TestNVCheckerContent(unittest.TestCase):
    def setUp(self):
        self.content = _read(NVCHECKER_PATH)

    def test_calamares_section_present(self):
        self.assertIn("[calamares]", self.content)

    def test_source_is_git(self):
        self.assertIn('source = "git"', self.content)

    def test_git_url_is_calamares_codeberg(self):
        self.assertIn(
            'git = "https://codeberg.org/Calamares/calamares.git"', self.content
        )

    def test_prefix_is_v(self):
        self.assertIn('prefix = "v"', self.content)

    def test_git_url_ends_with_dot_git(self):
        m = re.search(r'git\s*=\s*"([^"]+)"', self.content)
        self.assertIsNotNone(m, "git key not found in .nvchecker.toml")
        self.assertTrue(m.group(1).endswith(".git"), "git URL should end with .git")

    def test_git_url_uses_https(self):
        m = re.search(r'git\s*=\s*"([^"]+)"', self.content)
        self.assertIsNotNone(m)
        self.assertTrue(m.group(1).startswith("https://"), "git URL should use HTTPS")


if __name__ == "__main__":
    unittest.main()