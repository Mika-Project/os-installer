# os-installer

Builds the **[Calamares](https://codeberg.org/Calamares/calamares) installer** for
[Mika Linux](https://github.com/Mika-Project/base-iso) from source, against the Arch
libraries that are current *today* — so it needs **no soname shims** and doesn't break
every time a dependency bumps.

---

## Why this exists

Mika currently ships a *pinned*, prebuilt Calamares in
[mikalinux-repo](https://github.com/Mika-Project/mikalinux-repo). On rolling Arch that
binary breaks whenever a dependency's soname changes (yaml-cpp, icu, python,
boost-python, kpmcore…), and each break has to be patched over with a `*-shim` package.
The real fix is to **rebuild Calamares against whatever Arch ships now**. This repo
vendors the AUR recipe to do exactly that.

---

## What's here

| File | Purpose |
|------|---------|
| `PKGBUILD`, `.SRCINFO` | The Calamares package recipe (currently `calamares 3.4.2-2`). |
| `0001-support-yay.patch`, `0001-support-paru.patch` | Mika patches (AUR-helper support in the installer). |
| `.nvchecker.toml` | Upstream version tracking. |
| `x86_64/` | Build output (`*.pkg.tar.zst`). |
| `.github/workflows/` | Home for the build CI (see below). |

---

## Build locally

```bash
git clone https://github.com/Mika-Project/os-installer
cd os-installer
makepkg -s        # builds calamares-*.pkg.tar.zst against your current libraries
```

> [!IMPORTANT]
> Build in a **clean Arch environment** (a container, or `PYENV_VERSION=system`). If
> your shell's `python` is a pyenv shim, `makepkg` links the wrong `libpython` and the
> resulting binary won't run on the target.

Then publish it to the package repo:

```bash
cp x86_64/calamares-*.pkg.tar.zst ../mikalinux-repo/x86_64/
cd ../mikalinux-repo && sh build-database.sh
```

---

## CI (planned)

The goal is a **GitHub Actions** workflow that rebuilds Calamares in a clean
`archlinux:latest` container whenever upstream (or this recipe) changes, and publishes
the package to `mikalinux-repo` automatically — so the installer is always built
against current libraries and the shims can finally be retired. It lives under
`.github/workflows/`.
