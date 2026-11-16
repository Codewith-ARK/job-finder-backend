from vercel.blob import sync as blob


def upload(pathname: str, data: bytes, content_type: str) -> str:
    blob.put_blob(pathname, data, access="private", content_type=content_type)
    return pathname  # DB mein pathname save karo, URL nahi

def download(pathname: str) -> tuple[bytes, str | None]:
    r = blob.get_blob(pathname, access="private")
    return r.body, r.metadata.content_type

def remove(pathname: str) -> None:
    blob.delete_blob(pathname)
