import json
import logging
from io import BufferedReader
from typing import Any, Dict, List, cast

import requests

from dj_telegram_bot.core.exceptions import TelegramAPIError
from dj_telegram_bot.core.types import (
    AcceptedGiftTypes,
    BotAccessSettings,
    BotCommand,
    BotCommandList,
    BotCommandScope,
    BotCommandScopeDefault,
    BotDescription,
    BotName,
    BotShortDescription,
    BusinessConnection,
    ChatAdministratorRights,
    ChatFullInfo,
    ChatInviteLink,
    ChatMember,
    ChatMemberAdapter,
    ChatPermissions,
    File,
    ForumTopic,
    GameHighScore,
    Gift,
    InlineKeyboardMarkup,
    InlineQueryResult,
    InlineQueryResultsButton,
    InputChecklist,
    InputFile,
    InputMedia,
    InputPaidMedia,
    InputPollMedia,
    InputPollOption,
    InputProfilePhoto,
    InputRichMessage,
    InputSticker,
    InputStoryContent,
    KeyboardButton,
    LabeledPrice,
    LinkPreviewOptions,
    MaskPosition,
    MenuButton,
    MenuButtonAdapter,
    MenuButtonDefault,
    Message,
    MessageEntity,
    MessageId,
    MessageIdList,
    MessageListAdapter,
    OwnedGift,
    OwnedGiftAdapter,
    PassportElementError,
    Poll,
    PreparedInlineMessage,
    PreparedKeyboardButton,
    ReactionType,
    ReplyMarkup,
    ReplyParameters,
    SentGuestMessage,
    SentWebAppMessage,
    ShippingOption,
    StarAmount,
    StarTransactions,
    Sticker,
    StickerList,
    StickerSet,
    Story,
    StoryArea,
    SuggestedPostParameters,
    User,
    UserChatBoosts,
    UserProfileAudios,
    UserProfilePhotos,
)

logger = logging.getLogger(__name__)


