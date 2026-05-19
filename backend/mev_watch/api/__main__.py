import uvicorn

from ..config import settings


def main() -> None:
    uvicorn.run(
        "mev_watch.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
