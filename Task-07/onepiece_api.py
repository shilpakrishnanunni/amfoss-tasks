import random
import aiohttp


# BASE_URL = "https://api.api-onepiece.com/v2"
BASE_URL = "https://onepieceapi.com/api"


class OnePieceAPI:
    async def get_character(self):
        url = f"{BASE_URL}/characters"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:

                    if response.status != 200:
                        return None

                    data = await response.json()

                    if isinstance(data, list) and data:
                        return random.choice(data)

                    return data

        except (aiohttp.ClientError, TimeoutError):
            return None

    async def get_devil_fruit(self):
        url = f"{BASE_URL}/devil-fruits"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:

                    if response.status != 200:
                        return None

                    data = await response.json()

                    if isinstance(data, list) and data:
                        return random.choice(data)

                    return data

        except (aiohttp.ClientError, TimeoutError):
            return None

    @staticmethod
    def localized_name(value):
        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            return (
                value.get("en")
                or value.get("romaji")
                or value.get("jp")
                or "Unknown"
            )

        return "Unknown"

    async def log_pose(self):
        try:
            # 50/50 chance of getting character or Devil Fruit intel.
            if random.choice([True, False]):
                character = await self.get_character()

                if not character:
                    return None

                name = self.localized_name(character.get("name"))
                bounty = character.get("bounty")

                return {
                    "type": "character",
                    "name": name,
                    "bounty": bounty,
                }

            fruit = await self.get_devil_fruit()

            if not fruit:
                return None

            return {
                "type": "fruit",
                "name": self.localized_name(fruit.get("name")),
                "model": self.localized_name(fruit.get("model")),
                "fruit_type": fruit.get("type", "Unknown"),
            }
        except Exception as e:
            print(e)
            return None
