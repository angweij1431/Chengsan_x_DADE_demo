from moviepy import ColorClip


def create_video():

    output_path = "videos/my_video.mp4"

    video = ColorClip(
        size=(1280, 720),
        color=(0, 0, 0),
        duration=10
    )

    video.write_videofile(
        output_path,
        fps=30,
        audio=False
    )

    video.close()

    return output_path