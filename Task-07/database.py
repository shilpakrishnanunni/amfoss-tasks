import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from config import DATABASE_PATH, STARTING_BERRIES


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path=DATABASE_PATH):
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            path,
            check_same_thread=False
        )

        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")

        self.create_tables()
        self.seed_shop()

    def create_tables(self):
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                balance INTEGER NOT NULL DEFAULT 1000,
                last_daily TEXT,
                last_raid TEXT,
                created_at TEXT NOT NULL,

                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                cost INTEGER NOT NULL,
                effect_type TEXT NOT NULL,
                effect_value INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                purchased_at TEXT NOT NULL,

                FOREIGN KEY (item_id)
                    REFERENCES shop_items(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                target_user_id INTEGER,
                description TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        self.connection.commit()

    def seed_shop(self):
        items = [
            (
                "log_pose",
                "A mysterious Log Pose. Slightly improves your raid success chance.",
                2500,
                "raid_bonus",
                5,
            ),
            (
                "seastone",
                "Seastone cuffs. Reduces the amount lost when a raid against you succeeds.",
                3000,
                "raid_shield",
                10,
            ),
            (
                "lucky_coin",
                "A suspiciously shiny coin. Gives you a small chance of doubling !setsail.",
                4000,
                "daily_bonus",
                25,
            ),
            (
                "den_den_mushi",
                "A Den Den Mushi that whispers market rumours.",
                1500,
                "bounty_bonus",
                100,
            ),
        ]

        self.connection.executemany(
            """
            INSERT OR IGNORE INTO shop_items
                (name, description, cost, effect_type, effect_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            items
        )

        self.connection.commit()

    # -------------------------
    # User management
    # -------------------------

    def ensure_user(self, guild_id, user_id):
        self.connection.execute(
            """
            INSERT OR IGNORE INTO users
                (guild_id, user_id, balance, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                STARTING_BERRIES,
                utc_now(),
            )
        )

        self.connection.commit()

    def get_user(self, guild_id, user_id):
        self.ensure_user(guild_id, user_id)

        return self.connection.execute(
            """
            SELECT *
            FROM users
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (guild_id, user_id)
        ).fetchone()

    def change_balance(self, guild_id, user_id, amount):
        self.ensure_user(guild_id, user_id)

        self.connection.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE guild_id = ?
              AND user_id = ?
            """,
            (amount, guild_id, user_id)
        )

        self.connection.commit()

    def transfer(self, guild_id, sender_id, receiver_id, amount):
        self.ensure_user(guild_id, sender_id)
        self.ensure_user(guild_id, receiver_id)

        try:
            with self.connection:
                sender = self.connection.execute(
                    """
                    SELECT balance
                    FROM users
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (guild_id, sender_id)
                ).fetchone()

                if sender["balance"] < amount:
                    return False

                self.connection.execute(
                    """
                    UPDATE users
                    SET balance = balance - ?
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (amount, guild_id, sender_id)
                )

                self.connection.execute(
                    """
                    UPDATE users
                    SET balance = balance + ?
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (amount, guild_id, receiver_id)
                )

                self.log_transaction(
                    guild_id,
                    sender_id,
                    "trade_sent",
                    -amount,
                    receiver_id,
                    f"Sent {amount} Berries"
                )

                self.log_transaction(
                    guild_id,
                    receiver_id,
                    "trade_received",
                    amount,
                    sender_id,
                    f"Received {amount} Berries"
                )

                return True

        except sqlite3.Error:
            return False

    # -------------------------
    # Daily
    # -------------------------

    def set_last_daily(self, guild_id, user_id):
        self.connection.execute(
            """
            UPDATE users
            SET last_daily = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (utc_now(), guild_id, user_id)
        )

        self.connection.commit()

    # -------------------------
    # Raids
    # -------------------------

    def set_last_raid(self, guild_id, user_id):
        self.connection.execute(
            """
            UPDATE users
            SET last_raid = ?
            WHERE guild_id = ? AND user_id = ?
            """,
            (utc_now(), guild_id, user_id)
        )

        self.connection.commit()

    def raid_transfer(
        self,
        guild_id,
        attacker_id,
        defender_id,
        amount,
    ):
        self.ensure_user(guild_id, attacker_id)
        self.ensure_user(guild_id, defender_id)

        with self.connection:
            defender = self.connection.execute(
                """
                SELECT balance
                FROM users
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, defender_id)
            ).fetchone()

            actual_amount = min(amount, max(0, defender["balance"]))

            if actual_amount <= 0:
                return 0

            self.connection.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (actual_amount, guild_id, defender_id)
            )

            self.connection.execute(
                """
                UPDATE users
                SET balance = balance + ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (actual_amount, guild_id, attacker_id)
            )

            self.log_transaction(
                guild_id,
                attacker_id,
                "raid_gain",
                actual_amount,
                defender_id,
                f"Raided {actual_amount} Berries"
            )

            self.log_transaction(
                guild_id,
                defender_id,
                "raid_loss",
                -actual_amount,
                attacker_id,
                f"Lost {actual_amount} Berries in a raid"
            )

            return actual_amount

    # -------------------------
    # Shop
    # -------------------------

    def get_shop_items(self):
        return self.connection.execute(
            """
            SELECT *
            FROM shop_items
            ORDER BY cost ASC
            """
        ).fetchall()

    def get_shop_item(self, name):
        return self.connection.execute(
            """
            SELECT *
            FROM shop_items
            WHERE LOWER(name) = LOWER(?)
            """,
            (name,)
        ).fetchone()

    def buy_item(self, guild_id, user_id, item_id, cost):
        self.ensure_user(guild_id, user_id)

        with self.connection:
            user = self.connection.execute(
                """
                SELECT balance
                FROM users
                WHERE guild_id = ? AND user_id = ?
                """,
                (guild_id, user_id)
            ).fetchone()

            if user["balance"] < cost:
                return False

            self.connection.execute(
                """
                UPDATE users
                SET balance = balance - ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (cost, guild_id, user_id)
            )

            self.connection.execute(
                """
                INSERT INTO inventory
                    (guild_id, user_id, item_id, status, purchased_at)
                VALUES (?, ?, ?, 'active', ?)
                """,
                (
                    guild_id,
                    user_id,
                    item_id,
                    utc_now(),
                )
            )

            self.log_transaction(
                guild_id,
                user_id,
                "shop_purchase",
                -cost,
                None,
                f"Purchased item #{item_id}"
            )

            return True

    def get_inventory(self, guild_id, user_id):
        return self.connection.execute(
            """
            SELECT
                inventory.id,
                inventory.status,
                inventory.purchased_at,
                shop_items.name,
                shop_items.description,
                shop_items.effect_type,
                shop_items.effect_value
            FROM inventory
            JOIN shop_items
                ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id = ?
              AND inventory.user_id = ?
            ORDER BY inventory.purchased_at DESC
            """,
            (guild_id, user_id)
        ).fetchall()

    def get_active_effect(self, guild_id, user_id, effect_type):
        row = self.connection.execute(
            """
            SELECT
                COALESCE(SUM(shop_items.effect_value), 0) AS total
            FROM inventory
            JOIN shop_items
                ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id = ?
              AND inventory.user_id = ?
              AND inventory.status = 'active'
              AND shop_items.effect_type = ?
            """,
            (guild_id, user_id, effect_type)
        ).fetchone()

        return row["total"]

    # -------------------------
    # Leaderboard
    # -------------------------

    def leaderboard(self, guild_id, limit=5):
        return self.connection.execute(
            """
            SELECT user_id, balance
            FROM users
            WHERE guild_id = ?
            ORDER BY balance DESC
            LIMIT ?
            """,
            (guild_id, limit)
        ).fetchall()

    # -------------------------
    # History
    # -------------------------

    def log_transaction(
        self,
        guild_id,
        user_id,
        transaction_type,
        amount,
        target_user_id=None,
        description=None,
    ):
        self.connection.execute(
            """
            INSERT INTO transactions
                (
                    guild_id,
                    user_id,
                    transaction_type,
                    amount,
                    target_user_id,
                    description,
                    created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                guild_id,
                user_id,
                transaction_type,
                amount,
                target_user_id,
                description,
                utc_now(),
            )
        )

    def get_history(self, guild_id, user_id, limit=10):
        return self.connection.execute(
            """
            SELECT *
            FROM transactions
            WHERE guild_id = ?
              AND user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (guild_id, user_id, limit)
        ).fetchall()