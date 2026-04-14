"""Post-install hook: download default embedding model (bge-small) after pip install."""
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


def _download_model():
    try:
        from sentence_transformers import SentenceTransformer
        print("\n[simargl] Downloading default embedding model (BAAI/bge-small-en-v1.5, ~130MB)...")
        SentenceTransformer("BAAI/bge-small-en-v1.5")
        print("[simargl] Model ready.\n")
    except Exception as e:
        print(f"[simargl] Could not download model automatically: {e}")
        print("[simargl] Run manually after install:  simargl download\n")


class PostInstall(install):
    def run(self):
        super().run()
        _download_model()


class PostDevelop(develop):
    def run(self):
        super().run()
        _download_model()


setup(cmdclass={"install": PostInstall, "develop": PostDevelop})
