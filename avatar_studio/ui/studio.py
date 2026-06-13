"""Gradio control panel — the easy, clickable way to run the studio.

Top-level imports are kept light (gradio + stdlib); ML backends import lazily
inside the callbacks, so this module imports fine without a GPU.

Launch on the VM:
    python -m avatar_studio.ui.studio
Then reach it from your laptop with an SSH tunnel (don't expose it publicly):
    ssh -L 7860:localhost:7860 user@your-vm
    # open http://localhost:7860
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid

import gradio as gr

from avatar_studio.config import Settings

settings = Settings.from_env()

ME_DIR = "assets/me"
_pipeline = None


# --- Tab 1: likeness data + training ---------------------------------------
def save_photos(files: list[str] | None) -> str:
    if not files:
        return "No files received — pick your photos first."
    os.makedirs(ME_DIR, exist_ok=True)
    for f in files:
        shutil.copy(f, os.path.join(ME_DIR, os.path.basename(f)))
    total = len([x for x in os.listdir(ME_DIR) if not x.startswith(".")])
    tip = "" if total >= 15 else "  (aim for 15-30 for a good likeness)"
    return f"Saved. {total} photo(s) now in {ME_DIR}.{tip}"


def save_voice(path: str | None) -> str:
    if not path:
        return "No clip received."
    os.makedirs(os.path.dirname(settings.voice_sample) or ".", exist_ok=True)
    shutil.copy(path, settings.voice_sample)
    return f"Saved voice reference to {settings.voice_sample}."


def train_stream(steps: int, token: str):
    from avatar_studio.face.train_lora import TrainConfig

    if not os.path.isdir(ME_DIR) or not os.listdir(ME_DIR):
        yield "No photos in assets/me/. Upload them above first."
        return

    cfg = TrainConfig(
        instance_data_dir=ME_DIR,
        output_dir="models/likeness-lora",
        instance_prompt=token,
        max_train_steps=int(steps),
    )
    log = "Launching training (20-40 min on a typical GPU)...\n\n"
    yield log
    try:
        proc = subprocess.Popen(
            cfg.command(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        yield log + f"Could not start training: {exc}\nDid scripts/provision_vm.sh run?"
        return

    for line in proc.stdout:  # type: ignore[union-attr]
        log += line
        yield log
    proc.wait()
    if proc.returncode == 0:
        yield log + (
            "\n\nDone. Your LoRA is in models/likeness-lora/. "
            "Set AVATAR_LORA_PATH to its .safetensors, then use Tab 2."
        )
    else:
        yield log + f"\n\nTraining exited with code {proc.returncode}."


# --- Tab 2: reference face --------------------------------------------------
def generate_face(prompt: str):
    from avatar_studio.factory import build_face_generator
    from avatar_studio.safety.image_filter import NSFWImageClassifier

    os.makedirs(settings.work_dir, exist_ok=True)
    out = os.path.join(settings.work_dir, f"face_{uuid.uuid4().hex[:8]}.png")
    build_face_generator(settings).generate(prompt, out)

    guard = NSFWImageClassifier(settings.nsfw_classifier, settings.nsfw_threshold, settings.device)
    if not guard.is_sfw(out):
        os.remove(out)
        return None, "Blocked by the SFW media filter. Try a different prompt."
    return out, f"Generated {out}."


def use_as_reference(image_path: str | None) -> str:
    if not image_path:
        return "Generate a face first, then click this."
    os.makedirs(os.path.dirname(settings.face_image) or ".", exist_ok=True)
    shutil.copy(image_path, settings.face_image)
    return f"Set as reference face: {settings.face_image}."


# --- Tab 3: chat ------------------------------------------------------------
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from avatar_studio.factory import build_pipeline

        _pipeline = build_pipeline(settings)
    return _pipeline


def chat(message: str, history: list | None):
    history = list(history or [])
    result = get_pipeline().handle_turn(message, history)
    video = result.video_path if result.video_path and os.path.exists(result.video_path) else None
    if not result.blocked:
        history += [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.text},
        ]
    return result.text, video, history


def build_demo() -> "gr.Blocks":
    with gr.Blocks(title="Avatar Studio (SFW)") as demo:
        gr.Markdown(
            "# Avatar Studio (SFW)\n"
            "Train on **your own** likeness, generate a reference face, then chat. "
            "Everything stays non-explicit — the safety gates are always on."
        )

        with gr.Tab("1. Train your likeness"):
            gr.Markdown(
                "Upload **15-30 varied photos of yourself** (different angles, "
                "expressions, lighting; just you, no other people)."
            )
            photos = gr.File(file_count="multiple", file_types=["image"], label="Your photos")
            photo_status = gr.Textbox(label="Status", interactive=False)
            photos.upload(save_photos, photos, photo_status)

            voice = gr.Audio(type="filepath", label="Voice reference (~10s of your voice)")
            voice_status = gr.Textbox(label="Voice status", interactive=False)
            voice.change(save_voice, voice, voice_status)

            token = gr.Textbox(value="a photo of sks person", label="Training token / prompt")
            steps = gr.Slider(600, 2000, value=1200, step=100, label="Training steps")
            train_btn = gr.Button("Train likeness LoRA", variant="primary")
            train_log = gr.Textbox(label="Training log", lines=14, interactive=False)
            train_btn.click(train_stream, [steps, token], train_log)

        with gr.Tab("2. Reference face"):
            face_prompt = gr.Textbox(
                value="a professional studio portrait of sks person, soft lighting, smiling",
                label="Prompt",
            )
            gen_btn = gr.Button("Generate face", variant="primary")
            face_img = gr.Image(type="filepath", label="Result")
            face_status = gr.Textbox(label="Status", interactive=False)
            gen_btn.click(generate_face, face_prompt, [face_img, face_status])
            use_btn = gr.Button("Use this as my reference face")
            use_btn.click(use_as_reference, face_img, face_status)

        with gr.Tab("3. Chat"):
            chatbox = gr.Chatbot(height=360)  # messages format is the default
            reply_video = gr.Video(label="Avatar reply", autoplay=True)
            state = gr.State([])  # conversation history fed to the LLM
            msg = gr.Textbox(label="Say something", placeholder="Type and press Enter")

            def _turn(message, display, llm_history):
                # `display` accumulates every exchange (including blocked ones);
                # `llm_history` only carries the allowed turns to the model.
                text, video, new_llm_history = chat(message, llm_history)
                new_display = list(display or []) + [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": text},
                ]
                return new_display, video, new_llm_history, ""

            msg.submit(_turn, [msg, chatbox, state], [chatbox, reply_video, state, msg])

    return demo


def main() -> None:
    demo = build_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)


if __name__ == "__main__":
    main()
