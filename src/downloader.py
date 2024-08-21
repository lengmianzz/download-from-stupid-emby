import json
from pathlib import Path
import os
import os.path
from typing import Any, Dict, List, Tuple

from httpx import NetworkError, RemoteProtocolError, TransportError, TimeoutException
from tqdm import tqdm

from src.models import Media
from src.spider import GET, STREAM
from src.utils import config, MEMORY_PATH, DOWNLOAD_PATH
from src.errors import ChoiceOutRangeError, ChoiceTooMuchError, NotSupportError, ZeroinputError
        
        
async def downloadSeries(SeriesId: str) -> None:
    url = f"{config.host}/emby/Shows/{SeriesId}/Seasons?api_key={config.api_key}"
    
    data = (await GET(url)).json()
    
    selected_seasons = input("请选择要下载的季数(以空格为隔, 用-输入范围, 输入a下载整剧):\n")
      
    indexs, SeasonIds = fliterDownloadMediaIds(selected_seasons, data["Items"])
            
    for i, SeasonId in zip(indexs, SeasonIds):
        await downloadSeasons(SeriesId, SeasonId, i)
    

async def downloadSeasons(SeriesId: str, SeasonId: str, SeasonName: int) -> None:
    url = f"{config.host}/emby/Shows/{SeriesId}/Episodes?SeasonId={SeasonId}&Limit=1000&ImageTypeLimit=1&UserId={config.user_id}&api_key={config.api_key}"

    data = (await GET(url)).json()
    
    SeriesName = data["Items"][0]["SeriesName"]
    
    print(f"当前正在下载第{SeasonName}季!")
    
    for i, item in enumerate(data["Items"], 1):
        print(f"第{i}集 - {item['Name']}")

    selected_episodes = input("请选择要下载的集数(以空格为隔, 用-输入范围, 输入a下载整季):\n")
    
    indexs, EpisodeIds = fliterDownloadMediaIds(selected_episodes, data["Items"])
    
    save_dir = Path(f"{SeriesName}/第 {SeasonName} 季")
    
    for i, EpisodeId in zip(indexs, EpisodeIds):
        media_type, media_size, media_stream = await get_media_stream(EpisodeId)
        save_file = Path(f"第{i}集.{media_type}")
        await saveMedia(save_dir, save_file, media_stream, media_size)


async def saveMedia(save_dir: Path,
                    save_file: Path,
                    media_stream: str,
                    size: int,
                    saved_size: int = 0,
                    **kwargs) -> None:
    save_dir = DOWNLOAD_PATH / save_dir
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    save_path = save_dir / save_file
    
    memory_size = 0 or saved_size
    kwargs["headers"] = {"Range": f"bytes={memory_size}-"}
    
    bar = tqdm(total=size, initial=memory_size, unit_scale=True)
    
    try:
        with open(save_path, "ab") as f:
            async for chunk in STREAM(media_stream, **kwargs):
                f.write(chunk)
                bar.update(len(chunk))
            
            bar.close()
    except (TransportError, NetworkError, TimeoutException, RemoteProtocolError):
        with open(MEMORY_PATH, "r") as f:
            memorys = json.load(f)
        
        memorys["only_me"] = [(str(save_dir), str(save_file), media_stream, size)]
        
        with open(MEMORY_PATH, "w") as f:
            json.dump(memorys, f)
            
        raise
        
    
async def search_media(key: str,
                       only_series: str,
                       only_episode: str,
                       only_movies: str) -> Dict[str, Any]:
    if sum([p != "" for p in [only_series, only_episode, only_movies]]) > 1:
        raise NotSupportError("[-]不支持多个过滤!")     
    
    url = f"{config.host}/emby/Users/{config.user_id}/Items?{only_series}&{only_episode}&{only_movies}&SortBy=SortName&SortOrder=Ascending&Fields=BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,Status,EndDate&StartIndex=0&EnableImageTypes=Primary,Backdrop,Thumb&ImageTypeLimit=1&Recursive=true&SearchTerm={key}&GroupProgramsBySeries=true&Limit=50&api_key={config.api_key}"
    
    return (await GET(url)).json()


