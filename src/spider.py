import asyncio
from functools import wraps
from typing import AsyncGenerator, TypeVar, Callable, Any
from loguru import logger

from httpx import AsyncClient, Response 

from src.utils import PROXY, config


T = TypeVar('T', bound=Callable[..., Any])


def retry(tries: int = 4, delay: int = 3) -> Callable[[T], T]:
    def deco_retry(f: T) -> T:
        @wraps(f)
        async def f_retry(*args, **kwargs) -> Any:
            mtries, mdelay = tries, delay
 
            while mtries > 1:
                try:         
                    return await f(*args, **kwargs)
                except Exception:
                    logger.warning(
                        f"第{tries - mtries + 1}尝试请求失败, 将在{mdelay}秒后重试"
                    )
                    
                    await asyncio.sleep(mdelay)
                    
                    mtries -= 1
                    mdelay *= 2
            
            return await f(*args, **kwargs)
 
        return f_retry  #type: ignore
 
    return deco_retry


@retry()
async def GET(url: str, **kwargs) -> Response:
    client = AsyncClient(timeout=10, proxy=PROXY)
            
    return await client.get(url, follow_redirects=True, **kwargs)
        
        
@retry()
async def POST(url: str, **kwargs) -> Response:
    client = AsyncClient(timeout=10, proxy=PROXY)
        
    return await client.post(url, follow_redirects=True, **kwargs)


async def STREAM(url: str, **kwargs) -> AsyncGenerator[bytes, None]:
    client = AsyncClient(timeout=10, proxy=PROXY)
    
    async with client.stream('GET', url, follow_redirects=True, **kwargs) as res:
        async for chunk in res.aiter_bytes(chunk_size=1024):
            yield chunk
            
        
async def get_server_name() -> str:
    url = f"{config.host}/emby/system/info/public"
    
    data = (await GET(url)).json()
    
    return data["ServerName"]


async def login(user_name: str, password: str) -> None:
    server_name = await get_server_name()
    
    if config.user_id and config.api_key:
        print(f"[+]使用token登入{server_name}成功!")
        return 
    
    login_url = f"{config.host}/emby/Users/authenticatebyname?X-Emby-Client=Emby%20WebX-Emby-Device-Id=1e202193-5444-4556-9f5a-adf97faa0735&X-Emby-Client-Version=4.7.11.0&X-Emby-Language=zh-cn"
    
    data = {
        "Username": user_name,
        "Pw": password
    }
        
    data = (await POST(login_url, data=data)).json()
    
    config.user_id = data['User']['Id']
    config.api_key = data['AccessToken']
    
    print(f"[+]使用账户密码登入{server_name}成功!")