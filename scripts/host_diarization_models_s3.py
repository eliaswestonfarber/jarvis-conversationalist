"""Host the pyannote diarization weights on S3 so end users of
jarvis-conversationalist do NOT need a Hugging Face token.

pyannote/speaker-diarization-3.1 and pyannote/segmentation-3.0 are MIT-licensed,
so re-hosting an ungated copy is permitted; the embedding model is already
ungated and is fetched anonymously at load time, so only the segmentation
checkpoint + pipeline config need hosting (~6 MB total).

At first use the package downloads these from JARVIS_MODELS_BASE_URL
(default: https://eliastechlabs.com/jarvis-models) -- see
audio_identifier._ensure_diarization_models().

Re-generate the host (one-time, or when updating the models):
  1. Obtain the files, either from a machine that already has them cached under
     ~/.cache/torch/pyannote/models--pyannote--{speaker-diarization-3.1,
     segmentation-3.0}/snapshots/*, or download once with a valid HF token:
         huggingface-cli download pyannote/segmentation-3.0
         huggingface-cli download pyannote/speaker-diarization-3.1
  2. Upload, preserving this layout:
         s3://<bucket>/<prefix>/speaker-diarization-3.1/config.yaml
         s3://<bucket>/<prefix>/segmentation-3.0/config.yaml
         s3://<bucket>/<prefix>/segmentation-3.0/pytorch_model.bin

This script automates step 2 from a local pyannote cache:
    python scripts/host_diarization_models_s3.py --bucket eliastechlabs.com --prefix jarvis-models
"""
import argparse
import glob
import os
import shutil
import subprocess
import tempfile

CACHE = os.path.expanduser("~/.cache/torch/pyannote")


def _snapshot(model: str, needs: list) -> str:
    base = os.path.join(CACHE, f"models--pyannote--{model}", "snapshots")
    for snap in sorted(glob.glob(os.path.join(base, "*"))):
        if all(os.path.exists(os.path.join(snap, f)) for f in needs):
            return snap
    raise SystemExit(
        f"Could not find cached {model} containing {needs} under {base}.\n"
        "Download it first (see this module's docstring)."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--prefix", default="jarvis-models")
    args = ap.parse_args()

    sd = _snapshot("speaker-diarization-3.1", ["config.yaml"])
    seg = _snapshot("segmentation-3.0", ["config.yaml", "pytorch_model.bin"])

    stage = tempfile.mkdtemp()
    os.makedirs(os.path.join(stage, "speaker-diarization-3.1"))
    os.makedirs(os.path.join(stage, "segmentation-3.0"))
    shutil.copy(os.path.join(sd, "config.yaml"), os.path.join(stage, "speaker-diarization-3.1", "config.yaml"))
    shutil.copy(os.path.join(seg, "config.yaml"), os.path.join(stage, "segmentation-3.0", "config.yaml"))
    shutil.copy(os.path.join(seg, "pytorch_model.bin"), os.path.join(stage, "segmentation-3.0", "pytorch_model.bin"))

    dest = f"s3://{args.bucket}/{args.prefix}/"
    print("uploading to", dest)
    subprocess.run(["aws", "s3", "cp", stage + "/", dest, "--recursive"], check=True)
    shutil.rmtree(stage)
    print("done")


if __name__ == "__main__":
    main()
