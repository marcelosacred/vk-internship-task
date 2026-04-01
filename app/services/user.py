from datetime import datetime, timedelta, timezone

from passlib.hash import bcrypt
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.user import UserCreate


def utc_now() -> datetime:
	"""вернуть текущее время в UTC для удобства тестирования"""

	return datetime.now(timezone.utc).replace(tzinfo=None)


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
	"""создать нового юзера с данными из user_data и вернуть его"""

	user = User(
		login=user_data.login,
		password=bcrypt.hash(user_data.password),
		project_id=user_data.project_id,
		env=user_data.env.value,
		domain=user_data.domain.value,
	)
	db.add(user)

	try:
		await db.commit()
	except IntegrityError as exc:
		await db.rollback()
		raise ValueError("login already exists") from exc

	await db.refresh(user)
	return user


async def get_users(db: AsyncSession) -> list[User]:
	"""вернуть всех юзеров, отсортированных по created_at в порядке возрастания"""

	result = await db.execute(select(User).order_by(User.created_at.asc()))
	return list(result.scalars().all())


async def lock_user(db: AsyncSession) -> User:
	"""заблокировать одного свободного юзера,
	   установив locktime в текущее время + TTL, и вернуть его
	"""

	now = utc_now()
	lock_until = now + timedelta(seconds=settings.user_lock_ttl_seconds)

	candidate_id_query = (
		select(User.id)
		.where(or_(User.locktime.is_(None), User.locktime <= now))
		.order_by(User.created_at.asc())
		.limit(1)
	)

	if db.bind is not None and db.bind.dialect.name == "postgresql":
		candidate_id_query = candidate_id_query.with_for_update(skip_locked=True)

	lock_stmt = (
		update(User)
		.where(User.id == candidate_id_query.scalar_subquery())
		.values(locktime=lock_until)
		.returning(User.id)
	)
	result = await db.execute(lock_stmt)
	locked_user_id = result.scalar_one_or_none()

	if locked_user_id is None:
		await db.rollback()
		raise LookupError("no available users")

	await db.commit()
	locked_user = await db.get(User, locked_user_id)

	if locked_user is None:
		raise LookupError("no available users")

	return locked_user


async def free_users(db: AsyncSession) -> int:
	"""очистить locktime у всех юзеров,
	   у которых он установлен,
	   и вернуть количество разблокированных юзеров
	"""

	result = await db.execute(update(User).values(locktime=None))
	await db.commit()
	return result.rowcount or 0
