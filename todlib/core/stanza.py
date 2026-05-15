from ..utils import util

def message(to: str, body: str, msg_id: str = "", msg_type: str = "c") -> str:
    mid = msg_id or util.generate_token(8)
    body_esc = util.escape_xml(body)
    return (
        f"<m to='{to}' t='{msg_type}' i='{mid}' xmlns='jc'>"
        f"<k xmlns='x8'/>"
        f"<b>{body_esc}</b>"
        f"</m>"
    )

def file_message(to: str, url: str, file_type: int, caption: str = "", msg_id: str = "", msg_type: str = "c", file_name: str = "", file_size: int = 0) -> str:
    mid = msg_id or util.generate_token(8)
    fid = util.generate_token(16)
    cap_esc = util.escape_xml(caption)
    name_esc = util.escape_xml(file_name)
    return (
        f"<m to='{to}' t='{msg_type}' i='{mid}' xmlns='jc'>"
        f"<k xmlns='x8'/>"
        f"<b>{cap_esc}</b>"
        f"<file xmlns='file:n' i='{fid}' mi='{mid}' n='{name_esc}' url='{util.escape_xml(url)}' s='{file_size}' h=''/>"
        f"</m>"
    )

def contact_message(to: str, contact_id: str, contact_name: str, contact_phone: str, msg_id: str = "", msg_type: str = "c") -> str:
    mid = msg_id or util.generate_token(8)
    name_esc = util.escape_xml(contact_name)
    return (
        f"<m to='{to}' t='{msg_type}' i='{mid}' xmlns='jc'>"
        f"<k xmlns='x8'/>"
        f"<contact xmlns='contact:n' i='{contact_id}' mi='{mid}' n='{name_esc}' num='{contact_phone}'/>"
        f"<b/>"
        f"</m>"
    )

def sticker_message(to: str, sticker_id: str, sticker_name: str, sticker_pack: str, sticker_hash: str, msg_id: str = "", msg_type: str = "c") -> str:
    mid = msg_id or util.generate_token(8)
    name_esc = util.escape_xml(sticker_name)
    pack_esc = util.escape_xml(sticker_pack)
    return (
        f"<m to='{to}' t='{msg_type}' i='{mid}' xmlns='jc'>"
        f"<k xmlns='x8'/>"
        f"<sticker xmlns='sticker:n' i='{sticker_id}' mi='{mid}' n='{name_esc}' f='{pack_esc}' url='' s='0' h='{sticker_hash}' json=''/>"
        f"<b/>"
        f"</m>"
    )

def video_message(to: str, url: str, video_id: str, file_name: str, file_size: int, duration: int, width: int, height: int, thumbnail: str, msg_id: str = "", msg_type: str = "c") -> str:
    mid = msg_id or util.generate_token(8)
    name_esc = util.escape_xml(file_name)
    url_esc = util.escape_xml(url)
    return (
        f"<m to='{to}' t='{msg_type}' i='{mid}' xmlns='jc'>"
        f"<k xmlns='x8'/>"
        f"<video xmlns='video:n' i='{video_id}' mi='{mid}' url='{url_esc}' s='{file_size}' h='' d='{duration}' n='{name_esc}' w='{width}' he='{height}' tnail='{thumbnail}'/>"
        f"<b/>"
        f"</m>"
    )

def presence(status: str = "Online", priority: int = 5, show: str = "", caps: bool = True) -> str:
    cap = ""
    if caps:
        cap = (
            "<c ver='foVtX1ZDcopvf5CM63LcnVayPRs=' "
            "node='http://www.process-one.net/en/ejabberd/' "
            "hash='sha-1' xmlns='http://jabber.org/protocol/caps'/>"
        )
    show_tag = f"<show>{show}</show>" if show else ""
    return (
        f"<presence xmlns='jc'>"
        f"<status>{util.escape_xml(status)}</status>"
        f"{show_tag}"
        f"<priority>{priority}</priority>"
        f"{cap}"
        f"</presence>"
    )

def iq(type_: str, iq_id: str, payload: str = "", to: str = "") -> str:
    to_attr = f" to='{to}'" if to else ""
    return f"<iq i='{iq_id}' t='{type_}'{to_attr}>{payload}</iq>"

def ping(ping_id: str) -> str:
    return f"<iq i='{ping_id}' t='get'><ping xmlns='urn:xmpp:ping'/></iq>"

def chat_state(to: str, state: str) -> str:
    return (
        f"<message to='{to}' t='chat' xmlns='jc'>"
        f"<{state} xmlns='http://jabber.org/protocol/chatstates'/>"
        f"</message>"
    )

def receipt(to: str, msg_id: str) -> str:
    return (
        f"<message to='{to}' t='chat' xmlns='jc'>"
        f"<received xmlns='urn:xmpp:receipts' id='{msg_id}'/>"
        f"</message>"
    )

def read_receipt(to: str, msg_id: str) -> str:
    return (
        f"<message to='{to}' t='chat' xmlns='jc'>"
        f"<read xmlns='urn:xmpp:read-receipts' id='{msg_id}'/>"
        f"</message>"
    )

def stream_open(host: str = "im.todus.cu") -> str:
    return f"<stream:stream xmlns='jc' o='{host}' xmlns:stream='x1' v='1.0'>"

def stream_restart(host: str = "im.todus.cu") -> str:
    return f"<stream:stream xmlns='jc' o='{host}' xmlns:stream='x1' v='1.0'>"

def stream_close() -> str:
    return "</stream:stream>"

def sasl_auth(authstr: bytes) -> str:
    return b"<ah xmlns='ah:ns' e='PLAIN'>" + authstr + b"</ah>"

def bind(iq_id: str) -> str:
    return f"<iq i='{iq_id}' t='set'><b1 xmlns='x4'></b1></iq>"

def mam_query(query_id: str, since: str = "", before: str = "", limit: int = 50) -> str:
    filters = ""
    if since:
        filters += f"<start>{since}</start>"
    if before:
        filters += f"<end>{before}</end>"
    return (
        f"<iq i='{query_id}' t='set'>"
        f"<query xmlns='todus:mam'>{filters}"
        f"<set xmlns='http://jabber.org/protocol/rsm'><max>{limit}</max></set>"
        f"</query></iq>"
    )

def upload_query(iq_id: str, size: int, file_type: int, persistent: bool = False) -> str:
    persist = "true" if persistent else "false"
    return (
        f"<iq i='{iq_id}-3' t='get'>"
        f"<query xmlns='todus:purl' type='{file_type}' "
        f"persistent='{persist}' size='{size}' room=''></query>"
        f"</iq>"
    )

def download_query(iq_id: str, url: str) -> str:
    return (
        f"<iq i='{iq_id}-2' t='get'>"
        f"<query xmlns='todus:gurl' url='{url}'></query>"
        f"</iq>"
    )