"""Video generation utilities for KARMA."""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("karma.utils.video")


def generate_video(
    input_path: str,
    prefix: str,
    char_id: int = 0,
    image_synthesis: Optional[List[str]] = None,
    frame_rate: int = 5,
    output_path: Optional[str] = None,
) -> None:
    """Generate a video from PNG frames using ffmpeg.

    Args:
        input_path: Root directory containing frame sequences.
        prefix: Sub-directory name containing frames.
        char_id: Character/agent ID for multi-agent scenes.
        image_synthesis: List of synthesis modes (e.g., ['normal']).
        frame_rate: Frames per second for the output video.
        output_path: Directory to write output video. Defaults to input_path.
    """
    if image_synthesis is None:
        image_synthesis = ["normal"]

    if output_path is None:
        output_path = input_path

    vid_folder = f"{input_path}/{prefix}/{char_id}/"
    vid_path = Path(vid_folder)

    if not vid_path.exists():
        logger.warning("Video input path does not exist: %s", vid_folder)
        return

    for synthesis_mode in image_synthesis:
        frame_pattern = f"{vid_folder}/Action_%04d_0_{synthesis_mode}.png"
        output_file = f"{output_path}/video_{synthesis_mode}.mp4"

        try:
            command = [
                "ffmpeg",
                "-i", frame_pattern,
                "-framerate", str(frame_rate),
                "-pix_fmt", "yuv420p",
                output_file,
                "-y",
            ]
            subprocess.run(command, check=True, capture_output=True)
            logger.info("Video generated: %s", output_file)
        except subprocess.CalledProcessError as e:
            logger.error("ffmpeg failed for %s: %s", output_file, e.stderr.decode())
        except FileNotFoundError:
            logger.error("ffmpeg not found. Please install ffmpeg.")
