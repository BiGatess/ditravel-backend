import argparse
import asyncio
import os
from typing import Optional

from sqlalchemy.future import select

from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal
from app.db.models import User, UserStatus, UserType


def parse_args():
    parser = argparse.ArgumentParser(description="Create or promote a DiTravel admin user.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"), help="Admin email address")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"), help="Password if the user must be created")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "DiTravel Admin"), help="Full name for a new admin")
    parser.add_argument("--phone", default=os.getenv("ADMIN_PHONE"), help="Phone number for a new admin")
    return parser.parse_args()


async def make_admin(email: str, password: Optional[str], name: str, phone: Optional[str]):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            user.user_type = UserType.ADMIN
            user.status = UserStatus.ACTIVE
            await db.commit()
            print(f"Promoted {email} to ADMIN.")
            return

        if not password:
            raise SystemExit("User not found. Provide --password or ADMIN_PASSWORD to create the admin account.")

        user = User(
            email=email,
            full_name=name,
            phone=phone,
            password_hash=get_password_hash(password),
            user_type=UserType.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.commit()
        print(f"Created ADMIN account for {email}.")


if __name__ == "__main__":
    args = parse_args()
    if not args.email:
        raise SystemExit("Provide --email or set ADMIN_EMAIL.")

    asyncio.run(make_admin(args.email, args.password, args.name, args.phone))
