from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    github_step_summary: str | None = None


settings = Settings.model_validate({})
_summary_initialized = False


@contextmanager
def ci_step(label: str) -> Generator[None]:
    global _summary_initialized
    print(f"::group::{label}", flush=True)
    start = time.monotonic()
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        duration = time.monotonic() - start
        print("::endgroup::", flush=True)

        if settings.github_step_summary:
            if duration < 60:
                formatted_duration = f"{duration:.1f}s"
            else:
                minutes = int(duration // 60)
                formatted_duration = f"{minutes}m {duration % 60:.0f}s"

            with open(settings.github_step_summary, "a") as file:
                if not _summary_initialized:
                    file.write("| Step | Duration |\n|---|---|\n")
                    _summary_initialized = True
                status = " :x:" if failed else ""
                file.write(f"| {label}{status} | {formatted_duration} |\n")
