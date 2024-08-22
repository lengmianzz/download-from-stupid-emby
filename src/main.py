import argparse
import asyncio
import json
import os
import shlex
from pathlib import Path
import sys
from typing import Dict, List, Tuple

from src.downloader import (
    get_media_stream,
    saveMedia,
    search_media,
    downloadSeries,
    show_media,
)
from src.spider import login
from src.utils import config, MEMORY_PATH
from src.errors import LackConfigError


async def readMemoryAndReDownload(
    memory: Dict[str, List[Tuple[Path, Path, str, int]]]
) -> None:
    args = memory["only_me"][0]

    save_dir = Path(args[0])
    save_file = Path(args[1])
    size = os.path.getsize(save_dir / save_file)

    args = args[2:]

    await saveMedia(save_dir, save_file, *args, headers={"Range": f"bytes={size}-"})

    with open(MEMORY_PATH, "w") as f:
        json.dump({}, f)


async def main() -> None:
    if not all([config.host, config.user_name, config.password]):
        raise LackConfigError("[-]请填写完配置再运行项目")

    with open(MEMORY_PATH, "r") as f:
        memorys = json.load(f)

    if memorys:
        choice = input("检测到上次的资源没有下载完, 请问是否继续下载(y/n)?")
        if choice == "y":
            await readMemoryAndReDownload(memorys)

            return

    parser = argparse.ArgumentParser(description="过滤搜索结果")
    parser.add_argument("key", type=str)
    parser.add_argument(
        "-s",
        dest="only_series",
        action="store_const",
        const="Filters=IsFolder",
        default="",
    )
    parser.add_argument(
        "-e",
        dest="only_episode",
        action="store_const",
        const="Filters=IsNotFolder",
        default="",
    )
    parser.add_argument(
        "-m",
        dest="only_movies",
        action="store_const",
        const="IsMovie=True",
        default=""
    )

    await login(config.user_name, config.password)

    text = input("请输入要搜索的关键词[-s过滤系列, -e过滤单集, -m过滤电影]:\n")

    params = parser.parse_args(shlex.split(text)).__dict__

    data = await search_media(**params)

    if not data["Items"]:
        print("[-]未搜索到任何结果!")
        sys.exit(0)

    medias = await show_media(data)

    index = int(input("请选择要下载的标号:\n"))
    choiced_media = medias[index]

    match choiced_media.type:
        case "Series":
            await downloadSeries(choiced_media.id)
        case "Episode":
            _, media_size, media_stream = await get_media_stream(choiced_media.id)

            save_dir = Path(f"{choiced_media.series_name}/第{ choiced_media.season }季")
            save_file = Path(f"第{choiced_media.name}集/{choiced_media.type}")

            await saveMedia(save_dir, save_file, media_stream, media_size)

            print(f"[+]下载{save_dir}{save_file}成功!")
        case "Movie":
            _, media_size, media_stream = await get_media_stream(choiced_media.id)

            await saveMedia(
                Path(choiced_media.name),
                Path(choiced_media.name),
                media_stream,
                media_size,
            )

            print(f"[+]下载{choiced_media.name}成功!")


if __name__ == "__main__":
    asyncio.run(main())
