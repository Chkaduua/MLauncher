#!/usr/bin/env python3
"""
Генерирует manifest.json для лаунчера Mythos.
Запуск (из корня репозитория):  python tools/make_manifest.py
Берёт:
  * tools/config.json          — версия Minecraft и Forge
  * mods/*.jar                 — список модов (sha1 + размер)
  * launcher/MythosLauncher.jar — версия лаунчера (из META-INF/MANIFEST.MF) + sha256
Репозиторий и ветка определяются из GITHUB_REPOSITORY / GITHUB_REF_NAME (в GitHub Actions)
или из git remote (локально).
"""
import hashlib, json, os, re, subprocess, sys, zipfile
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def file_hash(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_and_branch():
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_REF_NAME")
    if not repo:
        url = subprocess.check_output(["git", "-C", ROOT, "remote", "get-url", "origin"], text=True).strip()
        m = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?$", url)
        if not m:
            sys.exit("Не удалось определить репозиторий из git remote: " + url)
        repo = m.group(1)
    if not branch:
        branch = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    return repo, branch


def jar_version(path):
    with zipfile.ZipFile(path) as z:
        text = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
    m = re.search(r"^Implementation-Version:\s*(.+?)\s*$", text, re.M)
    return m.group(1) if m else None


def main():
    repo, branch = repo_and_branch()
    base = f"https://raw.githubusercontent.com/{repo}/{branch}/"
    with open(os.path.join(ROOT, "tools", "config.json"), encoding="utf-8") as f:
        manifest = json.load(f)

    mods = []
    mods_dir = os.path.join(ROOT, "mods")
    if os.path.isdir(mods_dir):
        for name in sorted(os.listdir(mods_dir), key=str.lower):
            p = os.path.join(mods_dir, name)
            if os.path.isfile(p) and name.lower().endswith(".jar"):
                mods.append({
                    "name": name,
                    "url": base + "mods/" + quote(name),
                    "sha1": file_hash(p, "sha1"),
                    "size": os.path.getsize(p),
                })
    manifest["mods"] = mods

    jar = os.path.join(ROOT, "launcher", "MythosLauncher.jar")
    if os.path.isfile(jar):
        version = jar_version(jar)
        if version:
            manifest["launcher"] = {
                "version": version,
                "url": base + "launcher/MythosLauncher.jar",
                "sha256": file_hash(jar, "sha256"),
                "size": os.path.getsize(jar),
            }
        else:
            print("ВНИМАНИЕ: в jar нет Implementation-Version — блок launcher пропущен")

    out = os.path.join(ROOT, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"manifest.json: модов {len(mods)}, лаунчер {manifest.get('launcher', {}).get('version', '—')}")


if __name__ == "__main__":
    main()
