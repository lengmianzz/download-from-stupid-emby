from pathlib import Path
import pytest
import os.path


import src.downloader
import src.spider

from src.downloader import saveMedia, fliterDownloadMediaIds, show_media


@pytest.mark.asyncio
async def test_saveMedia(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def donothing(*args, **kwargs):
        pass

    async def async_generator(*args, **kwargs):
        for i in [b"123456789"]:
            yield i

    monkeypatch.setattr(os, "makedirs", donothing)
    monkeypatch.setattr(src.downloader, "STREAM", async_generator)

    save_dir = tmp_path / "test_dir"
    save_dir.mkdir()
    save_file = save_dir / "test_e.mp4"
    size = 4
    media_stream = "https://test_url"

    await saveMedia(save_dir, save_file, media_stream, size)

    with open(save_dir / save_file, "rb") as f:
        content = f.read()

    assert b"123456789" == content


items = [{"name": f"test_{i}", "Id": f"100{i}", "IndexNumber": i} for i in range(8)]

items_without_zero = [
    {"name": f"test_{i}", "Id": f"100{i}", "IndexNumber": i + 1} for i in range(10)
]


@pytest.mark.parametrize(
    "items, inputs, excepted_index, excepted_id",
    [
        (items, "a", [i for i in range(8)], [f"100{i}" for i in range(8)]),
        (
            items_without_zero,
            "a",
            [i for i in range(1, 11)],
            [f"100{i}" for i in range(10)],
        ),
        (items, "2-5", [i for i in range(2, 6)], [f"100{i}" for i in range(2, 6)]),
        (
            items_without_zero,
            "2-5",
            [i for i in range(2, 6)],
            [f"100{i}" for i in range(1, 5)],
        ),
        (items, "3-", [i for i in range(3, 8)], [f"100{i}" for i in range(3, 8)]),
        (
            items_without_zero,
            "3-",
            [i for i in range(3, 11)],
            [f"100{i}" for i in range(2, 10)],
        ),
        (items, "-7", [i for i in range(8)], [f"100{i}" for i in range(8)]),
        (
            items_without_zero,
            "-7",
            [i for i in range(1, 8)],
            [f"100{i}" for i in range(7)],
        ),
        (items, "1 3 7", [1, 3, 7], ["1001", "1003", "1007"]),
        (items_without_zero, "1 3 7", [1, 3, 7], ["1000", "1002", "1006"]),
        (items, "0 4 6", [0, 4, 6], ["1000", "1004", "1006"]),
    ],
)
def test_fliterDownloadMediaIds(items, inputs, excepted_index, excepted_id):
    index, id_ = fliterDownloadMediaIds(inputs, items)

    assert excepted_index == index
    assert excepted_id == id_


@pytest.mark.asyncio
async def test_showMedias(monkeypatch, capsys):
    data = {}

    episode = {
        "Name": "鬼灭之宴特别篇（三）",
        "ServerId": "aa5e8d06ee3d454f937284b716ad851c",
        "Id": "683791",
        "CanDelete": False,
        "Container": "mkv",
        "RunTimeTicks": 1042710000,
        "ProductionYear": 2020,
        "IndexNumber": 3,
        "ParentIndexNumber": 0,
        "IsFolder": False,
        "Type": "Episode",
        "ParentBackdropItemId": "682505",
        "ParentBackdropImageTags": [...],
        "UserData": {...},
        "SeriesName": "鬼灭之刃",
        "SeriesId": "682505",
        "SeasonId": "683784",
        "PrimaryImageAspectRatio": 1.7777777777777777,
        "SeriesPrimaryImageTag": "6627fa5f10a173f27e09ca9a42b5f712",
    }
    series = {
        "Name": "鬼灭之刃",
        "ServerId": "aa5e8d06ee3d454f937284b716ad851c",
        "Id": "845375",
        "CanDelete": False,
        "RunTimeTicks": 14400000000,
        "ProductionYear": 2019,
        "IsFolder": True,
        "Type": "Series",
        "UserData": {
            "UnplayedItemCount": 9,
            "PlaybackPositionTicks": 0,
            "PlayCount": 0,
            "IsFavorite": False,
            "Played": False,
        },
        "Status": "Continuing",
        "AirDays": [],
        "PrimaryImageAspectRatio": 0.6666666666666666,
        "ImageTags": {
            "Primary": "905f490e264087b1d9441d7cd087571f",
            "Thumb": "044be01ae6d2e5502e3a89716eec1124",
        },
        "BackdropImageTags": ["10b26ca9861aa07cfe2916ce0c3f56c2"],
    }
    movie = {
        "Name": "正义联盟：神魔之战",
        "ServerId": "aa5e8d06ee3d454f937284b716ad851c",
        "Id": "1177401",
        "CanDelete": False,
        "Container": "mkv",
        "RunTimeTicks": 45424640000,
        "ProductionYear": 2015,
        "IsFolder": False,
        "Type": "Movie",
        "UserData": {
            "PlaybackPositionTicks": 0,
            "PlayCount": 0,
            "IsFavorite": False,
            "Played": False,
        },
        "PrimaryImageAspectRatio": 0.6666666666666666,
        "ImageTags": {"Primary": "da2e099d7504bb45f82f5f3698cf6a4b"},
        "BackdropImageTags": ["95ec3d0779640bae74ba7e6abcd58502"],
        "MediaType": "Video",
    }

    data["Items"] = [episode, series, movie]

    async def fake_haveWhatSeasons(*args, **kwargs):
        return [1, 2, 3, 4]

    monkeypatch.setattr(src.downloader, "haveWhatSeasons", fake_haveWhatSeasons)

    await show_media(data)

    captured = capsys.readouterr()
    assert captured.out == (
          "[0] 集名: 鬼灭之宴特别篇（三） - 鬼灭之刃[s0e3] Id: 683791\n"
        + "[1] 剧名: 鬼灭之刃[1, 2, 3, 4]季 Id: 845375\n"
        + "[2] 电影名: 正义联盟：神魔之战 Id: 1177401 发布于: 2015\n"
    )
