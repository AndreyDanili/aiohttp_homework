import json
from aiohttp import web
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.exc import IntegrityError

app = web.Application()


PG_DSN = "postgresql+asyncpg://admin:admin1pwd@postgresdb:5432/advertisement"
engine = create_async_engine(PG_DSN, echo=True)
Base = declarative_base()


class HTTPError(web.HTTPException):
    def __init__(self, *, headers=None, reason=None, body=None, message=None):
        json_response = json.dumps({"error": message})
        super().__init__(
            headers=headers,
            reason=reason,
            body=body,
            text=json_response,
            content_type="application/json",
        )


class BadRequest(HTTPError):
    status_code = 400


class NotFound(HTTPError):
    status_code = 400


class Advertisement(Base):

    __tablename__ = 'advertisement'
    id = Column(Integer, primary_key=True)
    header = Column(String, index=True, unique=True, nullable=False)
    description = Column(String, nullable=False)
    author = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


async def get_advertisement(advertisement_id: int, session) -> Advertisement:
    advertisement = await session.get(Advertisement, advertisement_id)
    if not advertisement:
        raise NotFound(message="Advertisement not found")
    return advertisement


class AdvertisementView(web.View):
    async def get(self):
        advertisement_id = int(self.request.match_info["id"])
        async with app.async_session_maker() as session:
            advertisement = await get_advertisement(advertisement_id, session)
            return web.json_response(
                {
                    "header": advertisement.header,
                    "created_at": advertisement.created_at.isoformat(),
                }
            )

    async def post(self):
        advertisement_data = await self.request.json()
        new_advertisement = Advertisement(**advertisement_data)
        async with app.async_session_maker() as session:

            try:
                session.add(new_advertisement)
                await session.commit()
                return web.json_response({"id": new_advertisement.id})
            except IntegrityError as er:
                raise BadRequest(message="Advertisement already exists")

    async def patch(self):
        advertisement_id = int(self.request.match_info["id"])
        advertisement_data = await self.request.json()
        async with app.async_session_maker() as session:
            advertisement = await get_advertisement(advertisement_id, session)
            for column, value in advertisement_data.items():
                setattr(advertisement, column, value)
            session.add(advertisement)
            await session.commit()
            return web.json_response({"status": "success"})

    async def delete(self):
        advertisement_id = int(self.request.match_info["id"])
        async with app.async_session_maker() as session:
            advertisement = await get_advertisement(advertisement_id, session)
            await session.delete(advertisement)
            await session.commit()
            return web.json_response({"status": "success"})


async def init_orm(app: web.Application):
    print("Приложение стартовало")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        async_session_maker = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        app.async_session_maker = async_session_maker
        yield
    print("Приложение завершило работу")


app.cleanup_ctx.append(init_orm)
app.add_routes([web.get("/advertisement/{id:\d+}", AdvertisementView)])
app.add_routes([web.patch("/advertisement/{id:\d+}", AdvertisementView)])
app.add_routes([web.delete("/advertisement/{id:\d+}", AdvertisementView)])
app.add_routes([web.post("/advertisement/", AdvertisementView)])
web.run_app(app)
