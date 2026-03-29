import os
import time
import discord
from discord import app_commands
import requests
from concurrent.futures import ThreadPoolExecutor

TOKEN = os.environ["DISCORD_TOKEN"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

CURRENCY = 10  # 10 = IDR (Rupiah)

CONDITIONS = [
    "Factory New",
    "Minimal Wear",
    "Field-Tested",
    "Well-Worn",
    "Battle-Scarred",
]

CS2_CASES = [
    "CS:GO Weapon Case",
    "CS:GO Weapon Case 2",
    "CS:GO Weapon Case 3",
    "Operation Bravo Case",
    "Operation Phoenix Weapon Case",
    "Operation Breakout Weapon Case",
    "Operation Vanguard Weapon Case",
    "Chroma Case",
    "Chroma 2 Case",
    "Chroma 3 Case",
    "Falchion Case",
    "Shadow Case",
    "Revolver Case",
    "Operation Wildfire Case",
    "Spectrum Case",
    "Spectrum 2 Case",
    "Operation Hydra Case",
    "Clutch Case",
    "Horizon Case",
    "Danger Zone Case",
    "Prisma Case",
    "Prisma 2 Case",
    "CS20 Case",
    "Shattered Web Case",
    "Fracture Case",
    "Operation Broken Fang Case",
    "Snakebite Case",
    "Operation Riptide Case",
    "Dreams & Nightmares Case",
    "Recoil Case",
    "Revolution Case",
    "Kilowatt Case",
    "Gallery Case",
]


HELP_TEXT = """**📖 Cara Penggunaan Bot CS2 Price**

**/csprice <nama skin>**
Cek harga skin CS2 semua kondisi (Normal & StatTrak™)
Contoh: `/csprice ak47 redline`

**/cscase [nama case]**
Cek harga Case CS2 (last sold price dalam Rupiah)
• Tanpa parameter → tampil semua case
• Dengan parameter → cari case spesifik
Contoh: `/cscase revolution` atau `/cscase chroma`

**/cs**
Ping role CS2 untuk ngajak main bareng

━━━━━━━━━━━━━━━━━━━━━━
*Bot dibuat sama orang ganteng Toyolicious* 😎"""


class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print("CS2 Price Bot Ready")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        # Respond when bot is mentioned
        if self.user.mentioned_in(message):
            await message.reply(HELP_TEXT)


client = MyClient()


def fetch_price(market_hash_name: str, delay: float = 0.0) -> dict:
    """Fetch price data for a single item from Steam Market."""
    if delay:
        time.sleep(delay)
    try:
        r = requests.get(
            "https://steamcommunity.com/market/priceoverview/",
            params={
                "appid": 730,
                "currency": CURRENCY,
                "market_hash_name": market_hash_name,
            },
            headers=HEADERS,
            timeout=10,
        )
        data = r.json()
        if data.get("success"):
            return {
                "name": market_hash_name,
                "last_sold": data.get("median_price", "N/A"),
                "lowest": data.get("lowest_price", "N/A"),
                "volume": data.get("volume", "N/A"),
            }
    except Exception:
        pass
    return {
        "name": market_hash_name,
        "last_sold": "N/A",
        "lowest": "N/A",
        "volume": "N/A",
    }


def search_base_name(query: str) -> str | None:
    """Search Steam Market and return base item name (without condition)."""
    try:
        # Remove pipe character — Steam search doesn't handle it well
        clean_query = query.replace("|", " ").strip()
        r = requests.get(
            "https://steamcommunity.com/market/search/render/",
            params={
                "query": clean_query,
                "appid": 730,
                "search_descriptions": 0,
                "count": 10,
                "norender": 1,
            },
            headers=HEADERS,
            timeout=10,
        )
        results = r.json().get("results", [])
        if not results:
            return None
        name = results[0].get("name", "")
        for cond in CONDITIONS:
            name = name.replace(f" ({cond})", "")
        return name.strip()
    except Exception:
        return None


# ─── Command: /csprice ────────────────────────────────────────────────────────


@client.tree.command(name="csprice", description="Cek harga skin CS2 semua kondisi")
@app_commands.describe(
    item="Nama skin, contoh: ak47 redline"
)
async def csprice(interaction: discord.Interaction, item: str):
    await interaction.response.defer()

    # Redirect if user is searching for a case
    if "case" in item.lower():
        await interaction.followup.send(
            "📦 Untuk mencari harga case, gunakan **/cscase** ya!"
        )
        return

    base_name = search_base_name(item)
    if not base_name:
        await interaction.followup.send(
            f"❌ Item **{item}** tidak ditemukan di Steam Market."
        )
        return

    # Build list of all items to fetch (normal + stattrak, all conditions)
    items_to_fetch = []
    for cond in CONDITIONS:
        items_to_fetch.append(f"{base_name} ({cond})")
    for cond in CONDITIONS:
        items_to_fetch.append(f"StatTrak™ {base_name} ({cond})")

    # Fetch in parallel with staggered delays to avoid rate limiting
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(
            executor.map(
                lambda args: fetch_price(args[1], delay=args[0] * 0.3),
                enumerate(items_to_fetch),
            )
        )

    price_map = {r["name"]: r for r in results}

    # If all prices are N/A, item not found or misspelled
    all_prices = [price_map[k]["last_sold"] for k in price_map]
    if all(p in ("N/A", "Error") for p in all_prices):
        await interaction.followup.send(
            f"❌ Data tidak ditemukan atau kamu salah dalam pengejaaan nama skinnya.\n"
            f"Coba cek ejaan dan format nama skin, contoh: `ak47 redline`"
        )
        return

    # Build embed
    steam_url = (
        "https://steamcommunity.com/market/search?appid=730&q="
        + requests.utils.quote(base_name)
    )
    embed = discord.Embed(
        title=f"💰 {base_name}",
        url=steam_url,
        color=discord.Color.orange(),
    )

    # Normal
    normal_lines = []
    for cond in CONDITIONS:
        key = f"{base_name} ({cond})"
        price = price_map[key]["last_sold"]
        normal_lines.append(f"`{cond:<18}` {price}")
    embed.add_field(name="🔹 Normal", value="\n".join(normal_lines), inline=False)

    # StatTrak
    st_lines = []
    for cond in CONDITIONS:
        key = f"StatTrak™ {base_name} ({cond})"
        price = price_map[key]["last_sold"]
        st_lines.append(f"`{'ST™ ' + cond:<18}` {price}")
    embed.add_field(name="🟡 StatTrak™", value="\n".join(st_lines), inline=False)

    embed.set_footer(
        text="Harga = last sold • Steam Community Market • IDR (Rupiah) \n Jika tidak ada harga coba ulangi lagi"
    )
    await interaction.followup.send(embed=embed)


# ─── Command: /cscase ─────────────────────────────────────────────────────────


@client.tree.command(name="cscase", description="Cek harga Case CS2 (last sold)")
@app_commands.describe(
    nama="Nama case, contoh: revolution | kilowatt | chroma. Kosongkan untuk semua case."
)
async def cscase(interaction: discord.Interaction, nama: str = ""):
    await interaction.response.defer()

    # ── Single case search ──────────────────────────────────────────────────
    if nama.strip():
        keyword = nama.strip().lower()
        matched = [c for c in CS2_CASES if keyword in c.lower()]

        if not matched:
            case_list = "\n".join(f"• {c}" for c in CS2_CASES)
            await interaction.followup.send(
                f"❌ Case **{nama}** tidak ditemukan.\n\nCase yang tersedia:\n{case_list}"
            )
            return

        if len(matched) == 1:
            # Exact single match — show detailed embed
            case_name = matched[0]
            data = fetch_price(case_name)
            steam_url = (
                "https://steamcommunity.com/market/listings/730/"
                + requests.utils.quote(case_name)
            )
            embed = discord.Embed(
                title=f"📦 {case_name}",
                url=steam_url,
                color=discord.Color.blue(),
            )
            embed.add_field(name="💵 Last Sold", value=data["last_sold"], inline=True)
            embed.add_field(name="📉 Lowest", value=data["lowest"], inline=True)
            embed.add_field(name="📊 Volume", value=data["volume"], inline=True)
            embed.set_footer(text="Steam Community Market • IDR (Rupiah)")
            await interaction.followup.send(embed=embed)
        else:
            # Multiple matches — show list
            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(
                    executor.map(
                        lambda args: fetch_price(args[1], delay=args[0] * 0.2),
                        enumerate(matched),
                    )
                )
            lines = [f"`{r['name']:<35}` {r['last_sold']}" for r in results]
            embed = discord.Embed(
                title=f"📦 Case CS2 — hasil '{nama}'",
                color=discord.Color.blue(),
                description="\n".join(lines),
            )
            embed.set_footer(
                text="Harga = last sold • Steam Community Market • IDR (Rupiah)"
            )
            await interaction.followup.send(embed=embed)
        return

    # ── All cases ───────────────────────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(
            executor.map(
                lambda args: fetch_price(args[1], delay=args[0] * 0.2),
                enumerate(CS2_CASES),
            )
        )

    mid = len(results) // 2
    first_half = results[:mid]
    second_half = results[mid:]

    def format_case(r: dict) -> str:
        name = r["name"].replace(" Weapon", "")
        price = r["last_sold"]
        return f"`{name:<33}` {price}"

    embed = discord.Embed(
        title="📦 Semua Harga Case CS2 — Last Sold",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="Case (1/2)",
        value="\n".join(format_case(r) for r in first_half),
        inline=False,
    )
    embed.add_field(
        name="Case (2/2)",
        value="\n".join(format_case(r) for r in second_half),
        inline=False,
    )
    embed.set_footer(text="Harga = last sold • Steam Community Market • IDR (Rupiah)")
    await interaction.followup.send(embed=embed)


# ─── Command: /cs ─────────────────────────────────────────────────────────────


@client.tree.command(name="cs", description="Ping role CS2")
async def cs(interaction: discord.Interaction):
    role_id = 1208307952935505940
    allowed_mentions = discord.AllowedMentions(roles=True)
    await interaction.response.send_message(
        f"<@&{role_id}> buruan login bangsat",
        allowed_mentions=allowed_mentions
    )


# ─── Run ──────────────────────────────────────────────────────────────────────

client.run(TOKEN)
