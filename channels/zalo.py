
import logging
from sanic import Sanic, Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse
from typing import Text, Dict, Any, Optional, Callable, Awaitable
from rasa.core.channels.channel import (
    InputChannel,
    UserMessage,
    OutputChannel
)

#from functions.middleware import Authenticate

from packages.zalo.oa import ZaloOaClient

logger = logging.getLogger(__name__)

class ZaloInput(InputChannel):

    @classmethod
    def name(cls) -> Text:
        return 'zalo'

    def is_allow_event(self, event_name: str):
        account = event_name.split('_')[0]
        return account == 'user'
         
    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> InputChannel:
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(
            credentials.get("zalo_access_token"),
        )

    def __init__(self, zalo_access_token: Text) -> None:
        self.zalo_access_token = zalo_access_token

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[None]]
    ) -> Blueprint:
        zalo_webhook = Blueprint(
            "zalo_webhook", __name__
        )

        # noinspection PyUnusedLocal
        @zalo_webhook.route("/", methods=["GET"])
        async def health(request: Request) -> HTTPResponse:
            return response.json({"zalo status test": "ok"})

        @zalo_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request) -> HTTPResponse:
            metadata = self.get_metadata(request)
            payload = request.json
            print("request json", payload)

            if payload.get("event_name") is None:
                return response.json({"ok": "success"})

            isAllow = self.is_allow_event(payload.get('event_name'))
            print("isAllow", isAllow)

            if isAllow:
                # khởi tạo đối tượng Messender
                messenger = Messenger(self.zalo_access_token, on_new_message)
                await messenger.handle(payload, metadata)

            return response.json({"ok": "success"})
        return zalo_webhook

class Messenger:
    """Implement a zalomessenger to parse incoming webhooks and send msgs."""
    @classmethod
    def name(cls) -> Text:
        return "zalo"

    def __init__(
        self,
        access_token: Text,
        on_new_message: Callable[[UserMessage], Awaitable[Any]],
    ) -> None:

        self.on_new_message = on_new_message
        self.client = ZaloOaClient(access_token, {})
        self.last_message: Dict[Text, Any] = {}

    @staticmethod
    def _is_text_message(message: Dict[Text, Any]) -> bool:
        """Check if the message is a message from the user"""
        return (
            "text" in message
            and not "not_allow" in message
        )

    def get_user_id(self) -> Text:
        return self.last_message.get("sender", "")['id']

    def get_event_name(self) -> Text:
        return self.last_message.get("event_name", {})

    async def handle(self, payload: Dict, metadata: Optional[Dict[Text, Any]]) -> None:
        self.last_message = payload

        # lấy thông nội dung message
        message = payload.get('message')

        return await self.message(message, metadata)

    async def message(
        self, message: Dict[Text, Any], metadata: Optional[Dict[Text, Any]]
    ) -> None:
        """Handle an incoming event from the zalo webhook."""

        if self._is_text_message(message):
            text = message["text"]
        else:
            logger.warning(
                "Received a message from zalo that we can not "
                f"handle. Message: {message}"
            )
            return

        # xử lý tin nhắn
        await self._handle_user_message(text, self.get_user_id(), metadata)

    async def _handle_user_message(
        self, text: Text, sender_id: Text, metadata: Optional[Dict[Text, Any]]
    ) -> None:
        """Pass on the text to the dialogue engine for processing."""

        # khởi tạo out channel
        out_channel = MessengerBot(self.client, self.get_event_name())

        # khởi tạo UserMesssage để pass dữ liệu vào rasa core và rasa nlu phân tích và trả về Out channel
        user_msg = UserMessage(
            text, out_channel, sender_id, input_channel=self.name(), metadata=metadata
        )
        try:
            # Xử lý tiếp
            await self.on_new_message(user_msg)
        except Exception:
            logger.exception(
                "Exception when trying to handle webhook for zalo message."
            )
            pass

class MessengerBot(OutputChannel):
    """A bot that uses zalo-messenger to communicate."""

    @classmethod
    def name(cls) -> Text:
        return "zalo"

    def __init__(self, messenger_client: ZaloOaClient, event_name) -> None:
        self.messenger_client = messenger_client
        self.event_name = event_name
        super().__init__()

    # fucntion trả lại kết quả phân tích từ rasa core và rasa nlu
    def send(self, recipient_id: Text, element: Any) -> None:

        """Sends a message to the recipient using the zalo client."""
        text = {
            "text": element
        }

        self.messenger_client.send(text, recipient_id, self.event_name)

    # function gửi văn bản với mẫu riêng biệt
    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        """Send a message through this channel."""

        for message_part in text.strip().split("\n\n"):
            self.send(recipient_id, message_part)

    async def send_custom_json(
        self, recipient_id: Text, json_message: Dict[Text, Any], **kwargs: Any
    ) -> None:
        """Sends custom json data to the output."""

        recipient_id = json_message.pop("sender", {}).pop("id", None) or recipient_id

        self.messenger_client.send(json_message, recipient_id, "RESPONSE")




