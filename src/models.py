from pydantic import BaseModel


class Media(BaseModel):
    index: int
    name: str
    id: str
    type: str
    year: int
    series_name: str
    season: int | str
    episode: int | str

    