async def show_media(data: Dict[str, Any]) -> List[Media]:
    medias = [
        Media(
            **{
            "index": i,
            "name": item["Name"],
            "id": item["Id"],
            "type": item["Type"],
            "year": item.get("ProductionYear", "未知"),
            "series_name": item.get("SeriesName", "未知"),
            "season": item.get("ParentIndexNumber", "未知"),
            "episode": item.get("IndexNumber", "未知")
            }
        )
        
        for i, item in enumerate(data["Items"])
    ]
    
    for media in medias:
        match media.type:
            case "Series":
                seasons = await haveWhatSeasons(media.id)
                print(f"{[media.index]} 剧名: {media.name}{seasons}季 Id: {media.id}")
            case "Episode":
                print(f"{[media.index]} 集名: {media.name} - {media.series_name}[s{media.season}e{media.episode}] Id: {media.id}")
            case "Movie":
                print(f"{[media.index]} 电影名: {media.name} Id: {media.id} 发布于: {media.year}")
    
    return medias


async def get_media_stream(media_id: str) -> Tuple[str, int, str]:
    media_infos = f"{config.host}/emby/Items/{media_id}/PlaybackInfo?UserId={config.user_id}&api_key={config.api_key}"
        
    data = (await GET(media_infos)).json()
    
    subtitle_index = getSubtitleIndex(data)
    type_ = data["MediaSources"][0]["Container"]
    mediasource_id = data["MediaSources"][0]["Id"]
    size_ = int(data["MediaSources"][0]["Size"])
    
    return type_, size_, f"{config.host}/videos/{media_id}/stream.{type}?api_key={config.api_key}&MediaSourceId={mediasource_id }&SubtitleStreamIndex={subtitle_index}&Static=true"


async def haveWhatSeasons(SeriesId: str) -> List[int]:
    url = f"{config.host}/emby/Shows/{SeriesId}/Seasons?api_key={config.api_key}"

    data = (await GET(url)).json()
    
    return [item["IndexNumber"] for item in data["Items"]]


def getSubtitleIndex(data: Dict[str, Any]) -> int:
    for i, subtitle in enumerate(data["MediaSources"][0]["MediaStreams"]):
        lng = subtitle.get("Language", "").lower()
        title = subtitle.get("DisplayTitle", "").lower()
        
        if "chi" in lng and "simplified" in title:
            return i
        
    return 0


def fliterDownloadMediaIds(inputs: str, items: List[Dict[str, Any]]) -> Tuple[List[int], List[str]]:
    inputs = inputs.strip().lower()
    
    if not inputs: 
        raise ZeroinputError("[-]禁止空输入!")
    
    valid_min = items[0]["IndexNumber"]
    valid_max = items[-1]["IndexNumber"] + 1
    
    if inputs.lower() == "a":
        indexs = list(range(valid_min, valid_max))
        choiceIds = [item["Id"] for item in items]
    elif "-" in inputs.lower():
        start, end = inputs.split("-")
        
        start = int(start) if start else valid_min
        end = int(end) if end else valid_max - 1
        
        if end > valid_max or start < valid_min:
            raise ChoiceOutRangeError("[-]请把输入限制在范围内!")
        
        indexs = list(range(start, end + 1))
        
        choiceIds = [item["Id"] for item in items
                     if item["IndexNumber"] in indexs]
    else: 
        indexs = list(map(int, inputs.split()))
        choiceIds = [item["Id"] for item in items
                     if item["IndexNumber"] in indexs]
        
    if len(indexs) > len(items):
        raise ChoiceTooMuchError("请不要超出范围")
    
    return indexs, choiceIds
