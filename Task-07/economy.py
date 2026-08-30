from datetime import datetime, timezone, timedelta
import random

from config import (
    DAILY_COOLDOWN,
    RAID_COOLDOWN,
    RAID_SUCCESS_CHANCE,
    RAID_MIN_PERCENT,
    RAID_MAX_PERCENT,
    RAID_MIN_REMAINING,
)


def parse_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def cooldown_remaining(last_used, cooldown_seconds):
    if not last_used:
        return 0

    previous = parse_time(last_used)

    if not previous:
        return 0

    now = datetime.now(timezone.utc)
    elapsed = (now - previous).total_seconds()

    return max(0, int(cooldown_seconds - elapsed))


def daily_remaining(last_daily):
    return cooldown_remaining(last_daily, DAILY_COOLDOWN)


def raid_remaining(last_raid):
    return cooldown_remaining(last_raid, RAID_COOLDOWN)


def daily_reward(base_reward, lucky_bonus=0):
    reward = base_reward

    # Lucky Coin gives a 25% chance of a 2x payout.
    if lucky_bonus > 0 and random.random() < lucky_bonus / 100:
        reward *= 2

    return reward


def raid_attempt(raid_bonus=0):
    chance = RAID_SUCCESS_CHANCE + (raid_bonus / 100)

    chance = min(chance, 0.80)

    return random.random() < chance


def raid_amount(defender_balance):
    if defender_balance <= RAID_MIN_REMAINING:
        return 0

    maximum_loss = defender_balance - RAID_MIN_REMAINING

    percentage = random.uniform(
        RAID_MIN_PERCENT,
        RAID_MAX_PERCENT
    )

    return min(
        maximum_loss,
        max(1, int(defender_balance * percentage))
    )


def reduce_raid_loss(amount, shield_bonus):
    if shield_bonus <= 0:
        return amount

    reduction = min(shield_bonus, 50)

    return max(
        1,
        int(amount * (1 - reduction / 100))
    )