class Telegram:
    """
    A typed, production-ready client for the Telegram Bot API,
    built around clean architecture and maintainability.
    """

    HEADERS: Dict[str, str] = {"Cache-Control": "no-cache"}
    UNKNOWN_ERROR = 0

    def __init__(self, token: str, webhook_url: str, proxy_socks: str | None = None):
        self._validate_config(token, webhook_url)
        self.token = token
        self.webhook = webhook_url

        self.proxy = self._setup_proxy(proxy_socks)
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)

    def _validate_config(self, token, webhook_url):
        """Ensure all required environment variables are present."""
        if not token:
            raise ValueError("BOT_TOKEN is required.")

        if not webhook_url:
            raise ValueError("TM_WEBHOOK_URL is required.")

    def _setup_proxy(self, proxy_socks) -> Dict[str, str] | None:
        """Configure SOCKS5 proxy if provided."""
        if proxy_socks:
            return {
                "http": f"socks5h://{proxy_socks}",
                "https": f"socks5h://{proxy_socks}",
            }
        return {}

    def _make_request(
        self,
        method_name: str,
        method: str = "POST",
        data: Dict[Any, Any] | None = None,
        params: Dict[Any, Any] | None = None,
        files: Dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> Dict[Any, Any]:
        """
        Send HTTP request to Telegram Bot API.
        """
        url = f"{self.webhook}/bot{self.token}/{method_name}"
        params = self._clean_dict(params)
        data = self._clean_dict(data)
        response = None
        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url, params=params, proxies=self.proxy, timeout=timeout
                )
            else:
                response = self._session.post(
                    url,
                    data=data,
                    params=params,
                    files=files,
                    timeout=100,
                    proxies=self.proxy,
                )

            json_data = response.json()

        except Exception as error:
            raise TelegramAPIError(method_name, self.UNKNOWN_ERROR, str(error))

        if not json_data.get("ok", False):
            raise TelegramAPIError(
                method_name,
                json_data.get("error_code"),
                json_data.get("description", "Unknown error"),
            )

        return json_data["result"]

    def _clean_dict(self, data: Dict[str, Any] | None) -> Dict[str, Any] | None:
        """Remove None values and convert nested dicts to JSON strings."""
        if data is None:
            return None

        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue

            if isinstance(value, list):
                cleaned_list = [
                    item.model_dump(exclude_none=True)
                    if hasattr(item, "model_dump")
                    else item
                    for item in value
                ]
                cleaned[key] = json.dumps(cleaned_list, ensure_ascii=False)
                continue

            if hasattr(value, "model_dump"):
                value = value.model_dump(exclude_none=True)

            if isinstance(value, dict):
                cleaned[key] = json.dumps(value, ensure_ascii=False)
            else:
                cleaned[key] = value

        return cleaned

    def _add_file(
        self,
        field_name,
        file_name,
        file_obj,
        payload,
        thumbnail=None,
        cover=None,
        files=None,
    ):
        files = {} if files is None else files

        if isinstance(file_obj, BufferedReader):
            files[field_name] = (
                file_name or getattr(file_obj, "name", field_name),
                file_obj,
            )

        elif isinstance(file_obj, bytes):
            files[field_name] = (file_name or field_name, file_obj)

        elif isinstance(file_obj, str):
            payload[field_name] = file_obj

        else:
            raise ValueError(f"Unsupported type for {field_name}")

        if thumbnail:
            if isinstance(thumbnail, (bytes, BufferedReader)):
                thumb_name = getattr(thumbnail, "name", "thumb.jpg")
                files["thumbnail"] = (thumb_name, thumbnail)
                payload["thumbnail"] = "attach://thumbnail"
            else:
                payload["thumbnail"] = thumbnail

        if cover:
            if isinstance(cover, (bytes, BufferedReader)):
                cover_name = os.path.basename(getattr(cover, "name", "cover.jpg"))
                files["cover"] = (cover_name, cover)
                payload["cover"] = "attach://cover"
            else:
                payload["cover"] = cover

        return payload, files

    def close(self):
        """Close the session."""
        self._session.close()

    def get_me(self) -> User:
        response = self._make_request("getMe", method="GET")
        return User.model_validate(response)

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        parse_mode: str | None = "html",
        entities: List[MessageEntity] | None = None,
        link_preview_options: LinkPreviewOptions | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send text messages to a chat, user, group or channel.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            text: Text of the message to be sent, 1-4096 characters after entities parsing.
            parse_mode: Mode for parsing entities in the message text. ("html" or "MarkdownV2").

            See full parameters here: [sendMessage](https://core.telegram.org/bots/api#sendmessage)
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "parse_mode": parse_mode,
            "entities": entities,
            "link_preview_options": link_preview_options,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }

        response = self._make_request("sendMessage", data=payload)
        message = Message.model_validate(response)
        return message

    def forward_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        video_start_timestamp: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
    ) -> Message:
        """
        Forward messages of any kind.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            from_chat_id: Chat ID where the original message was sent, or @username of the target bot/supergroup/channel.
            message_id: Message identifier in the chat specified in from_chat_id.

            See full parameters here: [forwardMessage](https://core.telegram.org/bots/api#forwardmessage)
        """
        payload = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "video_start_timestamp": video_start_timestamp,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "suggested_post_parameters": suggested_post_parameters,
            "message_effect_id": message_effect_id,
        }
        response = self._make_request("forwardMessage", data=payload)
        message = Message.model_validate(response)
        return message

    def forward_messages(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_ids: List[int],
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
    ) -> List[MessageId]:
        """
        Forward multiple messages of any kind.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            from_chat_id: Chat ID where the original message was sent, or @username of the target bot/supergroup/channel.
            message_ids: List of message IDs (1-100) to forward. Must be in strictly increasing order.

            See full parameters here: [forwardMessages](https://core.telegram.org/bots/api#forwardmessages)
        """
        payload = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_ids": message_ids,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
        }
        response = self._make_request("forwardMessages", data=payload)
        return MessageIdList.validate_python(response or [])

    def copy_message(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_id: int,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        video_start_timestamp: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> MessageId:
        """
        Copy messages of any kind.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            from_chat_id: Chat ID where the original message was sent, or @username of the target bot/supergroup/channel.
            message_id: Message identifier in the chat specified in from_chat_id.

            See full parameters here: [copyMessage](https://core.telegram.org/bots/api#copymessage)
        """
        payload = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "video_start_timestamp": video_start_timestamp,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("copyMessage", data=payload)
        msg_id = MessageId.model_validate(response)
        return msg_id

    def copy_messages(
        self,
        chat_id: int | str,
        from_chat_id: int | str,
        message_ids: List[int],
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        remove_caption: bool | None = None,
    ) -> List[MessageId]:
        """
        Copy messages of any kind.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            from_chat_id: Unique identifier for the chat where the original messages were sent (or username of the target bot,
                supergroup or channel in the format @username).
            message_ids: A list of 1-100 identifiers of messages in the chat from_chat_id to copy.
                The identifiers must be specified in a strictly increasing order.

            See full parameters here: [copymessages](https://core.telegram.org/bots/api#copymessages)
        """
        payload = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_ids": message_ids,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "remove_caption": remove_caption,
        }
        response = self._make_request("copyMessages", data=payload)
        return MessageIdList.validate_python(response or [])

    def send_photo(
        self,
        chat_id: int | str,
        photo: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        has_spoiler: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send a photo to a chat.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            photo: Photo to send. Pass a file_id as String to send a photo that exists
                on the Telegram servers (recommended), pass an HTTP URL as a String for Telegram to
                get a photo from the Internet, or upload a new photo using multipart/form-data.
                The photo must be at most 10 MB in size. The photo's width and height must not exceed 10000 in total.
                Width and height ratio must be at most 20.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendPhoto](https://core.telegram.org/bots/api#sendphoto)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file("photo", file_name, photo, payload)
        response = self._make_request(
            "sendPhoto", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_live_photo(
        self,
        chat_id: int | str,
        live_photo: InputFile | str,
        photo: InputFile | str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        has_spoiler: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send live photos.

        Args:
            chat_id: Unique identifier for the target chat or username of the target channel (in the format @channelusername).
            live_photo: Live photo video to send. The video must be no longer than 10 seconds and
                must not exceed 10 MB in size. Pass a file_id as String to send a video that exists on
                the Telegram servers (recommended) or upload a new video using multipart/form-data.
                More information on [Sending Files](https://core.telegram.org/bots/api#sending-files)
                Sending live photos by a URL is currently unsupported.
            photo: The static photo to send. Pass a file_id as String to send a photo that exists on
                the Telegram servers (recommended) or upload a new video using multipart/form-data.
                More information on [Sending Files](https://core.telegram.org/bots/api#sending-files).
                Sending live photos by a URL is currently unsupported.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendLivePhoto](https://core.telegram.org/bots/api#sendlivephoto)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file("live_photo", file_name, live_photo, payload)
        payload, files = self._add_file("photo", file_name, photo, payload, files=files)
        response = self._make_request(
            "sendLivePhoto", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_audio(
        self,
        chat_id: int | str,
        audio: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        duration: int | None = None,
        performer: str | None = None,
        title: str | None = None,
        thumbnail: str | InputFile | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send an audio file (e.g., music) to be displayed in the music player.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            audio: Audio file to send. Pass a file_id as String to send an audio file that exists on
                the Telegram servers (recommended), pass an HTTP URL as a String for Telegram to get
                an audio file from the Internet, or upload a new one using multipart/form-data.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendAudio](https://core.telegram.org/bots/api#sendaudio)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "duration": duration,
            "performer": performer,
            "title": title,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file("audio", file_name, audio, payload, thumbnail)
        response = self._make_request(
            "sendAudio", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_document(
        self,
        chat_id: int | str,
        document: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        thumbnail: str | InputFile | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        disable_content_type_detection: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send a general file to a chat. Uses GET for file_id/URL, POST for raw bytes.

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            document: File to send. Can be a file_id (str), URL (str), or raw bytes.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendDocument](https://core.telegram.org/bots/api#senddocument)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "disable_content_type_detection": disable_content_type_detection,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file(
            "document", file_name, document, payload, thumbnail
        )
        response = self._make_request(
            "sendDocument", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_video(
        self,
        chat_id: int | str,
        video: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        duration: int | None = None,
        width: int | None = None,
        height: int | None = None,
        thumbnail: str | InputFile | None = None,
        cover: str | InputFile | None = None,
        start_timestamp: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        has_spoiler: bool | None = None,
        supports_streaming: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send a video file to a chat. Uses GET for file_id/URL, POST for raw bytes.

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            video: Video to send. Can be a file_id (str), URL (str), or raw bytes.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendVideo](https://core.telegram.org/bots/api#sendvideo)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "duration": duration,
            "width": width,
            "height": height,
            "start_timestamp": start_timestamp,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "has_spoiler": has_spoiler,
            "supports_streaming": supports_streaming,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file(
            "video", file_name, video, payload, thumbnail, cover
        )
        response = self._make_request(
            "sendVideo", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_animation(
        self,
        chat_id: int | str,
        animation: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        duration: int | None = None,
        width: int | None = None,
        height: int | None = None,
        thumbnail: str | InputFile | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        has_spoiler: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send an animation file (GIF or H.264/MPEG-4 AVC video without sound).

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            animation: Animation to send. Can be a file_id (str), URL (str), or raw bytes.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendAnimation](https://core.telegram.org/bots/api#sendanimation)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "duration": duration,
            "width": width,
            "height": height,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "has_spoiler": has_spoiler,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file(
            "video", file_name, animation, payload, thumbnail
        )
        response = self._make_request(
            "sendAnimation", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_voice(
        self,
        chat_id: int | str,
        voice: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        duration: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send a voice message (audio file displayed as voice message).

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            voice: Voice file to send. Can be a file_id (str), URL (str), or raw bytes (.OGG with OPUS, .MP3, .M4A).
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendVoice](https://core.telegram.org/bots/api#sendvoice)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "duration": duration,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file("voice", file_name, voice, payload)
        response = self._make_request(
            "sendVoice", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_video_note(
        self,
        chat_id: int | str,
        video_note: str | InputFile,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        duration: int | None = None,
        length: int | None = None,
        thumbnail: str | InputFile | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
        file_name: str = "",
    ) -> Message:
        """
        Send a video note (round video message).

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            video_note: Video note to send. Can be a file_id (str) or raw bytes. Sending via URL is not supported.
            file_name: Optional custom filename with format suffix(e.g., 'test.png').

            See full parameters here: [sendVideoNote](https://core.telegram.org/bots/api#sendvideonote)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "duration": duration,
            "length": length,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        payload, files = self._add_file(
            "video_note", file_name, video_note, payload, thumbnail
        )
        response = self._make_request(
            "sendVideoNote", method="POST", data=payload, files=files if files else None
        )
        return Message.model_validate(response)

    def send_paid_media(
        self,
        chat_id: int | str,
        star_count: int,
        media: List[InputPaidMedia],
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        payload: str | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send paid media that requires Telegram Stars to access.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            star_count: Number of Telegram Stars required to access the media (1–10000).
            media: A list of InputPaidMedia objects (e.g., photo, video) describing the media to send (up to 10 items).

            See full parameters here: [sendPaidMedia](https://core.telegram.org/bots/api#sendpaidmedia)
        """
        payload_data = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "star_count": star_count,
            "media": media,
            "payload": payload,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendPaidMedia", method="POST", data=payload_data)
        return Message.model_validate(response)

    def send_media_group(
        self,
        chat_id: int | str,
        media: List[InputPaidMedia],
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        reply_parameters: ReplyParameters | None = None,
    ) -> Message:
        """
        Send a group of photos, videos, documents, or audios as an album.

        Args:
            chat_id: Unique identifier for the target chat or username of the target channel (e.g. @channelusername).
            media: A InputPaidMedia array describing messages to be sent, must include 2-10 items.

            See full parameters here: [sendMediaGroup](https://core.telegram.org/bots/api#sendmediagroup)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "media": media,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "reply_parameters": reply_parameters,
        }
        response = self._make_request("sendMediaGroup", method="POST", data=payload)
        return Message.model_validate(response)

    def send_location(
        self,
        chat_id: int | str,
        latitude: float,
        longitude: float,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        horizontal_accuracy: float | None = None,
        live_period: int | None = None,
        heading: int | None = None,
        proximity_alert_radius: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send a point on the map.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            latitude: Latitude of the location.
            longitude: Longitude of the location.

            See full parameters here: [sendLocation](https://core.telegram.org/bots/api#sendlocation)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "latitude": latitude,
            "longitude": longitude,
            "horizontal_accuracy": horizontal_accuracy,
            "live_period": live_period,
            "heading": heading,
            "proximity_alert_radius": proximity_alert_radius,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendLocation", method="POST", data=payload)
        return Message.model_validate(response)

    def send_venue(
        self,
        chat_id: int | str,
        latitude: float,
        longitude: float,
        title: str,
        address: str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        foursquare_id: str | None = None,
        foursquare_type: str | None = None,
        google_place_id: str | None = None,
        google_place_type: str | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send information about a venue.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            latitude: Latitude of the venue.
            longitude: Longitude of the venue.
            title: Name of the venue.
            address: Address of the venue.

            See full parameters here: [sendVenue](https://core.telegram.org/bots/api#sendvenue)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "latitude": latitude,
            "longitude": longitude,
            "title": title,
            "address": address,
            "foursquare_id": foursquare_id,
            "foursquare_type": foursquare_type,
            "google_place_id": google_place_id,
            "google_place_type": google_place_type,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendVenue", method="POST", data=payload)
        return Message.model_validate(response)

    def send_contact(
        self,
        chat_id: int | str,
        phone_number: str,
        first_name: str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        last_name: str | None = None,
        vcard: str | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send a phone contact.

        Args:
            chat_id: Unique identifier for the target chat or username of the target channel (e.g. @channelusername).
            phone_number: Contact's phone number.
            first_name: Contact's first name.

            See full parameters here: [sendContact](https://core.telegram.org/bots/api#sendcontact)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "phone_number": phone_number,
            "first_name": first_name,
            "last_name": last_name,
            "vcard": vcard,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendContact", method="POST", data=payload)
        return Message.model_validate(response)

    def send_poll(
        self,
        chat_id: int | str,
        question: str,
        options: List[InputPollOption],
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        question_parse_mode: str | None = None,
        question_entities: List[MessageEntity] | None = None,
        is_anonymous: bool | None = None,
        poll_type: str | None = None,
        allows_revoting: bool | None = None,
        shuffle_options: bool | None = None,
        allows_multiple_answers: bool | None = None,
        allow_adding_options: bool | None = None,
        hide_results_until_closes: bool | None = None,
        members_only: bool | None = None,
        country_codes: List[str] | None = None,
        correct_option_ids: List[int] | None = None,
        explanation: str | None = None,
        explanation_parse_mode: str | None = None,
        explanation_entities: List[MessageEntity] | None = None,
        explanation_media: InputPollMedia | None = None,
        open_period: int | None = None,
        close_date: int | None = None,
        is_closed: bool | None = None,
        description: str | None = None,
        description_parse_mode: str | None = None,
        description_entities: List[MessageEntity] | None = None,
        media: InputPollMedia | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send a native poll.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel. Polls can't be sent
                to channel direct messages chats.
            question: Poll question (1–300 characters).
            options: List of answer options (2–12 options, each 1–100 characters).

            See full parameters here: [sendPoll](https://core.telegram.org/bots/api#sendpoll)
        """
        payload = {
            "chat_id": chat_id,
            "question": question,
            "options": options,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "question_parse_mode": question_parse_mode,
            "question_entities": question_entities,
            "is_anonymous": is_anonymous,
            "poll_type": poll_type,
            "allows_revoting": allows_revoting,
            "shuffle_options": shuffle_options,
            "allows_multiple_answers": allows_multiple_answers,
            "allow_adding_options": allow_adding_options,
            "hide_results_until_closes": hide_results_until_closes,
            "members_only": members_only,
            "country_codes": country_codes,
            "correct_option_ids": correct_option_ids,
            "explanation": explanation,
            "explanation_parse_mode": explanation_parse_mode,
            "explanation_entities": explanation_entities,
            "explanation_media": explanation_media,
            "open_period": open_period,
            "close_date": close_date,
            "is_closed": is_closed,
            "description": description,
            "description_parse_mode": description_parse_mode,
            "description_entities": description_entities,
            "media": media,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendPoll", method="POST", data=payload)
        return Message.model_validate(response)

    def send_checklist(
        self,
        business_connection_id: str,
        chat_id: int,
        checklist: InputChecklist,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        message_effect_id: str | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message:
        """
        Send a checklist on behalf of a connected business account.

        Args:
            chat_id: Chat ID or @username of the target chat/bot.
            checklist: A InputChecklist object for the checklist to send.
            business_connection_id: Unique identifier of the business connection on behalf of which the message will be sent.

            See full parameters here: [sendChecklist](https://core.telegram.org/bots/api#sendchecklist)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "checklist": checklist,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "message_effect_id": message_effect_id,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendChecklist", method="POST", data=payload)
        return Message.model_validate(response)

    def send_dice(
        self,
        chat_id: int | str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        emoji: str | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send an animated emoji that displays a random value (e.g., dice, target, slot machine).

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.

            See full parameters here: [sendDice](https://core.telegram.org/bots/api#senddice)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "emoji": emoji,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendDice", method="POST", data=payload)
        return Message.model_validate(response)

    def send_message_draft(
        self,
        chat_id: int | str,
        draft_id: int,
        text: str,
        message_thread_id: int | None = None,
        parse_mode: str | None = "html",
        entities: List[MessageEntity] | None = None,
    ) -> bool:
        """
        Use this method to stream a partial message to a user while the message is being generated;
        supported only for bots with forum topic mode enabled.

        Args:
            chat_id: Unique identifier for the target private chat.
            draft_id: Unique identifier of the message draft; must be non-zero.
                Changes to drafts with the same identifier are animated.
            text: Text of the message to be sent, 0-4096 characters after entities parsing.
                Pass an empty text to show a `Thinking...` placeholder.

            See full parameters here: [sendMessageDraft](https://core.telegram.org/bots/api#sendmessagedraft)
        """
        payload = {
            "chat_id": chat_id,
            "draft_id": draft_id,
            "text": text,
            "message_thread_id": message_thread_id,
            "parse_mode": parse_mode,
            "entities": entities,
        }
        response = self._make_request("sendMessageDraft", method="POST", data=payload)
        return bool(response)

    def send_chat_action(
        self,
        chat_id: int | str,
        action: str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
    ) -> bool:
        """
        Tell the user that something is happening on the bot's side (e.g., typing, uploading photo).

        Args:
            chat_id: Target chat ID or @username (bot/supergroup). Channels not supported.
            action: Type of action to broadcast. Possible values:
                'typing' - for text messages,
                'upload_photo' - for photos,
                'record_video', 'upload_video' - for videos,
                'record_voice', 'upload_voice' - for voice notes,
                'upload_document' - for general files,
                'choose_sticker' - for stickers,
                'find_location' - for location data,
                'record_video_note', 'upload_video_note' - for video notes.

            See full parameters here: [sendChatAction](https://core.telegram.org/bots/api#sendchataction)
        """
        payload = {
            "chat_id": chat_id,
            "action": action,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request("sendChatAction", method="POST", data=payload)
        return bool(response)

    def set_message_reaction(
        self,
        chat_id: int | str,
        message_id: int,
        reaction: List[ReactionType] | None = None,
        is_big: bool | None = None,
    ) -> bool:
        """
        Change the chosen reactions on a message.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            message_id: Identifier of the target message. If the message belongs to a media group,
                the reaction is set to the first non-deleted message in the group instead.

            See full parameters here: [setMessageReaction](https://core.telegram.org/bots/api#setmessagereaction)
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reaction": reaction,
            "is_big": is_big,
        }
        response = self._make_request("setMessageReaction", method="POST", data=payload)
        return bool(response)

    def get_user_profile_photos(
        self, user_id: int, offset: int | None = None, limit: int | None = 100
    ) -> UserProfilePhotos:
        """
        Get a list of profile pictures for a user.

        Args:
            user_id: Unique identifier of the target user.
            offset: Sequential number of the first photo to be returned. By default, all photos are returned.
            limit: Limits the number of photos to be retrieved. Values between 1-100 are accepted. Defaults to 100.
        """
        payload = {
            "user_id": user_id,
            "offset": offset,
            "limit": limit,
        }
        response = self._make_request(
            "getUserProfilePhotos", method="GET", params=payload
        )
        return UserProfilePhotos.model_validate(response)

    def get_user_profile_audios(
        self, user_id: int, offset: int | None = None, limit: int | None = 100
    ) -> UserProfileAudios:
        """
        Use this method to get a list of profile audios for a user.

        Args:
            user_id: Unique identifier of the target user.
            offset: Sequential number of the first audio to be returned. By default, all audios are returned.
            limit: Limits the number of audios to be retrieved. Values between 1-100 are accepted. Defaults to 100.
        """
        payload = {
            "user_id": user_id,
            "offset": offset,
            "limit": limit,
        }
        response = self._make_request(
            "getUserProfileAudios", method="GET", params=payload
        )
        return UserProfileAudios.model_validate(response)

    def set_user_emoji_status(
        self,
        user_id: int,
        emoji_status_custom_emoji_id: str | None = None,
        emoji_status_expiration_date: int | None = None,
    ) -> bool:
        """
        Changes the emoji status for a given user that previously allowed the bot to
        manage their emoji status via the Mini App method requestEmojiStatusAccess.

        Args:
            user_id: Unique identifier of the target user.
            emoji_status_custom_emoji_id: Custom emoji identifier of the emoji status to set.
                Pass an empty string to remove the status.
            emoji_status_expiration_date: Expiration date of the emoji status, if any.
        """
        payload = {
            "user_id": user_id,
            "emoji_status_custom_emoji_id": emoji_status_custom_emoji_id,
            "emoji_status_expiration_date": emoji_status_expiration_date,
        }
        response = self._make_request("setUserEmojiStatus", method="POST", data=payload)
        return bool(response)

    def get_file(self, file_id: str) -> File:
        """
        Get basic information about a file and prepare it for downloading.

        Args:
            file_id: File identifier to get information about.

        Returns:
            A File object on success.
            The file can be downloaded via https://api.telegram.org/file/bot<token>/<file_path>.
            It is guaranteed that the link will be valid for at least 1 hour.

        Note:
            This function may not preserve the original file name and MIME type.
            You should save the file's MIME type and name (if available) when the File object is received.
        """
        payload = {"file_id": file_id}
        response = self._make_request("getFile", method="GET", params=payload)
        return File.model_validate(response)

    def ban_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        until_date: int | None = None,
        revoke_messages: bool | None = None,
    ) -> bool:
        """
        Ban a user in a group, supergroup, or channel.
        In supergroups and channels, the user will not be able to return on their own unless unbanned.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target group or username of the target supergroup or channel in the format @username.
            user_id: Unique identifier of the target user.

            See full parameters here: [banChatMember](https://core.telegram.org/bots/api#banchatmember)
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "until_date": until_date,
            "revoke_messages": revoke_messages,
        }
        response = self._make_request("banChatMember", method="POST", data=payload)
        return bool(response)

    def unban_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        only_if_banned: bool | None = None,
    ) -> bool:
        """
        Unban a previously banned user in a supergroup or channel.
        The user won't rejoin automatically but can use invite links to join.
        If the user is currently a member, they will be removed from the chat unless only_if_banned is True.
        The bot must be an administrator.

        Args:
            chat_id: Unique identifier for the target group or username of
                the target supergroup or channel in the format @username.
            user_id: Unique Unique identifier of the target user.
            only_if_banned: Do nothing if the user is not banned.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "only_if_banned": only_if_banned,
        }
        response = self._make_request("unbanChatMember", method="POST", data=payload)
        return bool(response)

    def restrict_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        permissions: Dict[str, Any],
        use_independent_chat_permissions: bool | None = None,
        until_date: int | None = None,
    ) -> bool:
        """
        Restrict a user in a supergroup.
        The bot must be an administrator with appropriate rights.
        Pass True for all permissions to lift restrictions.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            user_id: Unique identifier of the target user.
            permissions: A ChatPermissions object specifying new permissions.

            See full parameters here: [restrictChatMember](https://core.telegram.org/bots/api#restrictchatmember)
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "permissions": permissions,
            "use_independent_chat_permissions": use_independent_chat_permissions,
            "until_date": until_date,
        }
        response = self._make_request("restrictChatMember", method="POST", data=payload)
        return bool(response)

    def promote_chat_member(
        self,
        chat_id: int | str,
        user_id: int,
        is_anonymous: bool | None = None,
        can_manage_chat: bool | None = None,
        can_delete_messages: bool | None = None,
        can_manage_video_chats: bool | None = None,
        can_restrict_members: bool | None = None,
        can_promote_members: bool | None = None,
        can_change_info: bool | None = None,
        can_invite_users: bool | None = None,
        can_post_stories: bool | None = None,
        can_edit_stories: bool | None = None,
        can_delete_stories: bool | None = None,
        can_post_messages: bool | None = None,
        can_edit_messages: bool | None = None,
        can_pin_messages: bool | None = None,
        can_manage_topics: bool | None = None,
        can_manage_direct_messages: bool | None = None,
        can_manage_tags: bool | None = None,
    ) -> bool:
        """
        Promote or demote a user in a supergroup or channel.
        The bot must be an administrator with appropriate rights.
        Pass False for all parameters to demote the user.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            user_id: Unique identifier of the target user.

            See full parameters here: [promoteChatMember](https://core.telegram.org/bots/api#promotechatmember)
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "is_anonymous": is_anonymous,
            "can_manage_chat": can_manage_chat,
            "can_delete_messages": can_delete_messages,
            "can_manage_video_chats": can_manage_video_chats,
            "can_restrict_members": can_restrict_members,
            "can_promote_members": can_promote_members,
            "can_change_info": can_change_info,
            "can_invite_users": can_invite_users,
            "can_post_stories": can_post_stories,
            "can_edit_stories": can_edit_stories,
            "can_delete_stories": can_delete_stories,
            "can_post_messages": can_post_messages,
            "can_edit_messages": can_edit_messages,
            "can_pin_messages": can_pin_messages,
            "can_manage_topics": can_manage_topics,
            "can_manage_direct_messages": can_manage_direct_messages,
            "can_manage_tags": can_manage_tags,
        }
        response = self._make_request("promoteChatMember", method="POST", data=payload)
        return bool(response)

    def set_chat_administrator_custom_title(
        self, chat_id: int | str, user_id: int, custom_title: str
    ) -> bool:
        """
        Set a custom title for an administrator in a supergroup promoted by the bot.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            user_id: Unique identifier of the target user.
            custom_title: New custom title for the administrator; 0-16 characters, emoji are not allowed.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "custom_title": custom_title,
        }
        response = self._make_request(
            "setChatAdministratorCustomTitle", method="POST", data=payload
        )
        return bool(response)

    def set_chat_member_tag(self, chat_id: int | str, user_id: int, tag: str):
        """
        Use this method to set a tag for a regular member in a group or a supergroup.
        The bot must be an administrator in the chat for this to work and must
        have the can_manage_tags administrator right.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup
            user_id: Unique identifier of the target user.
            tag: New tag for the member; 0-16 characters, emoji are not allowed.
        """
        payload = {"chat_id": chat_id, "user_id": user_id, "tag": tag}
        response = self._make_request("setChatMemberTag", method="POST", data=payload)
        return bool(response)

    def ban_chat_sender_chat(self, chat_id: int | str, sender_chat_id: int) -> bool:
        """
        Ban a channel chat in a supergroup or channel.
        After this, the channel's owner cannot post on behalf of that channel until it's unbanned.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique Unique identifier for the target chat or username of
                the target channel in the format @username.
            sender_chat_id: Unique identifier of the target sender chat.
        """
        payload = {
            "chat_id": chat_id,
            "sender_chat_id": sender_chat_id,
        }
        response = self._make_request("banChatSenderChat", method="POST", data=payload)
        return bool(response)

    def unban_chat_sender_chat(self, chat_id: int | str, sender_chat_id: int) -> bool:
        """
        Unban a previously banned channel chat in a supergroup or channel.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            sender_chat_id: Unique identifier of the sender chat (channel) to unban.
        """
        payload = {
            "chat_id": chat_id,
            "sender_chat_id": sender_chat_id,
        }
        response = self._make_request(
            "unbanChatSenderChat", method="POST", data=payload
        )
        return bool(response)

    def set_chat_permissions(
        self,
        chat_id: int | str,
        permissions: ChatPermissions,
        use_independent_chat_permissions: bool | None = None,
    ) -> bool:
        """
        Set default chat permissions for all members in a group or supergroup.
        The bot must be an administrator with can_restrict_members right.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            permissions: A ChatPermissions object for new default chat permissions.
            use_independent_chat_permissions: Pass True if chat permissions are set independently.
                Otherwise, the can_send_other_messages and can_add_web_page_previews permissions will
                imply the can_send_messages, can_send_audios, can_send_documents, can_send_photos, can_send_videos,
                can_send_video_notes, and can_send_voice_notes permissions; the can_send_polls permission will imply
                the can_send_messages permission.
        """
        payload = {
            "chat_id": chat_id,
            "permissions": permissions,
            "use_independent_chat_permissions": use_independent_chat_permissions,
        }
        response = self._make_request("setChatPermissions", method="POST", data=payload)
        return bool(response)

    def export_chat_invite_link(self, chat_id: int | str) -> str:
        """
        Generate a new primary invite link for a chat. Any previous primary link is revoked.
        The bot must be an administrator with appropriate rights.
        Each administrator (including bots) has their own invite links.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.

        Note:
            Each administrator in a chat generates their own invite links.
            Bots can't use invite links generated by other administrators.
            If you want your bot to work with invite links, it will need to generate its own link
             using exportChatInviteLink or by calling the getChat method.
            If your bot needs to generate a new primary invite link replacing its previous one,
             use exportChatInviteLink again.

        Returns:
            The new invite link as a string on success.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "exportChatInviteLink", method="GET", params=payload
        )
        return str(response)

    def create_chat_invite_link(
        self,
        chat_id: int | str,
        name: str | None = None,
        expire_date: int | None = None,
        member_limit: int | None = None,
        creates_join_request: bool | None = None,
    ) -> ChatInviteLink:
        """
        Create a new additional invite link for a chat.
        The link can be edited or revoked using editChatInviteLink or revokeChatInviteLink.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.

            See full parameters here: [createChatInviteLink](https://core.telegram.org/bots/api#createchatinvitelink)
        """
        payload = {
            "chat_id": chat_id,
            "name": name,
            "expire_date": expire_date,
            "member_limit": member_limit,
            "creates_join_request": creates_join_request,
        }
        response = self._make_request(
            "createChatInviteLink", method="POST", data=payload
        )
        return ChatInviteLink.model_validate(response)

    def edit_chat_invite_link(
        self,
        chat_id: int | str,
        invite_link: str,
        name: str | None = None,
        expire_date: int | None = None,
        member_limit: int | None = None,
        creates_join_request: bool | None = None,
    ) -> ChatInviteLink:
        """
        Edit a non-primary invite link created by the bot.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or username (e.g. @channelusername).
            invite_link: The invite link to edit.

            See full parameters here: [editChatInviteLink](https://core.telegram.org/bots/api#editchatinvitelink)
        """
        payload = {
            "chat_id": chat_id,
            "invite_link": invite_link,
            "name": name,
            "expire_date": expire_date,
            "member_limit": member_limit,
            "creates_join_request": creates_join_request,
        }
        response = self._make_request("editChatInviteLink", method="POST", data=payload)
        return ChatInviteLink.model_validate(response)

    def create_chat_subscription_invite_link(
        self,
        chat_id: int | str,
        subscription_period: int,
        subscription_price: int,
        name: str | None = None,
    ) -> ChatInviteLink:
        """
        Create a subscription invite link for a channel.
        Users must pay Telegram Stars to join via this link.
        The bot must have the 'can_invite_users' administrator right.

        Args:
            chat_id: Unique identifier for the target channel or username (e.g. @channelusername).
            subscription_period: Duration of the subscription in seconds. Must be 2592000 (30 days).
            subscrdiption_price: Amount of Telegram Stars required (1–10000).
            name: Invite link name (0–32 characters).
        """
        payload = {
            "chat_id": chat_id,
            "name": name,
            "subscription_period": subscription_period,
            "subscription_price": subscription_price,
        }
        response = self._make_request(
            "createChatSubscriptionInviteLink", method="POST", data=payload
        )
        return ChatInviteLink.model_validate(response)

    def edit_chat_subscription_invite_link(
        self, chat_id: int | str, invite_link: str, name: str | None = None
    ) -> ChatInviteLink:
        """
        Edit a subscription invite link created by the bot.
        The bot must have the 'can_invite_users' administrator right.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            invite_link: The subscription invite link to edit.
            name: New invite link name (0–32 characters).
        """
        payload = {
            "chat_id": chat_id,
            "invite_link": invite_link,
            "name": name,
        }
        response = self._make_request(
            "editChatSubscriptionInviteLink", method="POST", data=payload
        )
        return ChatInviteLink.model_validate(response)

    def revoke_chat_invite_link(
        self, chat_id: int | str, invite_link: str
    ) -> ChatInviteLink:
        """
        Revoke an invite link created by the bot.
        If the primary link is revoked, a new one is automatically generated.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            invite_link: The invite link to revoke.
        """
        payload = {
            "chat_id": chat_id,
            "invite_link": invite_link,
        }
        response = self._make_request(
            "revokeChatInviteLink", method="POST", data=payload
        )
        return ChatInviteLink.model_validate(response)

    def approve_chat_join_request(self, chat_id: int | str, user_id: int) -> bool:
        """
        Approve a user's request to join a chat.
        The bot must be an administrator with the 'can_invite_users' right.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            user_id: Unique identifier of the user whose join request is approved.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
        }
        response = self._make_request(
            "approveChatJoinRequest", method="POST", data=payload
        )
        return bool(response)

    def decline_chat_join_request(self, chat_id: int | str, user_id: int) -> bool:
        """
        Decline a user's request to join a chat.
        The bot must be an administrator with the 'can_invite_users' right.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            user_id: Unique identifier of the user whose join request is declined.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
        }
        response = self._make_request(
            "declineChatJoinRequest", method="POST", data=payload
        )
        return bool(response)

    def answer_chat_join_request_query(
        self, chat_join_request_query_id: str, result: str
    ) -> bool:
        """
        Use this method to process a received chat join request query.

        Args:
            chat_join_request_query_id: Unique identifier of the join request query.
            result: Result of the query. Must be either `approve` to allow the user to join the chat,
             `decline` to disallow the user to join the chat, or `queue` to leave the decision to other administrators.
        """
        payload = {
            "chat_join_request_query_id": chat_join_request_query_id,
            "result": result,
        }
        response = self._make_request(
            "answerChatJoinRequestQuery", method="POST", data=payload
        )
        return bool(response)

    def send_chat_join_request_web_app(
        self, chat_join_request_query_id: str, web_app_url: str
    ) -> bool:
        """
        Use this method to process a received chat join request query by
        showing a Mini App to the user before deciding the outcome.

        Args:
            chat_join_request_query_id: Unique identifier of the join request query.
            web_app_url: The URL of the Mini App to be opened.
        """
        payload = {
            "chat_join_request_query_id": chat_join_request_query_id,
            "web_app_url": web_app_url,
        }
        response = self._make_request(
            "sendChatJoinRequestWebApp", method="POST", data=payload
        )
        return bool(response)

    def set_chat_photo(self, chat_id: int | str, photo: bytes) -> bool:
        """
        Set a new profile photo for the chat.
        Not available for private chats.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            photo: New chat photo, uploaded using multipart/form-data.
        """
        files = {"photo": photo}
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "setChatPhoto", method="POST", data=payload, files=files
        )
        return bool(response)

    def delete_chat_photo(self, chat_id: int | str) -> bool:
        """
        Delete the current profile photo of the chat.
        Not available for private chats.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request("deleteChatPhoto", method="POST", data=payload)
        return bool(response)

    def set_chat_title(self, chat_id: int | str, title: str) -> bool:
        """
        Change the title of a chat.
        Not available for private chats.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            title: New chat title, 1-128 characters.
        """
        payload = {
            "chat_id": chat_id,
            "title": title,
        }
        response = self._make_request("setChatTitle", method="POST", data=payload)
        return bool(response)

    def set_chat_description(
        self, chat_id: int | str, description: str | None = None
    ) -> bool:
        """
        Change the description of a group, supergroup, or channel.
        The bot must be an administrator with appropriate rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            description: New chat description, 0-255 characters.
        """
        payload = {
            "chat_id": chat_id,
            "description": description,
        }

        response = self._make_request("setChatDescription", method="POST", data=payload)
        return bool(response)

    def pin_chat_message(
        self,
        chat_id: int | str,
        message_id: int,
        business_connection_id: str | None = None,
        disable_notification: bool | None = None,
    ) -> bool:
        """
        Pin a message in a chat.
        In groups and channels, the bot must have 'can_pin_messages' or 'can_edit_messages' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            message_id: Identifier of a message to pin.
            business_connection_id: Unique identifier of the business connection on behalf of which the message will be pinned.
            disable_notification: Sends the message silently.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "business_connection_id": business_connection_id,
            "disable_notification": disable_notification,
        }
        response = self._make_request("pinChatMessage", method="POST", data=payload)
        return bool(response)

    def unpin_chat_message(
        self,
        chat_id: int | str,
        message_id: int | None = None,
        business_connection_id: str | None = None,
    ) -> bool:
        """
        Unpin a specific message in a chat.
        If message_id is not specified, the most recent pinned message is unpinned.
        The bot must have appropriate rights in groups and channels.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
            message_id: Identifier of the message to unpin. Required if business_connection_id is specified.
                If not specified, the most recent pinned message (by sending date) will be unpinned.
            business_connection_id: Unique identifier of the business connection on behalf of which the message will be unpinned.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "business_connection_id": business_connection_id,
        }
        response = self._make_request("unpinChatMessage", method="POST", data=payload)
        return bool(response)

    def unpin_all_chat_messages(self, chat_id: int | str) -> bool:
        """
        Clear all pinned messages in a chat.
        No special rights needed in private chats or channel direct messages.
        In groups and channels, the bot must have 'can_pin_messages' or 'can_edit_messages' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "unpinAllChatMessages", method="POST", data=payload
        )
        return bool(response)

    def leave_chat(self, chat_id: int | str) -> bool:
        """
        Make the bot leave a group, supergroup, or channel.
        Channel direct messages chats are not supported; leave the corresponding channel instead.

        Args:
            chat_id: Unique identifier for the target chat or username of the target supergroup or channel
                in the format @username. Channel direct messages chats aren't supported;
                leave the corresponding channel instead.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request("leaveChat", method="POST", data=payload)
        return bool(response)

    def get_chat(self, chat_id: int | str) -> ChatFullInfo:
        """
        Get up-to-date information about a chat (group, supergroup, channel, or private chat).
        Returns a ChatFullInfo object.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup/channel.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request("getChat", method="GET", params=payload)
        return ChatFullInfo.model_validate(response)

    def get_chat_administrators(
        self, chat_id: int | str, return_bots: bool = False
    ) -> ChatMember:
        """
        Use this method to get a list of administrators in a chat.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup/channel.
            return_bots: Pass True to additionally receive all bots that are administrators of the chat.
                By default, bots other than the current bot are omitted.
        """
        payload = {"chat_id": chat_id, "return_bots": return_bots}
        response = self._make_request(
            "getChatAdministrators", method="GET", params=payload
        )
        return ChatMemberAdapter.validate_python(response)

    def get_chat_member_count(self, chat_id: int | str) -> int:
        """
        Get the number of members in a chat.
        Returns an integer on success.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup/channel.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "getChatMemberCount", method="GET", params=payload
        )
        return cast(int, response)

    def get_chat_member(self, chat_id: int | str, user_id: int) -> ChatMember:
        """
        Get information about a specific member of a chat.
        Guaranteed to work for other users only if the bot is an administrator.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup/channel.
            user_id: Unique identifier of the target user.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
        }
        response = self._make_request("getChatMember", method="GET", params=payload)
        return ChatMemberAdapter.validate_python(response)

    def get_user_personal_chat_messages(
        self, user_id: int, limit: int
    ) -> List[Message]:
        """
        Use this method to get the last messages from the personal chat
        (i.e., the chat currently added to their profile) of a given user

        Args:
            user_id: Unique identifier for the target chat or @username of the supergroup/channel.
            limit: The maximum number of messages to return; 1-20.
        """
        payload = {"user_id": user_id, "limit": limit}
        response = self._make_request(
            "getUserPersonalChatMessages", method="GET", params=payload
        )
        return MessageListAdapter.validate_python(response)

    def set_chat_sticker_set(self, chat_id: int | str, sticker_set_name: str) -> bool:
        """
        Set a new group sticker set for a supergroup.
        The bot must be an administrator with appropriate rights.
        Use getChat to check if the bot can_set_sticker_set.

        Args:
            chat_id: Unique Unique identifier for the target chat or @username of the supergroup.
            sticker_set_name: Name of the sticker set to be set as the group sticker set.
        """
        payload = {
            "chat_id": chat_id,
            "sticker_set_name": sticker_set_name,
        }
        response = self._make_request("setChatStickerSet", method="POST", data=payload)
        return bool(response)

    def delete_chat_sticker_set(self, chat_id: int | str) -> bool:
        """
        Delete the group sticker set from a supergroup.
        The bot must be an administrator with appropriate rights.
        Use getChat to check if the bot can_set_sticker_set.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "deleteChatStickerSet", method="POST", data=payload
        )
        return bool(response)

    def get_forum_topic_icon_stickers(self) -> List[Sticker]:
        """
        Get custom emoji stickers that can be used as forum topic icons by any user.
        This method requires no parameters.
        """
        response = self._make_request("getForumTopicIconStickers", method="GET")
        return StickerList.validate_python(response)

    def create_forum_topic(
        self,
        chat_id: int | str,
        name: str,
        icon_color: int | None = None,
        icon_custom_emoji_id: str | None = None,
    ) -> ForumTopic:
        """
        Create a new topic in a forum supergroup chat.
        The bot must be an administrator with 'can_manage_topics' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            name: Topic name, 1-128 characters.
            icon_color: Color of the topic icon in RGB format. Must be one of:
                7322096 (0x6FB9F0), 16766590 (0xFFD67E), 13338331 (0xCB86DB),
                9367192 (0x8EEE98), 16749490 (0xFF93B2), 16478047 (0xFB6F5F).
            icon_custom_emoji_id: UniqUnique identifier of the custom emoji shown as the topic icon.
                Use get_forum_topic_icon_stickers() to get all allowed custom emoji identifiers.
        """
        payload = {
            "chat_id": chat_id,
            "name": name,
            "icon_color": icon_color,
            "icon_custom_emoji_id": icon_custom_emoji_id,
        }
        response = self._make_request("createForumTopic", method="POST", data=payload)
        return ForumTopic.model_validate(response)

    def edit_forum_topic(
        self,
        chat_id: int | str,
        message_thread_id: int,
        name: str | None = None,
        icon_custom_emoji_id: str | None = None,
    ) -> bool:
        """
        Edit the name and/or icon of a forum topic.
        The bot must be an administrator with 'can_manage_topics' rights, unless it's the topic creator.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_thread_id: Unique identifier for the target message thread of the forum topic.
            name: New topic name, 0-128 characters. If not specified, the current icon will be kept.
            icon_custom_emoji_id: New unique identifier of the custom emoji shown as the topic icon.
                Use get_forum_topic_icon_stickers() to get all allowed custom emoji identifiers.
                Pass an empty string to remove the icon.
                If not specified, the current icon will be kept.
        """
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
            "name": name,
            "icon_custom_emoji_id": icon_custom_emoji_id,
        }
        response = self._make_request("editForumTopic", method="POST", data=payload)
        return bool(response)

    def close_forum_topic(self, chat_id: int | str, message_thread_id: int) -> bool:
        """
        Close an open forum topic.
        The bot must be an administrator with 'can_manage_topics' rights, unless it's the topic creator.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_thread_id: Unique identifier for the target message thread of the forum topic.
        """
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request("closeForumTopic", method="POST", data=payload)
        return bool(response)

    def reopen_forum_topic(self, chat_id: int | str, message_thread_id: int) -> bool:
        """
        Reopen a closed forum topic.
        The bot must be an administrator with 'can_manage_topics' rights, unless it's the topic creator.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_thread_id: Unique identifier for the target message thread of the forum topic.
        """
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request("reopenForumTopic", method="POST", data=payload)
        return bool(response)

    def delete_forum_topic(self, chat_id: int | str, message_thread_id: int) -> bool:
        """
        Delete a forum topic along with all its messages.
        The bot must be an administrator with 'can_delete_messages' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_thread_id: Unique identifier for the target message thread of the forum topic.
        """
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request("deleteForumTopic", method="POST", data=payload)
        return bool(response)

    def unpin_all_forum_topic_messages(
        self, chat_id: int | str, message_thread_id: int
    ) -> bool:
        """
        Clear the list of pinned messages in a specific forum topic.
        The bot must be an administrator with 'can_pin_messages' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_thread_id: Unique identifier for the target message thread of the forum topic.
        """
        payload = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request(
            "unpinAllForumTopicMessages", method="POST", data=payload
        )
        return bool(response)

    def edit_general_forum_topic(self, chat_id: int | str, name: str) -> bool:
        """
        Edit the name of the 'General' topic in a forum supergroup.
        The bot must be an administrator with 'can_manage_topics' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            name: New topic name, 1-128 characters.
        """
        payload = {
            "chat_id": chat_id,
            "name": name,
        }
        response = self._make_request(
            "editGeneralForumTopic", method="POST", data=payload
        )
        return bool(response)

    def close_general_forum_topic(self, chat_id: int | str) -> bool:
        """
        Close the 'General' topic in a forum supergroup.
        The bot must be an administrator with 'can_manage_topics' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "closeGeneralForumTopic", method="POST", data=payload
        )
        return bool(response)

    def reopen_general_forum_topic(self, chat_id: int | str) -> bool:
        """
        Reopen a closed 'General' topic in a forum supergroup.
        The bot must be an administrator with 'can_manage_topics' rights.
        If the topic was hidden, it will be automatically unhidden.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "reopenGeneralForumTopic", method="POST", data=payload
        )
        return bool(response)

    def hide_general_forum_topic(self, chat_id: int | str) -> bool:
        """
        Hide the 'General' topic in a forum supergroup.
        The bot must be an administrator with 'can_manage_topics' rights.
        The topic will be automatically closed if it was open.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "hideGeneralForumTopic", method="POST", data=payload
        )
        return bool(response)

    def unhide_general_forum_topic(self, chat_id: int | str) -> bool:
        """
        Unhide the 'General' topic in a forum supergroup.
        The bot must be an administrator with 'can_manage_topics' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "unhideGeneralForumTopic", method="POST", data=payload
        )
        return bool(response)

    def unpin_all_general_forum_topic_messages(self, chat_id: int | str) -> bool:
        """
        Clear the list of pinned messages in the 'General' forum topic.
        The bot must be an administrator with 'can_pin_messages' rights.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "unpinAllGeneralForumTopicMessages", method="POST", data=payload
        )
        return bool(response)

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool | None = False,
        url: str | None = None,
        cache_time: int | None = None,
    ) -> bool:
        """
        Send an answer to a callback query sent from an inline keyboard.
        The answer will be displayed to the user as a notification or an alert.

        Args:
            callback_query_id: Unique identifier for the query to be answered.
            text: Text of the notification. If not specified, nothing will be shown to the user, 0-200 characters.
            show_alert: If True, an alert will be shown by the client instead of a notification at the top of the chat screen.
            url: URL to be opened by the user's client. Use for games (created via @BotFather) or
                deep linking (e.g., t.me/your_bot?start=XXXX).
            cache_time: Maximum amount of time in seconds that the result may be cached client-side. Defaults to 0.
        """
        payload = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
            "url": url,
            "cache_time": cache_time,
        }

        response = self._make_request(
            "answerCallbackQuery", method="POST", data=payload
        )
        return bool(response)

    def answer_guest_query(
        self, guest_query_id: str, result: InlineQueryResult
    ) -> SentGuestMessage:
        """
        Use this method to reply to a received guest message.

        Args:
            guest_query_id: Unique identifier for the query to be answered.
            result: InlineQueryResult object describing the message to be sent.
        """
        payload = {"guest_query_id": guest_query_id, "result": result}

        response = self._make_request("answerGuestQuery", method="POST", data=payload)
        return SentGuestMessage.model_validate(response)

    def get_user_chat_boosts(self, chat_id: int | str, user_id: int) -> UserChatBoosts:
        """
        Get the list of boosts added to a chat by a user.
        The bot must have administrator rights in the chat.

        Args:
            chat_id: Unique identifier for the chat or username of the channel in the format @username.
            user_id: Unique identifier of the target user.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
        }
        response = self._make_request("getUserChatBoosts", method="GET", params=payload)
        return UserChatBoosts.model_validate(response)

    def get_business_connection(
        self, business_connection_id: str
    ) -> BusinessConnection:
        """
        Get information about the connection of the bot with a business account.

        Args:
            business_connection_id: Unique identifier of the business connection.
        """
        payload = {"business_connection_id": business_connection_id}
        response = self._make_request(
            "getBusinessConnection", method="GET", params=payload
        )
        return BusinessConnection.model_validate(response)

    def get_managed_bot_token(self, user_id: int) -> str:
        """
        Use this method to get the token of a managed bot.

        Args:
            user_id: User identifier of the managed bot whose token will be returned.
        """
        payload = {"user_id": user_id}
        response = self._make_request(
            "getManagedBotToken", method="GET", params=payload
        )
        return str(response)

    def replace_managed_bot_token(self, user_id: int) -> str:
        """
        Use this method to revoke the current token of a managed bot and generate a new one.

        Args:
            user_id: User identifier of the managed bot whose token will be replaced.
        """
        payload = {"user_id": user_id}
        response = self._make_request(
            "replaceManagedBotToken", method="POST", data=payload
        )
        return str(response)

    def get_managed_bot_access_settings(self, user_id: int) -> BotAccessSettings:
        """
        Use this method to get the access settings of a managed bot.

        Args:
            user_id: User identifier of the managed bot whose access settings will be returned.
        """
        payload = {"user_id": user_id}
        response = self._make_request(
            "getManagedBotAccessSettings", method="GET", params=payload
        )
        return BotAccessSettings.model_validate(response)

    def set_managed_bot_access_settings(
        self, user_id: int, is_access_restricted: bool, added_user_ids: List[int]
    ) -> bool:
        """
        Use this method to change the access settings of a managed bot.

        Args:
            user_id: User identifier of the managed bot whose access settings will be changed.
            is_access_restricted: Pass True, if only selected users can access the bot. The bot's owner can always access it.
            added_user_ids: A list of user IDs up to 10 identifiers of who will have access to the bot
                in addition to its owner. Ignored if is_access_restricted is false.
        """
        payload = {
            "user_id": user_id,
            "is_access_restricted": is_access_restricted,
            "added_user_ids": added_user_ids,
        }
        response = self._make_request(
            "setManagedBotAccessSettings", method="POST", data=payload
        )
        return bool(response)

    def set_my_commands(
        self,
        commands: BotCommand,
        scope: BotCommandScope | None = None,
        language_code: str | None = None,
    ) -> bool:
        """
        Change the list of the bot's commands.

        Args:
            commands: A list of BotCommand objects, at most 100 commands can be specified.
            scope: A BotCommandScope object, describing scope of users for which the commands are relevant.
            language_code: A two-letter ISO 639-1 language code.
                If empty, commands will be applied to all users from the given scope,
                for whose language there are no dedicated commands.
        """
        scope = scope or BotCommandScopeDefault()
        payload = {
            "commands": commands,
            "scope": scope,
            "language_code": language_code,
        }
        response = self._make_request("setMyCommands", method="POST", data=payload)
        return bool(response)

    def delete_my_commands(
        self,
        scope: BotCommandScope | None = None,
        language_code: str | None = None,
    ) -> bool:
        """
        Delete the list of the bot's commands for the given scope and language.
        After deletion, higher-level commands will be used.

        Args:
            scope: A BotCommandScope object, describing scope of users for which the commands are relevant.
            language_code: A two-letter ISO 639-1 language code.
                If empty, commands will be applied to all users from the given scope,
                for whose language there are no dedicated commands.
        """
        scope = scope or BotCommandScopeDefault()
        payload = {"scope": scope, "language_code": language_code}
        response = self._make_request("deleteMyCommands", method="POST", data=payload)
        return bool(response)

    def get_my_commands(
        self,
        scope: BotCommandScope | None = None,
        language_code: str | None = None,
    ) -> List[BotCommand]:
        """
        Get the current list of the bot's commands for the given scope and language.

        Args:
            scope: A BotCommandScope object, describing scope of users.
            language_code: A two-letter ISO 639-1 language code or an empty string
        """
        scope = scope or BotCommandScopeDefault()
        payload = {"scope": scope, "language_code": language_code}
        response = self._make_request("getMyCommands", method="GET", params=payload)
        return BotCommandList.validate_python(response)

    def set_my_name(
        self, name: str | None = None, language_code: str | None = None
    ) -> bool:
        """
        Change the bot's name.

        Args:
            name: New bot name; 0-64 characters. Pass an empty string to remove the dedicated name for the given language.
            language_code: A two-letter ISO 639-1 language code.
                If empty, the name will be shown to all users for whose language there is no dedicated name.
        """
        payload = {
            "name": name,
            "language_code": language_code,
        }
        response = self._make_request("setMyName", method="POST", data=payload)
        return bool(response)

    def get_my_name(self, language_code: str | None = None) -> BotName:
        """
        Get the current bot name for the given user language.

        Args:
            language_code: A two-letter ISO 639-1 language code or an empty string.
        """
        payload = {"language_code": language_code}
        response = self._make_request("getMyName", method="GET", params=payload)
        return BotName.model_validate(response)

    def set_my_description(
        self, description: str | None = None, language_code: str | None = None
    ) -> bool:
        """
        Change the bot's description shown in the chat when it's empty.

        Args:
            description: New bot description; 0-512 characters.
                Pass an empty string to remove the dedicated description for the given language.
            language_code: A two-letter ISO 639-1 language code. If empty, the description will
                be applied to all users for whose language there is no dedicated description.
        """
        payload = {
            "description": description,
            "language_code": language_code,
        }

        response = self._make_request("setMyDescription", method="POST", data=payload)
        return bool(response)

    def get_my_description(self, language_code: str | None = None) -> BotDescription:
        """
        Get the current bot description for the given user language.

        Args:
            language_code: A two-letter ISO 639-1 language code or an empty string.
        """
        payload = {"language_code": language_code}
        response = self._make_request("getMyDescription", method="GET", params=payload)
        return BotDescription.model_validate(response)

    def set_my_short_description(
        self,
        short_description: str | None = None,
        language_code: str | None = None,
    ) -> bool:
        """
        Change the bot's short description shown on the profile and when shared.

        Args:
            short_description: New short description for the bot; 0-120 characters.
                Pass an empty string to remove the dedicated short description for the given language.
            language_code: A two-letter ISO 639-1 language code. If empty, the short description will be
                applied to all users for whose language there is no dedicated short description.
        """
        payload = {
            "short_description": short_description,
            "language_code": language_code,
        }
        response = self._make_request(
            "setMyShortDescription", method="POST", data=payload
        )
        return bool(response)

    def get_my_short_description(
        self, language_code: str | None = None
    ) -> BotShortDescription:
        """
        Get the current bot short description for the given user language.

        Args:
            language_code: A two-letter ISO 639-1 language code or an empty string.
        """
        payload = {"language_code": language_code}

        response = self._make_request(
            "getMyShortDescription", method="GET", params=payload
        )
        return BotShortDescription.model_validate(response)

    def set_my_profile_photo(self, photo: InputProfilePhoto) -> bool:
        """
        Changes the profile photo of the bot.

        Args:
            photo: The new profile photo to set.
        """
        payload = {"photo": photo}
        response = self._make_request("setMyProfilePhoto", method="POST", data=payload)
        return bool(response)

    def remove_my_profile_photo(self) -> bool:
        """
        Removes the profile photo of the bot. Requires no parameters.
        """
        response = self._make_request("removeMyProfilePhoto", method="POST")
        return bool(response)

    def set_chat_menu_button(
        self,
        chat_id: int | None = None,
        menu_button: MenuButton | None = None,
    ) -> bool:
        """
        Change the bot's menu button in a private chat or the default menu button.

        Args:
            chat_id: Unique identifier for the target private chat. If not specified,
                the bot's default menu button will be changed.
            menu_button: A MenuButton object for the bot's new menu button.
        """
        menu_button = menu_button or MenuButtonDefault()
        payload = {
            "chat_id": chat_id,
            "menu_button": menu_button,
        }
        response = self._make_request("setChatMenuButton", method="POST", data=payload)
        return bool(response)

    def get_chat_menu_button(self, chat_id: int | None = None) -> MenuButton:
        """
        Get the current value of the bot's menu button in a private chat or the default.

        Args:
            chat_id: Unique identifier for the target private chat.
                If not specified, the bot's default menu button will be returned.
        """
        payload = {"chat_id": chat_id}
        response = self._make_request("getChatMenuButton", method="GET", params=payload)
        return MenuButtonAdapter.validate_python(response)

    def set_my_default_administrator_rights(
        self,
        rights: ChatAdministratorRights | None = None,
        for_channels: bool | None = None,
    ) -> bool:
        """
        Change the default administrator rights requested when the bot is added to groups or channels.

        Args:
            rights: A ChatAdministratorRights object describing new default administrator rights.
                If not specified, the default administrator rights will be cleared.
            for_channels: Pass True to change the default administrator rights of the bot in channels.
                Otherwise, the default administrator rights of the bot for groups and supergroups will be changed.
        """
        payload = {"rights": rights, "for_channels": for_channels}
        response = self._make_request(
            "setMyDefaultAdministratorRights", method="POST", data=payload
        )
        return bool(response)

    def get_my_default_administrator_rights(
        self, for_channels: bool | None = None
    ) -> ChatAdministratorRights:
        """
        Get the current default administrator rights of the bot.

        Args:
            for_channels: Pass True to get default administrator rights of the bot in channels.
                Otherwise, default administrator rights of the bot for groups and supergroups will be returned.
        """
        payload = {"for_channels": for_channels}
        response = self._make_request(
            "getMyDefaultAdministratorRights", method="GET", params=payload
        )
        return ChatAdministratorRights.model_validate(response)

    def get_available_gifts(self) -> Gift:
        """
        Get the list of gifts that can be sent by the bot to users and channel chats.
        """
        response = self._make_request("getAvailableGifts", method="GET")
        return Gift.model_validate(response)

    def send_gift(
        self,
        gift_id: str,
        user_id: int | None = None,
        chat_id: int | str | None = None,
        pay_for_upgrade: bool | None = None,
        text: str | None = None,
        text_parse_mode: str | None = "html",
        text_entities: List[MessageEntity] | None = None,
    ) -> bool:
        """
        Send a gift to a user or channel chat. The gift cannot be converted to Telegram Stars.

        Args:
            gift_id: Identifier of the gift; limited gifts can't be sent to channel chats.
            user_id: Unique identifier of the target user who will receive the gift.
            chat_id: Unique identifier for the chat or username of
                the channel (in the format @username) that will receive the gift.

        Note:
            chat_id Required if user_id is not specified.
            user_id Required if chat_id is not specified.
        """
        if not (user_id or chat_id):
            raise ValueError("Either user_id or chat_id must be provided.")

        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "gift_id": gift_id,
            "pay_for_upgrade": pay_for_upgrade,
            "text": text,
            "text_parse_mode": text_parse_mode,
            "text_entities": text_entities,
        }
        response = self._make_request("sendGift", method="POST", data=payload)
        return bool(response)

    def gift_premium_subscription(
        self,
        user_id: int,
        month_count: int,
        star_count: int,
        text: str | None = None,
        text_parse_mode: str | None = "html",
        text_entities: List[MessageEntity] | None = None,
    ) -> bool:
        """
        Gift a Telegram Premium subscription to a user.

        Args:
            user_id: Unique identifier of the target user who will receive a Telegram Premium subscription.
            month_count: Number of months the Telegram Premium subscription
                will be active for the user; must be one of 3, 6, or 12.
            star_count: Number of Telegram Stars to pay. Must be 1000 (3 months), 1500 (6 months), or 2500 (12 months).

            See full parameters here: [giftPremiumSubscription](https://core.telegram.org/bots/api#giftpremiumsubscription)
        """
        payload = {
            "user_id": user_id,
            "month_count": month_count,
            "star_count": star_count,
            "text": text,
            "text_parse_mode": text_parse_mode,
            "text_entities": text_entities,
        }
        response = self._make_request(
            "giftPremiumSubscription", method="POST", data=payload
        )
        return bool(response)

    def verify_user(self, user_id: int, custom_description: str | None = None) -> bool:
        """
        Verify a user on behalf of the organization represented by the bot.

        Args:
            user_id: Unique identifier of the target user.
            custom_description: Custom description for the verification; 0-70 characters.
                Must be empty if the organization isn't allowed to provide a custom verification description.
        """
        payload = {
            "user_id": user_id,
            "custom_description": custom_description,
        }
        response = self._make_request("verifyUser", method="POST", data=payload)
        return bool(response)

    def verify_chat(
        self, chat_id: int | str, custom_description: str | None = None
    ) -> bool:
        """
        Verify a chat (e.g., channel) on behalf of the organization represented by the bot.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
                Channel direct messages chats can't be verified.
            custom_description: Custom description for the verification; 0-70 characters.
                Must be empty if the organization isn't allowed to provide a custom verification description.
        """
        payload = {
            "chat_id": chat_id,
            "custom_description": custom_description,
        }
        response = self._make_request("verifyChat", method="POST", data=payload)
        return bool(response)

    def remove_user_verification(self, user_id: int) -> bool:
        """
        Remove verification from a user who is currently verified on behalf of the organization.

        Args:
            user_id: Unique identifier of the target user.
        """
        payload = {"user_id": user_id}
        response = self._make_request(
            "removeUserVerification", method="POST", data=payload
        )
        return bool(response)

    def remove_chat_verification(self, chat_id: int | str) -> bool:
        """
        Remove verification from a chat that is currently verified on behalf of the organization.

        Args:
            chat_id: Unique identifier for the target chat or username of the target bot or channel in the format @username
        """
        payload = {"chat_id": chat_id}
        response = self._make_request(
            "removeChatVerification", method="POST", data=payload
        )
        return bool(response)

    def read_business_message(
        self, business_connection_id: str, chat_id: int, message_id: int
    ) -> bool:
        """
        Mark an incoming message as read on behalf of a connected business account.
        Requires the 'can_read_messages' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection on behalf of which to read the message.
            chat_id: Unique identifier of the chat in which the message was received.
                The chat must have been active in the last 24 hours.
            message_id: Unique identifier of the message to mark as read.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
        }
        response = self._make_request(
            "readBusinessMessage", method="POST", data=payload
        )
        return bool(response)

    def delete_business_messages(
        self, business_connection_id: str, message_ids: List[int]
    ) -> bool:
        """
        Delete messages on behalf of a business account.
        Requires 'can_delete_sent_messages' to delete own messages, or 'can_delete_all_messages' to delete any message.

        Args:
            business_connection_id: Unique identifier of the business connection on behalf of which to delete the messages.
            message_ids: A list of msg ids, 1-100 identifiers of messages to delete.
                All messages must be from the same chat. See deleteMessage for limitations on which messages can be deleted.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "message_ids": message_ids,
        }
        response = self._make_request(
            "deleteBusinessMessages", method="POST", data=payload
        )
        return bool(response)

    def set_business_account_name(
        self,
        business_connection_id: str,
        first_name: str,
        last_name: str | None = None,
    ) -> bool:
        """
        Change the first and last name of a managed business account.
        Requires the 'can_change_name' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            first_name: The new value of the first name for the business account; 1-64 characters.
            last_name: The new value of the last name for the business account; 0-64 characters.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        response = self._make_request(
            "setBusinessAccountName", method="POST", data=payload
        )
        return bool(response)

    def set_business_account_username(
        self, business_connection_id: str, username: str | None = None
    ) -> bool:
        """
        Change the username of a managed business account.
        Requires the 'can_change_username' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            username: The new value of the username for the business account; 0-32 characters.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "username": username,
        }
        response = self._make_request(
            "setBusinessAccountUsername", method="POST", data=payload
        )
        return bool(response)

    def set_business_account_bio(
        self, business_connection_id: str, bio: str | None = None
    ) -> bool:
        """
        Change the bio (description) of a managed business account.
        Requires the 'can_change_bio' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            bio: The new value of the bio for the business account; 0-140 characters.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "bio": bio,
        }
        response = self._make_request(
            "setBusinessAccountBio", method="POST", data=payload
        )
        return bool(response)

    def set_business_account_profile_photo(
        self,
        business_connection_id: str,
        photo: InputProfilePhoto,
        is_public: bool | None = None,
    ) -> bool:
        """
        Change the profile photo of a managed business account.
        Requires the 'can_edit_profile_photo' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            photo: The new profile photo to set.
            is_public: Pass True to set the public photo, which will be visible even if the main photo
                is hidden by the business account's privacy settings. An account can have only one public photo.
        """
        files = {"photo": photo}
        payload = {
            "business_connection_id": business_connection_id,
            "is_public": is_public,
        }
        response = self._make_request(
            "setBusinessAccountProfilePhoto",
            method="POST",
            data=payload,
            files=files,
        )
        return bool(response)

    def remove_business_account_profile_photo(
        self, business_connection_id: str, is_public: bool | None = None
    ) -> bool:
        """
        Remove the current profile photo of a managed business account.
        Requires the 'can_edit_profile_photo' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            is_public: Pass True to remove the public photo, which is visible even if the main photo
                is hidden by the business account's privacy settings. After the main photo is removed,
                the previous profile photo (if present) becomes the main photo.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "is_public": is_public,
        }
        response = self._make_request(
            "removeBusinessAccountProfilePhoto", method="POST", data=payload
        )
        return bool(response)

    def set_business_account_gift_settings(
        self,
        business_connection_id: str,
        show_gift_button: bool,
        accepted_gift_types: AcceptedGiftTypes,
    ) -> bool:
        """
        Change the privacy settings for incoming gifts in a managed business account.
        Requires the 'can_change_gift_settings' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            show_gift_button: Pass True, if a button for sending a gift to the user
                or by the business account must always be shown in the input field.
            accepted_gift_types: Types of gifts accepted by the business account.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "show_gift_button": show_gift_button,
            "accepted_gift_types": accepted_gift_types,
        }
        response = self._make_request(
            "setBusinessAccountGiftSettings", method="POST", data=payload
        )
        return bool(response)

    def get_business_account_star_balance(
        self, business_connection_id: str
    ) -> AcceptedGiftTypes:
        """
        Get the amount of Telegram Stars owned by a managed business account.
        Requires the 'can_view_gifts_and_stars' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection
        """
        payload = {"business_connection_id": business_connection_id}
        response = self._make_request(
            "getBusinessAccountStarBalance", method="GET", params=payload
        )
        return AcceptedGiftTypes.model_validate(response)

    def transfer_business_account_stars(
        self, business_connection_id: str, star_count: int
    ) -> bool:
        """
        Transfer Telegram Stars from the business account balance to the bot's balance.
        Requires the 'can_transfer_stars' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            star_count: Number of Telegram Stars to transfer; 1-10000
        """
        payload = {
            "business_connection_id": business_connection_id,
            "star_count": star_count,
        }
        response = self._make_request(
            "transferBusinessAccountStars", method="POST", data=payload
        )
        return bool(response)

    def get_business_account_gifts(
        self,
        business_connection_id: str,
        exclude_unsaved: bool | None = None,
        exclude_saved: bool | None = None,
        exclude_unlimited: bool | None = None,
        exclude_limited: bool | None = None,
        exclude_unique: bool | None = None,
        sort_by_price: bool | None = None,
        offset: str | None = None,
        limit: int | None = None,
    ) -> OwnedGift:
        """
        Get the list of gifts received and owned by a managed business account.
        Requires the 'can_view_gifts_and_stars' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.

            See full parameters here: [getBusinessAccountGifts](https://core.telegram.org/bots/api#getbusinessaccountgifts)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "exclude_unsaved": exclude_unsaved,
            "exclude_saved": exclude_saved,
            "exclude_unlimited": exclude_unlimited,
            "exclude_limited": exclude_limited,
            "exclude_unique": exclude_unique,
            "sort_by_price": sort_by_price,
            "offset": offset,
            "limit": limit,
        }
        response = self._make_request(
            "getBusinessAccountGifts", method="GET", params=payload
        )
        return OwnedGiftAdapter.validate_python(response)

    def get_user_gift(
        self,
        user_id: str,
        exclude_unlimited: bool | None = None,
        exclude_limited_upgradable: bool | None = None,
        exclude_limited_non_upgradable: bool | None = None,
        exclude_from_blockchain: bool | None = None,
        exclude_unique: bool | None = None,
        sort_by_price: bool | None = None,
        offset: str | None = None,
        limit: int | None = None,
    ) -> OwnedGift:
        """
        Returns the gifts owned and hosted by a user.

        Args:
            user_id: Unique identifier of the user.

            See full parameters here: [getUserGifts](https://core.telegram.org/bots/api#getusergifts)
        """
        payload = {
            "user_id": user_id,
            "exclude_unlimited": exclude_unlimited,
            "exclude_limited_upgradable": exclude_limited_upgradable,
            "exclude_limited_non_upgradable": exclude_limited_non_upgradable,
            "exclude_from_blockchain": exclude_from_blockchain,
            "exclude_unique": exclude_unique,
            "sort_by_price": sort_by_price,
            "offset": offset,
            "limit": limit,
        }
        response = self._make_request("getUserGifts", method="GET", params=payload)
        return OwnedGiftAdapter.validate_python(response)

    def get_chat_gift(
        self,
        chat_id: str | int,
        exclude_unsaved: bool | None = None,
        exclude_saved: bool | None = None,
        exclude_unlimited: bool | None = None,
        exclude_limited_upgradable: bool | None = None,
        exclude_limited_non_upgradable: bool | None = None,
        exclude_from_blockchain: bool | None = None,
        exclude_unique: bool | None = None,
        sort_by_price: bool | None = None,
        offset: str | None = None,
        limit: int | None = None,
    ) -> OwnedGift:
        """
        Returns the gifts owned by a chat.

        Args:
            chat_id: Unique identifier for the target chat or @username of the channel.

            See full parameters here: [getChatGifts](https://core.telegram.org/bots/api#getchatgifts)
        """
        payload = {
            "chat_id": chat_id,
            "exclude_unsaved": exclude_unsaved,
            "exclude_saved": exclude_saved,
            "exclude_unlimited": exclude_unlimited,
            "exclude_limited_upgradable": exclude_limited_upgradable,
            "exclude_limited_non_upgradable": exclude_limited_non_upgradable,
            "exclude_from_blockchain": exclude_from_blockchain,
            "exclude_unique": exclude_unique,
            "sort_by_price": sort_by_price,
            "offset": offset,
            "limit": limit,
        }
        response = self._make_request("getChatGifts", method="GET", params=payload)
        return OwnedGiftAdapter.validate_python(response)

    def convert_gift_to_stars(
        self, business_connection_id: str, owned_gift_id: str
    ) -> bool:
        """
        Convert a regular gift to Telegram Stars.
        Requires the 'can_convert_gifts_to_stars' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            owned_gift_id: Unique identifier of the regular gift that should be converted to Telegram Stars.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "owned_gift_id": owned_gift_id,
        }
        response = self._make_request("convertGiftToStars", method="POST", data=payload)
        return bool(response)

    def upgrade_gift(
        self,
        business_connection_id: str,
        owned_gift_id: str,
        keep_original_details: bool | None = None,
        star_count: int | None = None,
    ) -> bool:
        """
        Upgrade a regular gift to a unique gift.
        Requires the 'can_transfer_and_upgrade_gifts' business bot right.
        If the upgrade is paid, the 'can_transfer_stars' right is also required.

        Args:
            business_connection_id: Unique identifier of the business connection.
            owned_gift_id: Unique identifier of the regular gift that should be upgraded to a unique one.

            See full parameters here: [upgradeGift](https://core.telegram.org/bots/api#upgradegift)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "owned_gift_id": owned_gift_id,
            "keep_original_details": keep_original_details,
            "star_count": star_count,
        }
        response = self._make_request("upgradeGift", method="POST", data=payload)
        return bool(response)

    def transfer_gift(
        self,
        business_connection_id: str,
        owned_gift_id: str,
        new_owner_chat_id: int,
        star_count: int | None = None,
    ) -> bool:
        """
        Transfer an owned unique gift to another user.
        Requires the 'can_transfer_and_upgrade_gifts' business bot right.
        If the transfer is paid, the 'can_transfer_stars' right is required.

        Args:
            business_connection_id: Unique identifier of the business connection.
            owned_gift_id: Unique identifier of the regular gift that should be transferred.
            new_owner_chat_id: Unique identifier of the chat which will own the gift.
                The chat must be active in the last 24 hours.
            star_count: The amount of Telegram Stars that will be paid for the transfer from the business account balance.
                If positive, then the can_transfer_stars business bot right is required.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "owned_gift_id": owned_gift_id,
            "new_owner_chat_id": new_owner_chat_id,
            "star_count": star_count,
        }
        response = self._make_request("transferGift", method="POST", data=payload)
        return bool(response)

    def post_story(
        self,
        business_connection_id: str,
        content: InputStoryContent,
        active_period: int,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        areas: List[StoryArea] | None = None,
        post_to_chat_page: bool | None = None,
        protect_content: bool | None = None,
    ) -> Story:
        """
        Post a story on behalf of a managed business account.
        Requires the 'can_manage_stories' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            content: Content of the story.
            active_period: Duration in seconds after which the story expires.
                Must be one of: 21600 (6h), 43200 (12h), 86400 (1d), or 172800 (2d).

            See full parameters here: [postStory](https://core.telegram.org/bots/api#poststory)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "content": content,
            "active_period": active_period,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "areas": areas,
            "post_to_chat_page": post_to_chat_page,
            "protect_content": protect_content,
        }
        response = self._make_request("postStory", method="POST", data=payload)
        return Story.model_validate(response)

    def repost_story(
        self,
        business_connection_id: str,
        from_chat_id: int,
        from_story_id: int,
        active_period: int,
        post_to_chat_page: bool | None = None,
        protect_content: bool | None = None,
    ) -> Story:
        """
        Post a story on behalf of a managed business account.
        Requires the 'can_manage_stories' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            from_chat_id: Unique identifier of the chat which posted the story that should be reposted.
            from_story_id: Unique identifier of the story that should be reposted.
            active_period: Duration in seconds after which the story expires.
                Must be one of: 21600 (6h), 43200 (12h), 86400 (1d), or 172800 (2d).
            post_to_chat_page: Pass True to keep the story accessible after it expires.
            protect_content: Pass True if the content of the story must be protected from forwarding and screenshotting.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "from_chat_id": from_chat_id,
            "from_story_id": from_story_id,
            "active_period": active_period,
            "post_to_chat_page": post_to_chat_page,
            "protect_content": protect_content,
        }
        response = self._make_request("repostStory", method="POST", data=payload)
        return Story.model_validate(response)

    def edit_story(
        self,
        business_connection_id: str,
        story_id: int,
        content: InputStoryContent,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        areas: List[StoryArea] | None = None,
    ) -> Story:
        """
        Edit a story previously posted by the bot on behalf of a managed business account.
        Requires the 'can_manage_stories' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            story_id: Unique identifier of the story to edit.
            content: Content of the story.

            See full parameters here: [editStory](https://core.telegram.org/bots/api#editstory)
        """
        payload = {
            "business_connection_id": business_connection_id,
            "story_id": story_id,
            "content": content,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "areas": areas,
        }
        response = self._make_request("editStory", method="POST", data=payload)
        return Story.model_validate(response)

    def delete_story(self, business_connection_id: str, story_id: int) -> bool:
        """
        Delete a story previously posted by the bot on behalf of a managed business account.
        Requires the 'can_manage_stories' business bot right.

        Args:
            business_connection_id: Unique identifier of the business connection.
            story_id: Unique identifier of the story to delete.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "story_id": story_id,
        }
        response = self._make_request("deleteStory", method="POST", data=payload)
        return bool(response)

    def answer_web_app_query(
        self, web_app_query_id: str, result: InlineQueryResult
    ) -> SentWebAppMessage:
        """
        Set the result of an interaction with a Web App and send a corresponding message on behalf of the user
        to the chat from which the query originated.

        Args:
            web_app_query_id: Unique identifier for the query to be answered.
            result: A InlineQueryResult object describing the message to be sent
        """
        payload = {"web_app_query_id": web_app_query_id, "result": result}
        response = self._make_request("answerWebAppQuery", method="POST", data=payload)
        return SentWebAppMessage.model_validate(response)

    def save_prepared_inline_message(
        self,
        user_id: int,
        result: InlineQueryResult,
        allow_user_chats: bool | None = None,
        allow_bot_chats: bool | None = None,
        allow_group_chats: bool | None = None,
        allow_channel_chats: bool | None = None,
    ) -> PreparedInlineMessage:
        """
        Store a message that can be sent by a user of a Mini App.
        This allows the Mini App to prepare a message in advance, which the user can send later with a single tap.

        Args:
            user_id: Unique identifier of the target user that can use the prepared message.
            result: A InlineQueryResult object describing the message to be sent.

            See full parameters here: [savePreparedInlineMessage](https://core.telegram.org/bots/api#savepreparedinlinemessage)
        """
        payload = {
            "user_id": user_id,
            "result": result,
            "allow_user_chats": allow_user_chats,
            "allow_bot_chats": allow_bot_chats,
            "allow_group_chats": allow_group_chats,
            "allow_channel_chats": allow_channel_chats,
        }
        response = self._make_request(
            "savePreparedInlineMessage", method="POST", data=payload
        )
        return PreparedInlineMessage.model_validate(response)

    def save_prepared_keyboard_button(
        self, user_id: int, button: KeyboardButton
    ) -> PreparedKeyboardButton:
        """
        Stores a keyboard button that can be used by a user within a Mini App.

        Args:
            user_id: Unique identifier of the target user that can use the prepared message.
            button: A KeyboardButton object describing the button to be saved.
                The button must be of the type request_users, request_chat, or request_managed_bot.
        """
        payload = {"user_id": user_id, "button": button}
        response = self._make_request(
            "savePreparedKeyboardButton", method="POST", data=payload
        )
        return PreparedKeyboardButton.model_validate(response)

    def edit_message_text(
        self,
        text: str | None = None,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        parse_mode: str | None = "html",
        entities: List[MessageEntity] | None = None,
        link_preview_options: LinkPreviewOptions | None = None,
        rich_message: InputRichMessage | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit the text and game messages.

        Args:
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id:Required if inline_message_id is not specified. Identifier of the message to edit.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
            text: New text of the message, 1-4096 characters after entity parsing; required if rich_message isn't specified.

           See full parameters here: [editMessageText](https://core.telegram.org/bots/api#editmessagetext)

        Note:
            business messages that were not sent by the bot and do not contain an inline keyboard
            can only be edited within 48 hours from the time they were sent.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "text": text,
            "parse_mode": parse_mode,
            "entities": entities,
            "link_preview_options": link_preview_options,
            "rich_message": rich_message,
            "reply_markup": reply_markup,
        }
        response = self._make_request("editMessageText", method="POST", data=payload)
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def edit_message_caption(
        self,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        caption: str | None = None,
        parse_mode: str | None = "html",
        caption_entities: List[MessageEntity] | None = None,
        show_caption_above_media: bool | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit the caption of messages.

        Args:
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id:Required if inline_message_id is not specified. Identifier of the message to edit.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
            caption: New caption of the message, 0-1024 characters after entities parsing.

            See full parameters here: [editMessageCaption](https://core.telegram.org/bots/api#editmessagecaption)

        Note:
            business messages that were not sent by the bot and do not contain an inline keyboard
            can only be edited within 48 hours from the time they were sent.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "caption": caption,
            "parse_mode": parse_mode,
            "caption_entities": caption_entities,
            "show_caption_above_media": show_caption_above_media,
            "reply_markup": reply_markup,
        }
        response = self._make_request("editMessageCaption", method="POST", data=payload)
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def edit_message_media(
        self,
        media: InputMedia,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit the media content of a message (animation, audio, document, photo, video) or add media to a text message.
        When editing inline messages, a new file cannot be uploaded; use existing file_id or URL.

        Args:
            media: A InputMedia object representing the new media content (InputMediaPhoto, InputMediaVideo, etc.).
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id: Required if inline_message_id is not specified. Identifier of the message to edit.
            business_connection_id: Unique identifier of the business connection on behalf of which the message was sent.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
            reply_markup: A InlineKeyboardMarkup object for a new inline keyboard.

        Note:
            business messages that were not sent by the bot and do not contain an inline keyboard
            can only be edited within 48 hours from the time they were sent.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "media": media,
            "reply_markup": reply_markup,
        }
        response = self._make_request("editMessageMedia", method="POST", data=payload)
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def edit_message_live_location(
        self,
        latitude: float,
        longitude: float,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        live_period: int | None = None,
        horizontal_accuracy: float | None = None,
        heading: int | None = None,
        proximity_alert_radius: int | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit live location messages.

        Location can be edited until live_period expires or until stopMessageLiveLocation is called.

        Args:
            latitude: New latitude of the location.
            longitude: New longitude of the location.
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id: Required if inline_message_id is not specified. Identifier of the message to edit.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.

            See full parameters here: [editMessageLiveLocation](https://core.telegram.org/bots/api#editmessagelivelocation)
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "latitude": latitude,
            "longitude": longitude,
            "live_period": live_period,
            "horizontal_accuracy": horizontal_accuracy,
            "heading": heading,
            "proximity_alert_radius": proximity_alert_radius,
            "reply_markup": reply_markup,
        }

        response = self._make_request(
            "editMessageLiveLocation", method="POST", data=payload
        )
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def stop_message_live_location(
        self,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Stop updating a live location message before live_period expires.

        Args:
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id: Required if inline_message_id is not specified. Identifier of the message to edit.
            business_connection_id: Unique identifier of the business connection on behalf of which the message was sent.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
            reply_markup: A InlineKeyboardMarkup object for a new inline keyboard.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "reply_markup": reply_markup,
        }
        response = self._make_request(
            "stopMessageLiveLocation", method="POST", data=payload
        )
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def edit_message_checklist(
        self,
        business_connection_id: str,
        chat_id: int,
        message_id: int,
        checklist: InputChecklist,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit a checklist on behalf of a connected business account.

        Args:
            business_connection_id: Unique identifier of the business connection on behalf of which the message will be sent.
            chat_id: Chat ID or @username of the target chat/bot.
            message_id: Unique identifier for the target message.
            checklist: A InputChecklist object for the new checklist.
            reply_markup: A InlineKeyboardMarkup object for a new inline keyboard.
        """
        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "checklist": checklist,
            "reply_markup": reply_markup,
        }
        response = self._make_request(
            "editMessageChecklist", method="POST", data=payload
        )
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def edit_message_reply_markup(
        self,
        business_connection_id: str | None = None,
        chat_id: int | str | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message | bool:
        """
        Edit only the reply markup (inline keyboard) of a message.

        Args:
            business_connection_id: Unique identifier of the business connection on behalf of which the message was sent.
            chat_id: Required if `inline_message_id` not specified. Target chat ID or @username (supergroup/channel).
            message_id: Required if inline_message_id is not specified. Identifier of the message to edit.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
            reply_markup: A InlineKeyboardMarkup object for a new inline keyboard.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "business_connection_id": business_connection_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
            "reply_markup": reply_markup,
        }
        response = self._make_request(
            "editMessageReplyMarkup", method="POST", data=payload
        )
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def stop_poll(
        self,
        chat_id: int | str,
        message_id: int,
        business_connection_id: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Poll:
        """
        Stop a poll that was sent by the bot.
        On success, the stopped Poll object is returned.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            message_id: Identifier of the original message with the poll.
            business_connection_id: Unique identifier of the business connection on behalf of which the message was sent.
            reply_markup: A InlineKeyboardMarkup object for a new inline keyboard attached to the message.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "business_connection_id": business_connection_id,
            "reply_markup": reply_markup,
        }
        response = self._make_request("stopPoll", method="POST", data=payload)
        return Poll.model_validate(response)

    def approve_suggested_post(
        self, chat_id: int, message_id: int, send_date: int | None = None
    ) -> bool:
        """
        Approve a suggested post in a direct messages chat.
        The bot must have the 'can_post_messages' administrator right in the corresponding channel chat.

        Args:
            chat_id: Unique identifier for the target direct messages chat.
            message_id: Identifier of a suggested post message to approve.
            send_date: Point in time (Unix timestamp) when the post is expected to be published;
                omit if the date has already been specified when the suggested post was created.
                If specified, then the date must be not more than 2678400 seconds (30 days) in the future.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "send_date": send_date,
        }
        response = self._make_request(
            "approveSuggestedPost", method="POST", data=payload
        )
        return bool(response)

    def decline_suggested_post(
        self, chat_id: int, message_id: int, comment: str | None = None
    ) -> bool:
        """
        Decline a suggested post in a direct messages chat.
        The bot must have the 'can_manage_direct_messages' administrator right in the corresponding channel chat.

        Args:
            chat_id: Unique identifier for the target direct messages chat.
            message_id: Identifier of a suggested post message to decline.
            comment: Comment for the creator of the suggested post; 0-128 characters.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "comment": comment,
        }
        response = self._make_request(
            "declineSuggestedPost", method="POST", data=payload
        )
        return bool(response)

    def delete_message(self, chat_id: int | str, message_id: int) -> bool:
        """
        Delete a message, including service messages, with the following limitations:
        - The message must have been sent less than 48 hours ago.
        - Service messages about supergroup/channel/forum topic creation cannot be deleted.
        - A dice message in a private chat can only be deleted if sent more than 24 hours ago.
        - Bots can delete outgoing messages in private chats, groups, and supergroups.
        - Bots can delete incoming messages in private chats.
        - Bots with 'can_post_messages' can delete outgoing messages in channels.
        - Administrators can delete any message in groups.
        - Bots with 'can_delete_messages' right can delete any message in supergroups and channels.
        - Bots with 'can_manage_direct_messages' right can delete any message in direct messages chats.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            message_id: Identifier of the message to delete.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        response = self._make_request("deleteMessage", method="POST", data=payload)
        return bool(response)

    def delete_messages(self, chat_id: int | str, message_ids: List[int]) -> bool:
        """
        Delete multiple messages simultaneously.
        If some messages can't be found or deleted, they are simply skipped.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            message_ids: A list of 1-100 identifiers of messages to delete.
                See `delete_message()` for limitations on which messages can be deleted.
        """
        payload = {"chat_id": chat_id, "message_ids": message_ids}
        response = self._make_request("deleteMessages", method="POST", data=payload)
        return bool(response)

    def delete_message_reaction(
        self, chat_id: int | str, message_id: int, user_id: int, actor_chat_id: int
    ) -> bool:
        """
        Use this method to remove a reaction from a message in a group or a supergroup chat.
        The bot must have the 'can_delete_messages' administrator right in the chat.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            message_id: Identifier of the target message.
            user_id: Identifier of the user whose reaction will be removed, if the reaction was added by a user.
            actor_chat_id: Identifier of the chat whose reaction will be removed, if the reaction was added by a chat.
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "user_id": user_id,
            "actor_chat_id": actor_chat_id,
        }
        response = self._make_request(
            "deleteMessageReaction", method="POST", data=payload
        )
        return bool(response)

    def delete_message_reactions(
        self, chat_id: int | str, user_id: int, actor_chat_id: int
    ) -> bool:
        """
        Use this method to remove up to 10000 recent reactions in a
        group or a supergroup chat added by a given user or chat.
        The bot must have the 'can_delete_messages' administrator right in the chat.

        Args:
            chat_id: Unique identifier for the target chat or @username of the supergroup.
            user_id: Identifier of the user whose reactions will be removed, if the reactions were added by a user.
            actor_chat_id: Identifier of the chat whose reactions will be removed, if the reactions were added by a chat.
        """
        payload = {
            "chat_id": chat_id,
            "user_id": user_id,
            "actor_chat_id": actor_chat_id,
        }
        response = self._make_request(
            "deleteAllMessageReactions", method="POST", data=payload
        )
        return bool(response)

    def send_sticker(
        self,
        chat_id: int | str,
        sticker: InputFile | str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        emoji: str | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Send static .WEBP, animated .TGS, or video .WEBM stickers.
        On success, the sent Message is returned.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            sticker: Sticker to send. Can be a file_id (str), URL (str), or raw bytes.

                For static stickers: .WEBP or .PNG
                For animated stickers: .TGS
                For video stickers: .WEBM
                Note: Video and animated stickers cannot be sent via HTTP URL.

            - See full parameters here: [sendSticker](https://core.telegram.org/bots/api#sendsticker)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "emoji": emoji,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        if isinstance(sticker, bytes):
            # Upload new sticker → use POST + multipart/form-data
            files = {"sticker": sticker}
            payload["sticker"] = None
            response = self._make_request(
                "sendSticker", method="POST", data=payload, files=files
            )
        else:
            # Reuse existing file_id or URL → use POST (GET not supported for stickers)
            payload["sticker"] = sticker
            response = self._make_request("sendSticker", method="POST", data=payload)

        return Message.model_validate(response)

    def get_sticker_set(self, name: str) -> StickerSet:
        """
        Get information about a sticker set.

        Args:
            name: Name of the sticker set.
        """
        payload = {"name": name}
        response = self._make_request("getStickerSet", method="GET", params=payload)
        return StickerSet.model_validate(response)

    def get_custom_emoji_stickers(self, custom_emoji_ids: List[str]) -> Sticker:
        """
        Get information about custom emoji stickers by their identifiers.

        Args:
            custom_emoji_ids: A list of custom emoji identifiers.
                At most 200 custom emoji identifiers can be specified.
        """
        payload = {"custom_emoji_ids": custom_emoji_ids}
        response = self._make_request(
            "getCustomEmojiStickers", method="POST", data=payload
        )
        return Sticker.model_validate(response)

    def upload_sticker_file(
        self, user_id: int, sticker: InputFile, sticker_format: str
    ) -> File:
        """
        Upload a sticker file for later use in creating or editing sticker sets.
        The file can be reused multiple times.

        Args:
            user_id: User identifier of sticker file owner.
            sticker: File with the sticker in
                .WEBP (static)
                .PNG (static)
                .TGS (animated)
                .WEBM (video) format.
                See [stickers](https://core.telegram.org/stickers) for technical requirements.
            sticker_format: Format of the sticker, must be one of `static`, `animated`, `video`.
        """
        files = {"sticker": sticker}
        payload = {
            "user_id": user_id,
            "sticker_format": sticker_format,
        }
        response = self._make_request(
            "uploadStickerFile", method="POST", data=payload, files=files
        )
        return File.model_validate(response)

    def create_new_sticker_set(
        self,
        user_id: int,
        name: str,
        title: str,
        stickers: List[InputSticker],
        sticker_type: str | None = "regular",
        needs_repainting: bool | None = None,
    ) -> bool:
        """
        Create a new sticker set owned by a user. The bot will be able to edit this set.

        Args:
            user_id: User identifier of created sticker set owner.
            name: Short name of sticker set, to be used in t.me/addstickers/ URLs (e.g., animals).
                Can contain only English letters, digits and underscores.
                Must begin with a letter.
                Can't contain consecutive underscores.
                Must end in `_by_<bot_username>` (bot username is case insensitive).
                Length: 1-64 characters.
            title: Sticker set title, 1-64 characters.
            stickers: A list of InputSticker, 1-50 initial stickers to be added to the sticker set.
            sticker_type: Type of stickers in the set, pass `regular`, `mask`, or `custom_emoji`.
            needs_repainting: Pass True if stickers in the sticker set must be repainted to the color of text
                when used in messages, the accent color if used as emoji status, white on chat photos,
                or another appropriate color based on context; for custom emoji sticker sets only.
        """
        payload = {
            "user_id": user_id,
            "name": name,
            "title": title,
            "stickers": stickers,
            "sticker_type": sticker_type,
            "needs_repainting": needs_repainting,
        }
        response = self._make_request(
            "createNewStickerSet", method="POST", data=payload
        )
        return bool(response)

    def add_sticker_to_set(
        self, user_id: int, name: str, sticker: InputSticker
    ) -> bool:
        """
        Add a new sticker to a set created by the bot.
        - Regular/mask sets: up to 120 stickers.
        - Custom emoji sets: up to 200 stickers.

        Args:
            user_id: User identifier of the sticker set owner.
            name: Sticker set name.
            sticker: A InputSticker object with information about the added sticker.
                If exactly the same sticker had already been added to the set, then the set isn't changed.
        """
        payload = {"user_id": user_id, "name": name, "sticker": sticker}
        response = self._make_request("addStickerToSet", method="POST", data=payload)
        return bool(response)

    def set_sticker_position_in_set(self, sticker: str, position: int) -> bool:
        """
        Move a sticker in a bot-created set to a specific position (zero-based index).

        Args:
            sticker: File identifier of the sticker.
            position: New sticker position in the set, zero-based
        """
        payload = {
            "sticker": sticker,
            "position": position,
        }
        response = self._make_request(
            "setStickerPositionInSet", method="POST", data=payload
        )
        return bool(response)

    def delete_sticker_from_set(self, sticker: str) -> bool:
        """
        Delete a sticker from a set created by the bot.

        Args:
            sticker: File identifier of the sticker to delete.
        """
        payload = {"sticker": sticker}
        response = self._make_request(
            "deleteStickerFromSet", method="POST", data=payload
        )
        return bool(response)

    def replace_sticker_in_set(
        self, user_id: int, name: str, old_sticker: str, sticker: InputSticker
    ) -> bool:
        """
        Replace an existing sticker in a set with a new one.
        Equivalent to: delete → add → set position.

        Args:
            user_id: User identifier of the sticker set owner.
            name: NSticker set name.
            old_sticker: File identifier of the replaced sticker.
            sticker:A InputSticker object with information about the added sticker.
                If exactly the same sticker had already been added to the set, then the set remains unchanged.
        """
        payload = {
            "user_id": user_id,
            "name": name,
            "old_sticker": old_sticker,
            "sticker": sticker,
        }
        response = self._make_request(
            "replaceStickerInSet", method="POST", data=payload
        )
        return bool(response)

    def set_sticker_emoji_list(self, sticker: str, emoji_list: List[str]) -> bool:
        """
        Change the list of emoji associated with a regular or custom emoji sticker.
        The sticker must belong to a bot-created set.

        Args:
            sticker: File identifier of the sticker.
            emoji_list: A list of 1-20 emoji associated with the sticker.
        """
        payload = {"sticker": sticker, "emoji_list": emoji_list}
        response = self._make_request(
            "setStickerEmojiList", method="POST", data=payload
        )
        return bool(response)

    def set_sticker_keywords(
        self, sticker: str, keywords: List[str] | None = None
    ) -> bool:
        """
        Change search keywords for a regular or custom emoji sticker.
        Total length of all keywords must not exceed 64 characters.
        The sticker must belong to a bot-created set.

        Args:
            sticker: File identifier of the sticker.
            keywords: A list of 0-20 search keywords for the sticker with total length of up to 64 characters
        """
        payload = {"sticker": sticker, "keywords": keywords}
        response = self._make_request("setStickerKeywords", method="POST", data=payload)
        return bool(response)

    def set_sticker_mask_position(
        self, sticker: str, mask_position: MaskPosition | None = None
    ) -> bool:
        """
        Change the mask position of a mask sticker.
        The sticker must belong to a sticker set created by the bot.
        Omit the mask_position parameter to remove the current mask position.

        Args:
            sticker: File identifier of the mask sticker.
            mask_position: A object with the position where the mask should be placed on faces.
                Omit the parameter to remove the mask position.
        """
        payload = {"sticker": sticker, "mask_position": mask_position}
        response = self._make_request(
            "setStickerMaskPosition", method="POST", data=payload
        )
        return bool(response)

    def set_sticker_set_title(self, name: str, title: str) -> bool:
        """
        Set the title of a sticker set created by the bot.

        Args:
            name: Sticker set name.
            title: Sticker set title, 1-64 characters.
        """
        payload = {
            "name": name,
            "title": title,
        }
        response = self._make_request("setStickerSetTitle", method="POST", data=payload)
        return bool(response)

    def set_sticker_set_thumbnail(
        self,
        name: str,
        user_id: int,
        thumbnail: InputFile | str | None = None,
        _format: str = "static",
    ) -> bool:
        """
        Set the thumbnail of a regular or mask sticker set.
        The format of the thumbnail must match the format of the stickers in the set.

        - For 'static' sets: a .WEBP or .PNG image, exactly 100x100px, up to 128 KB.
        - For 'animated' sets: a .TGS animation, up to 32 KB.
        - For 'video' sets: a .WEBM video, up to 32 KB.

        Animated and video thumbnails cannot be uploaded via HTTP URL.
        If thumbnail is omitted, the thumbnail is removed and the first sticker becomes the thumbnail.

        Args:
            name: Sticker set name.
            user_id: User identifier of the sticker set owner.
            thumbnail: Thumbnail file to upload (bytes), file_id (str), or HTTP URL (str).
                If None, removes the current thumbnail.
            format: Format of the thumbnail: 'static', 'animated', or 'video'.
        """
        payload = {
            "name": name,
            "user_id": user_id,
            "format": _format,
        }
        files = None
        if isinstance(thumbnail, bytes):
            files = {"thumbnail": thumbnail}
            payload["thumbnail"] = None

        elif thumbnail is not None:
            payload["thumbnail"] = thumbnail

        # else: omit thumbnail to drop it
        response = self._make_request(
            "setStickerSetThumbnail", method="POST", data=payload, files=files
        )
        return bool(response)

    def set_custom_emoji_sticker_set_thumbnail(
        self, name: str, custom_emoji_id: str | None = ""
    ) -> bool:
        """
        Set the thumbnail of a custom emoji sticker set.

        Args:
            name: Sticker set name.
            custom_emoji_id: Custom emoji identifier of a sticker from the sticker set; pass an empty string
                to drop the thumbnail and use the first sticker as the thumbnail
        """
        payload = {
            "name": name,
            "custom_emoji_id": custom_emoji_id,
        }
        # We include custom_emoji_id even if None (to allow empty string for removal)
        response = self._make_request(
            "setCustomEmojiStickerSetThumbnail", method="POST", data=payload
        )
        return bool(response)

    def delete_sticker_set(self, name: str) -> bool:
        """
        Delete a sticker set that was created by the bot.

        Args:
            name: Sticker set name.
        """
        payload = {"name": name}
        response = self._make_request("deleteStickerSet", method="POST", data=payload)
        return bool(response)

    def send_rich_message(
        self,
        chat_id: int | str,
        rich_message: InputRichMessage,
        message_thread_id: int | None = None,
        business_connection_id: str | None = None,
        direct_messages_topic_id: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: ReplyMarkup | None = None,
    ) -> Message:
        """
        Use this method to send rich messages. If the message contains a block with a media element,
        then the bot must have the right to send the media to the chat.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            rich_message: The message to be sent.

            See full parameters here: [sendRichMessage](https://core.telegram.org/bots/api#sendrichmessage)
        """
        payload = {
            "chat_id": chat_id,
            "rich_message": rich_message,
            "message_thread_id": message_thread_id,
            "business_connection_id": business_connection_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendRichMessage", method="POST", data=payload)
        return Message.model_validate(response)

    def send_rich_message_draft(
        self,
        chat_id: int,
        draft_id: int,
        rich_message: InputRichMessage,
        message_thread_id: int | None = None,
    ):
        """
        Use this method to stream a partial rich message to a user while the message is being generated.
        Note that the streamed draft is ephemeral and acts as a temporary 30-second preview - once the output is finalized,
        you must call `send_rich_message()` with the complete message to persist it in the user's chat.

        Args:
            chat_id: Unique identifier for the target private chat.
            draft_id: Unique identifier of the message draft; must be non-zero.
                Changes to drafts with the same identifier are animated.
            rich_message: The partial message to be streamed.
            message_thread_id: Unique identifier for the target message thread.
        """
        payload = {
            "chat_id": chat_id,
            "draft_id": draft_id,
            "rich_message": rich_message,
            "message_thread_id": message_thread_id,
        }
        response = self._make_request(
            "sendRichMessageDraft", method="POST", data=payload
        )
        return bool(response)

    def answer_inline_query(
        self,
        inline_query_id: str,
        results: List[InlineQueryResult],
        cache_time: int | None = None,
        is_personal: bool | None = None,
        next_offset: str | None = None,
        button: InlineQueryResultsButton | None = None,
    ) -> bool:
        """
        Send answers to an incoming inline query.
        On success, True is returned.
        No more than 50 results per query are allowed.

        Args:
            inline_query_id: Unique identifier for the answered query.
            results: A InlineQueryResult array of results for the inline query.
            cache_time: The maximum amount of time in seconds that the result of
                the query may be cached on the server. Defaults to 300.
            is_personal: Pass True if results are meant only for the user that sent the query.
                Otherwise, results may be cached for all users.
            next_offset: Pass the offset that clients should send in the next query to receive more results.
                Pass empty string if no more results.
            button: A InlineQueryResultsButton object describing a button to be shown above the results.
        """
        payload = {
            "inline_query_id": inline_query_id,
            "results": results,
            "cache_time": cache_time,
            "is_personal": is_personal,
            "next_offset": next_offset,
            "button": button,
        }
        response = self._make_request("answerInlineQuery", method="POST", data=payload)
        return bool(response)

    def send_invoice(
        self,
        chat_id: int | str,
        title: str,
        description: str,
        payload: str,
        currency: str,
        prices: List[LabeledPrice],
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        provider_token: str | None = None,
        max_tip_amount: int | None = None,
        suggested_tip_amounts: List[int] | None = None,
        start_parameter: str | None = None,
        provider_data: str | None = None,
        photo_url: str | None = None,
        photo_size: int | None = None,
        photo_width: int | None = None,
        photo_height: int | None = None,
        need_name: bool | None = None,
        need_phone_number: bool | None = None,
        need_email: bool | None = None,
        need_shipping_address: bool | None = None,
        send_phone_number_to_provider: bool | None = None,
        send_email_to_provider: bool | None = None,
        is_flexible: bool | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        suggested_post_parameters: SuggestedPostParameters | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message:
        """
        Send an invoice for payment.

        Args:
            chat_id: Chat ID or @username of the target chat, supergroup or channel.
            title: Product name, 1-32 characters.
            description: Product description, 1-255 characters.
            payload: Bot-defined invoice payload, 1-128 bytes. This will not be displayed to the user,
                use it for your internal processes.
            currency: Three-letter ISO 4217 currency code, see more on currencies.
                Pass “XTR” for payments in Telegram Stars.
            prices: Price breakdown, a LabeledPrice list of components (e.g. product price, tax, discount,
                delivery cost, delivery tax, bonus, etc.).
                Must contain exactly one item for payments in Telegram Stars.

            See full parameters here: [sendInvoice](https://core.telegram.org/bots/api#sendinvoice)
        """
        if currency == "XTR" and (provider_token is not None and provider_token != ""):
            raise ValueError(
                "For payments in Telegram Stars (XTR), provider_token must be an empty string."
            )

        payload_data = {
            "chat_id": chat_id,
            "message_thread_id": message_thread_id,
            "direct_messages_topic_id": direct_messages_topic_id,
            "title": title,
            "description": description,
            "payload": payload,
            "provider_token": provider_token,
            "currency": currency,
            "prices": prices,
            "max_tip_amount": max_tip_amount,
            "suggested_tip_amounts": suggested_tip_amounts,
            "start_parameter": start_parameter,
            "provider_data": provider_data,
            "photo_url": photo_url,
            "photo_size": photo_size,
            "photo_width": photo_width,
            "photo_height": photo_height,
            "need_name": need_name,
            "need_phone_number": need_phone_number,
            "need_email": need_email,
            "need_shipping_address": need_shipping_address,
            "send_phone_number_to_provider": send_phone_number_to_provider,
            "send_email_to_provider": send_email_to_provider,
            "is_flexible": is_flexible,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "suggested_post_parameters": suggested_post_parameters,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendInvoice", method="POST", data=payload_data)
        return Message.model_validate(response)

    def create_invoice_link(
        self,
        title: str,
        description: str,
        payload: str,
        currency: str,
        prices: List[LabeledPrice],
        business_connection_id: str | None = None,
        provider_token: str | None = None,
        subscription_period: int | None = None,
        max_tip_amount: int | None = None,
        suggested_tip_amounts: List[int] | None = None,
        provider_data: str | None = None,
        photo_url: str | None = None,
        photo_size: int | None = None,
        photo_width: int | None = None,
        photo_height: int | None = None,
        need_name: bool | None = None,
        need_phone_number: bool | None = None,
        need_email: bool | None = None,
        need_shipping_address: bool | None = None,
        send_phone_number_to_provider: bool | None = None,
        send_email_to_provider: bool | None = None,
        is_flexible: bool | None = None,
    ) -> str:
        """
        Create a direct link for an invoice. This link can be used to open the payment interface directly.

        Args:
            title: Product name, 1-32 characters.
            description: Product description, 1-255 characters.
            payload: Bot-defined invoice payload, 1-128 bytes. This will not be displayed to the user,
                use it for your internal processes.
            currency: Three-letter ISO 4217 currency code, see more on currencies.
                Pass “XTR” for payments in Telegram Stars.
            prices: Price breakdown, a LabeledPrice list of components (e.g. product price, tax, discount,
                delivery cost, delivery tax, bonus, etc.).
                Must contain exactly one item for payments in Telegram Stars.

            See full parameters here: [createInvoiceLink](https://core.telegram.org/bots/api#createInvoiceLink)
        """
        # Validate currency and provider_token for Stars
        if currency == "XTR":
            if provider_token not in (None, ""):
                raise ValueError(
                    "For payments in Telegram Stars (XTR), provider_token must be an empty string."
                )
            if subscription_period is not None and subscription_period != 2592000:
                raise ValueError(
                    "For Telegram Stars subscriptions, subscription_period must be 2592000 (30 days)."
                )

        payload_data = {
            "business_connection_id": business_connection_id,
            "title": title,
            "description": description,
            "payload": payload,
            "provider_token": provider_token,
            "currency": currency,
            "prices": prices,
            "subscription_period": subscription_period,
            "max_tip_amount": max_tip_amount,
            "suggested_tip_amounts": suggested_tip_amounts,
            "provider_data": provider_data,
            "photo_url": photo_url,
            "photo_size": photo_size,
            "photo_width": photo_width,
            "photo_height": photo_height,
            "need_name": need_name,
            "need_phone_number": need_phone_number,
            "need_email": need_email,
            "need_shipping_address": need_shipping_address,
            "send_phone_number_to_provider": send_phone_number_to_provider,
            "send_email_to_provider": send_email_to_provider,
            "is_flexible": is_flexible,
        }
        response = self._make_request(
            "createInvoiceLink", method="POST", data=payload_data
        )
        return str(response)

    def answer_shipping_query(
        self,
        shipping_query_id: str,
        ok: bool,
        shipping_options: List[ShippingOption] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        Reply to a shipping query.
        If an invoice was sent with `is_flexible=True` and requested a shipping address,
        the Bot API will send an Update with a `shipping_query` field.
        Use this method to respond.

        Args:
            shipping_query_id: Unique identifier for the query to be answered.
            ok: Pass True if delivery to the specified address is possible and False if there are any
                problems (for example, if delivery to the specified address is not possible).
            shipping_options: Required if ok is True. A ShippingOption array of available shipping options.
            error_message: Required if ok is False. Error message in human readable form that
                explains why it is impossible to complete the order
                (e.g. “Sorry, delivery to your desired address is unavailable”).
                Telegram will display this message to the user.
        """
        if ok and not shipping_options:
            raise ValueError("shipping_options are required when ok is True.")

        if not ok and not error_message:
            raise ValueError("error_message is required when ok is False.")

        payload = {
            "shipping_query_id": shipping_query_id,
            "ok": ok,
            "shipping_options": shipping_options,
            "error_message": error_message,
        }
        response = self._make_request(
            "answerShippingQuery", method="POST", data=payload
        )
        return bool(response)

    def answer_pre_checkout_query(
        self, pre_checkout_query_id: str, ok: bool, error_message: str | None = None
    ) -> bool:
        """
        Respond to a pre-checkout query.
        After the user confirms payment and shipping details, the Bot API sends a `pre_checkout_query`.
        You must respond within 10 seconds.

        Args:
            pre_checkout_query_id: Unique identifier for the query to be answered.
            ok: Specify True if everything is alright (goods are available, etc.) and the bot is ready
                to proceed with the order. Use False if there are any problems.
            error_message: Required if ok is False. Error message in human readable form that explains the reason
                for failure to proceed with the checkout (e.g. "Sorry, somebody just bought the last of our
                amazing black T-shirts while you were busy filling out your payment details. Please choose a
                different color or garment!"). Telegram will display this message to the user.
        """
        if not ok and not error_message:
            raise ValueError("error_message is required when ok is False.")

        payload = {
            "pre_checkout_query_id": pre_checkout_query_id,
            "ok": ok,
            "error_message": error_message,
        }
        response = self._make_request(
            "answerPreCheckoutQuery", method="POST", data=payload
        )
        return bool(response)

    def get_my_star_balance(self) -> StarAmount:
        """
        Get the current Telegram Stars balance of the bot.
        """
        response = self._make_request("getMyStarBalance", method="GET")
        return StarAmount.model_validate(response)

    def get_star_transactions(
        self, offset: int | None = None, limit: int | None = None
    ) -> StarTransactions:
        """
        Get the bot's Telegram Star transactions in chronological order.

        Args:
            offset: Number of transactions to skip in the response.
            limit: The maximum number of transactions to be retrieved.
                Values between 1-100 are accepted. Defaults to 100.
        """
        payload = {"offset": offset, "limit": limit}
        response = self._make_request(
            "getStarTransactions", method="GET", params=payload
        )
        return StarTransactions.model_validate(response)

    def refund_star_payment(
        self, user_id: int, telegram_payment_charge_id: str
    ) -> bool:
        """
        Refund a successful payment made in Telegram Stars.

        Args:
            user_id: Identifier of the user whose payment will be refunded.
            telegram_payment_charge_id: Telegram payment identifier.
        """
        payload = {
            "user_id": user_id,
            "telegram_payment_charge_id": telegram_payment_charge_id,
        }
        response = self._make_request("refundStarPayment", method="POST", data=payload)
        return bool(response)

    def edit_user_star_subscription(
        self, user_id: int, telegram_payment_charge_id: str, is_canceled: bool
    ) -> bool:
        """
        Cancel or re-enable the extension of a subscription paid in Telegram Stars.

        Args:
            user_id: Identifier of the user whose subscription will be edited.
            telegram_payment_charge_id: Telegram payment identifier for the subscription.
            is_canceled: Pass True to cancel extension of the user subscription;
                the subscription must be active up to the end of the current subscription period.
                Pass False to allow the user to re-enable a subscription that was previously canceled by the bot.
        """
        payload = {
            "user_id": user_id,
            "telegram_payment_charge_id": telegram_payment_charge_id,
            "is_canceled": is_canceled,
        }
        response = self._make_request(
            "editUserStarSubscription", method="POST", data=payload
        )
        return bool(response)

    def set_passport_data_errors(
        self, user_id: int, errors: List[PassportElementError]
    ) -> bool:
        """
        Inform a user that some of the data they provided in Telegram Passport contains errors.
        The user will not be able to re-submit until the errors are fixed.

        Use this method if the submitted data doesn't meet your service's requirements
        (e.g., invalid date, blurry document, evidence of tampering).

        Args:
            user_id: Unique identifier of the target user.
            errors: A PassportElementError array describing the errors.
        """
        payload = {"user_id": user_id, "errors": errors}
        response = self._make_request(
            "setPassportDataErrors", method="POST", data=payload
        )
        return bool(response)

    def send_game(
        self,
        chat_id: int,
        game_short_name: str,
        business_connection_id: str | None = None,
        message_thread_id: int | None = None,
        disable_notification: bool | None = None,
        protect_content: bool | None = None,
        allow_paid_broadcast: bool | None = None,
        message_effect_id: str | None = None,
        reply_parameters: ReplyParameters | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> Message:
        """
        Send a game to a user.

        Args:
            chat_id: Chat ID or @username of the target chat/bot.
                Games can't be sent to channel direct messages chats and channel chats.
            game_short_name: Short name of the game, serves as the unique identifier for the game.
                Games must be created and configured via @BotFather.

            See full parameters here: [sendGame](https://core.telegram.org/bots/api#sendgame)
        """
        payload = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "message_thread_id": message_thread_id,
            "game_short_name": game_short_name,
            "disable_notification": disable_notification,
            "protect_content": protect_content,
            "allow_paid_broadcast": allow_paid_broadcast,
            "message_effect_id": message_effect_id,
            "reply_parameters": reply_parameters,
            "reply_markup": reply_markup,
        }
        response = self._make_request("sendGame", method="POST", data=payload)
        return Message.model_validate(response)

    def set_game_score(
        self,
        user_id: int,
        score: int,
        force: bool | None = None,
        disable_edit_message: bool | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
    ) -> Message | bool:
        """
        Set the score of a specified user in a game message.

        Args:
            user_id: User identifier.
            score: New score, must be non-negative.
            force: Pass True if the high score is allowed to decrease.
                This can be useful when fixing mistakes or banning cheaters.
            disable_edit_message: Pass True if the game message should not be automatically
                edited to include the current scoreboard
            chat_id: Required if inline_message_id is not specified. Unique identifier for the target chat.
            message_id: Required if inline_message_id is not specified. Identifier of the sent message.
            inline_message_id: Required if chat_id and message_id are not specified. Identifier of the inline message.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "user_id": user_id,
            "score": score,
            "force": force,
            "disable_edit_message": disable_edit_message,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
        }
        response = self._make_request("setGameScore", method="POST", data=payload)
        if isinstance(response, bool):
            return bool(response)

        return Message.model_validate(response)

    def get_game_high_scores(
        self,
        user_id: int,
        chat_id: int | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
    ) -> List[GameHighScore]:
        """
        Get data for high score tables.

        This method returns the score of the specified user and several of their neighbors in the game.
        Currently, it returns the target user's score plus two closest neighbors on each side.
        It also returns the top three users if the user and their neighbors are not among them.
        Note: This behavior is subject to change.

        Args:
            user_id: Target user id.
            chat_id: Required if inline_message_id is not specified. Unique identifier for the target chat.
            message_id: Required if inline_message_id is not specified. Identifier of the sent message.
            inline_message_id: Required if chat_id and message_id are not specified.
                Identifier of the inline message.
        """
        if not (chat_id and message_id) and not inline_message_id:
            raise ValueError(
                "Either (chat_id and message_id) or inline_message_id must be provided."
            )

        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "inline_message_id": inline_message_id,
        }
        response = self._make_request("getGameHighScores", method="GET", params=payload)
        return [GameHighScore.model_validate(game) for game in response]
