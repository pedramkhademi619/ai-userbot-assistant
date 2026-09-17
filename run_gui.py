"""
Launch the Rubika bot GUI. If the user has logged in before, the app
opens straight into the chat screen; otherwise it walks them through the
onboarding wizard. The bot itself only starts when the user presses
"Start" from inside the chat screen.
"""

import sys


def _force_utf8_stdio() -> None:
    """
    Windows console defaults to cp1252 / cp1256, which crashes on Persian
    characters when anything (rubpy, our code, a library warning) tries to
    print them. Reconfigure stdio to UTF-8 so a stray print never brings
    down the message handler.
    """

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


_force_utf8_stdio()


from bot.gui import launch_gui  # noqa: E402  (must run after stdio patch)


def main():
    launch_gui()


if __name__ == "__main__":
    main()
