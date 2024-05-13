import asyncio
import json
import logging
import sys
from datetime import datetime, time

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from dateutil.relativedelta import relativedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import ValidationError

from schemas import MessageIn
from settings import settings


class MongoManager:
    def __init__(
        self,
        db_url: str | None = settings.MONGO_DATABASE_URI,
        db_name: str | None = settings.MONGO_NAME,
    ) -> None:
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(db_url)[db_name]

    def __getitem__(self, collection_name: str) -> AsyncIOMotorDatabase:
        return self.client[collection_name]


class PaymentAggregator:
    DATE_FORMAT: dict = {
        "hour": ("%Y-%m-%dT%H:00:00", relativedelta(hours=1)),
        "day": ("%Y-%m-%dT00:00:00", relativedelta(days=1)),
        "week": ("%Y-%m-%dT00:00:00", relativedelta(weeks=1)),
        "month": ("%Y-%m-01T00:00:00", relativedelta(months=1)),
    }

    def __init__(self, collection: AsyncIOMotorDatabase) -> None:
        self.collection = collection

    async def aggregate_payments(
        self, dt_from: datetime, dt_upto: datetime, group_type: str
    ) -> dict[str, list]:
        bounds_end = (
            dt_upto + self.DATE_FORMAT[group_type][1]
            if dt_upto.time() == time(minute=0, second=0)
            else dt_upto
        )

        pipeline = [
            {"$match": {"dt": {"$gte": dt_from, "$lte": dt_upto}}},
            {
                "$densify": {
                    "field": "dt",
                    "range": {
                        "step": 1,
                        "unit": group_type,
                        "bounds": [dt_from, bounds_end],
                    },
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": self.DATE_FORMAT[group_type][0],
                            "date": "$dt",
                        }
                    },
                    "dataset": {"$sum": "$value"},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        result = await self.collection.aggregate(pipeline).to_list(None)

        dataset = [data["dataset"] for data in result]
        labels = [data["_id"] for data in result]

        return {"dataset": dataset, "labels": labels}


class BotHandler:
    def __init__(self) -> None:
        self.bot = Bot(
            token=settings.TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher()

    async def start_polling(self) -> None:
        await self.dp.start_polling(self.bot)

    async def command_start_handler(self, message: Message) -> None:
        await message.answer(f"Hi, {html.bold(message.from_user.full_name)}!")

    async def listen_all_messages(self, message: Message) -> None:
        try:
            data = MessageIn.model_validate_json(message.text)
        except ValidationError as e:
            await message.answer(e.json())
        else:
            result = await PaymentAggregator(
                MongoManager()["your_collection"]
            ).aggregate_payments(**data.model_dump())
            await message.answer(json.dumps(result))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    bot_handler = BotHandler()

    @bot_handler.dp.message(CommandStart())
    async def command_start_handler(message: Message):
        await bot_handler.command_start_handler(message)

    @bot_handler.dp.message()
    async def listen_all_messages(message: Message):
        await bot_handler.listen_all_messages(message)

    asyncio.run(bot_handler.start_polling())
