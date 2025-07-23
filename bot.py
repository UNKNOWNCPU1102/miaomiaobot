import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import time
import random

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 冷却系统
cooldowns = {}
def check_cooldown(user_id: int, command_name: str, cooldown_seconds: int):
    now = time.time()
    key = (user_id, command_name)
    last = cooldowns.get(key, 0)
    if now - last < cooldown_seconds:
        return cooldown_seconds - (now - last)
    cooldowns[key] = now
    return 0

# 颜色身份组配置
COLOR_ROLES = [
    "嘤嘤喵🌸粉",
    "海浪喵🧊蓝", 
    "夜莺喵🌌紫",
    "日落喵🌇橙",
    "森语喵🌲绿",
    "堕落喵🖤黑"
]

# 订阅身份组配置
SUBSCRIPTION_ROLES = [
    "果实",
    "弥赛亚", 
    "YUKI",
    "koko",
    "电影手册",
    "小n",
    "群星",
    "酸砂糖"
]

@bot.event
async def on_ready():
    guild_id = 1384945301780955246
    guild = discord.Object(id=guild_id)
    synced = await bot.tree.sync(guild=guild)
    print(f'✅ Logged in as {bot.user} ({bot.user.id})')
    print(f'✅ 同步命令到服务器 {guild_id}：{[cmd.name for cmd in synced]}')

@bot.event
async def on_member_join(member):
    role_name = "缓冲喵"
    guild = member.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        try:
            await member.add_roles(role, reason="新成员初始缓冲阶段")
            print(f"✅ 已赋予 {role_name} 身份组给 {member.display_name}")
            # 👇 新增提醒消息
            verification_channel_id = 1396360049672065155
            channel = guild.get_channel(verification_channel_id)
            if channel:
                try:
                    await channel.send(
                        f"{member.mention} _(：з」∠)_请使用 `/验证` 完成验证喵～",
                        delete_after=60
                    )
                    print("📩 提醒消息已发送")
                except Exception as e:
                    print(f"⚠️ 无法在验证区发送提醒消息：{e}")
        except Exception as e:
            print(f"❌ 添加身份组失败: {e}")
    else:
        print(f"⚠️ 未找到身份组 '{role_name}'")

# 清理验证区消息（除管理员和bot命令外）
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    VERIFICATION_CHANNEL_ID = 1396360049672065155
    if message.channel.id != VERIFICATION_CHANNEL_ID:
        await bot.process_commands(message)
        return

    if message.author.guild_permissions.manage_guild:
        await bot.process_commands(message)
        return

    try:
        await message.delete()
        print(f"🧹 已删除验证区消息：{message.content}")
    except Exception as e:
        print(f"❌ 删除验证区消息失败：{e}")

@bot.command()
async def ping(ctx):
    user_id = ctx.author.id
    cd = check_cooldown(user_id, "ping", 5)
    if cd > 0:
        await ctx.send(f"诶喵，请等待 {cd:.1f} 秒再使用此命令。", delete_after=5)
        return
    msg = await ctx.send('Pong!')
    await asyncio.sleep(30)
    try:
        await msg.delete()
    except Exception:
        pass

@bot.tree.command(name="首楼跳转", description="回到本帖子的首楼", guild=discord.Object(id=1384945301780955246))
async def 回顶(interaction: discord.Interaction):
    user_id = interaction.user.id
    cd = check_cooldown(user_id, "首楼跳转", 5)
    if cd > 0:
        await interaction.response.send_message(f"诶喵，请等待 {cd:.1f} 秒再用此命令。", ephemeral=True)
        return
    channel = interaction.channel
    if not isinstance(channel, discord.Thread):
        await interaction.response.send_message("该命令只能在帖子中使用。", ephemeral=True)
        return
    try:
        async for msg in channel.history(limit=1, oldest_first=True):
            first_message = msg
        await interaction.response.send_message(f"~o( =∩ω∩= )m请首楼跳转链接：{first_message.jump_url}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"出错了：{e}", ephemeral=True)

# --- 🧠 答题验证系统 ---
QUESTIONS = [
    {
        "question": "1.你是成年人吗？会对自己的言行举止负责吗？",
        "options": ["是，会", "不是，会", "是，不会", "不是，不会"],
        "answer": "是，会"
    },
    {
        "question": "2.是否有认真阅读喵喵守则?",
        "options": ["是的", "还没有"],
        "answer": "是的"
    },
    {
        "question": "3.使用MOM系预设时，第一步需要做什么？",
        "options": ["自动解析", "询问预设作者"],
        "answer": "自动解析"
    },
    {
        "question": "4.MOM系预设修改的自动解析改的标签是？",
        "options": ["<think>", "<thank>", "<thinking>", "不需要自动解析"],
        "answer": "<thinking>"
    },
    {
        "question": "5.遇到言语攻击了怎么办",
        "options": ["公屏骂回去", "艾特喵员", "截图在别的频道挂人"],
        "answer": "艾特喵员"
    }
]

class QuizView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.answers = {}
        self.correct = 0
        self.finished = False
        self.selects = []
        self.generate_questions()

    def generate_questions(self):
        for idx, q in enumerate(QUESTIONS):
            options = q["options"].copy()
            random.shuffle(options)
            select = ui.Select(
                placeholder=q["question"],
                options=[
                    discord.SelectOption(label=opt, value=opt)
                    for opt in options
                ],
                custom_id=f"quiz_q{idx}"
            )

            async def callback(interaction: discord.Interaction, index=idx):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ 你不能操作别人的验证。", ephemeral=True)
                    return
                self.answers[index] = interaction.data["values"][0]
                await interaction.response.defer()
                if len(self.answers) == len(QUESTIONS) and not self.finished:
                    await self.finish(interaction)

            select.callback = callback
            self.selects.append(select)
            self.add_item(select)

    async def finish(self, interaction: discord.Interaction):
        self.finished = True
        for i, q in enumerate(QUESTIONS):
            if self.answers.get(i) == q["answer"]:
                self.correct += 1

        if self.correct == len(QUESTIONS):
            guild = interaction.guild
            member = interaction.user
            new_role = discord.utils.get(guild.roles, name="新喵")
            old_role = discord.utils.get(guild.roles, name="缓冲喵")
            try:
                if new_role:
                    await member.add_roles(new_role, reason="答题验证通过")
                    print(f"✅ {member.display_name} 验证通过，赋予身份组：新喵")
                if old_role:
                    await member.remove_roles(old_role, reason="通过验证移除缓冲")
                    print(f"🔄 已移除身份组：缓冲喵")
                await interaction.followup.send(
                    "(●'◡'●)恭喜你全部答对，身份组 `新喵` 已授予，你已解锁所有频道！欢迎来到喵喵电波共享基地~",
                    ephemeral=True
                )
            except Exception as e:
                print(f"❌ 身份组处理出错：{e}")
                await interaction.followup.send(f"❌ 身份组处理出错：{e}", ephemeral=True)
        else:
            await interaction.followup.send(
                f"诶喵Σ(ŎдŎ|||)ﾉﾉ你只答对了 {self.correct} / {len(QUESTIONS)} 题，请重新阅读守则并再试一次！",
                ephemeral=True
            )

@bot.tree.command(name="验证", description="完成答题以解锁频道", guild=discord.Object(id=1384945301780955246))
async def verify(interaction: discord.Interaction):
    user_id = interaction.user.id
    cd = check_cooldown(user_id, "验证", 300)  # 5分钟冷却
    if cd > 0:
        await interaction.response.send_message(
            f"喵o(´^｀)o你刚刚进行过验证，请 {cd:.0f} 秒后再试一次喵！",
            ephemeral=True
        )
        return

    view = QuizView(user_id)
    await interaction.response.send_message(
        "喵(o｀ε´o)是 **验证问答**：请认真完成以下题目（每题仅有一个正确答案）选完就可以成为新喵了哦^^",
        view=view,
        ephemeral=True
    )

# --- 🌈 颜色身份组选择系统 ---
class ColorRoleView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @ui.select(
        placeholder="选择你喜欢的颜色身份组...",
        options=[
            discord.SelectOption(label=role, value=role, emoji="🌈") 
            for role in COLOR_ROLES
        ]
    )
    async def select_color_role(self, interaction: discord.Interaction, select: ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 你不能操作别人的选择。", ephemeral=True)
            return
            
        guild = interaction.guild
        member = interaction.user
        selected_role_name = select.values[0]
        
        try:
            # 移除所有颜色身份组
            for role_name in COLOR_ROLES:
                role = discord.utils.get(guild.roles, name=role_name)
                if role and role in member.roles:
                    await member.remove_roles(role, reason="切换颜色身份组")
            
            # 添加新选择的身份组
            new_role = discord.utils.get(guild.roles, name=selected_role_name)
            if new_role:
                await member.add_roles(new_role, reason="选择颜色身份组")
                await interaction.response.send_message(
                    f"耶(◦˙▽˙◦)成功获得身份组：`{selected_role_name}` 喵~",
                    ephemeral=True
                )
                print(f"✅ {member.display_name} 获得颜色身份组：{selected_role_name}")
            else:
                await interaction.response.send_message(
                    f"诶喵(ﾟ⊿ﾟ)ﾂ未找到身份组 `{selected_role_name}`，请联系管理员。",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ 操作失败：{e}", ephemeral=True)
            print(f"❌ 颜色身份组操作失败：{e}")

@bot.tree.command(name="颜色", description="选择你的颜色身份组", guild=discord.Object(id=1384945301780955246))
async def select_color(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # 检查是否为缓冲喵
    member = interaction.user
    buffer_role = discord.utils.get(interaction.guild.roles, name="缓冲喵")
    if buffer_role and buffer_role in member.roles:
        await interaction.response.send_message(
            "诶喵Σ( ° △ °|||)︴缓冲喵不能选择颜色身份组，请先完成验证！",
            ephemeral=True
        )
        return
    
    # 检查冷却时间（3小时 = 10800秒）
    cd = check_cooldown(user_id, "颜色", 10800)
    if cd > 0:
        hours = int(cd // 3600)
        minutes = int((cd % 3600) // 60)
        await interaction.response.send_message(
            f"嘻嘻(=^▽^=)颜色身份组更换冷却中，请等待 {hours}小时{minutes}分钟后再试！",
            ephemeral=True
        )
        return

    view = ColorRoleView(user_id)
    await interaction.response.send_message(
        "喵喵੭ ᐕ)੭ **选择颜色身份组**\n请从下方选择你喜欢的颜色身份组（同时只能拥有一个颜色身份组）:",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="清除颜色", description="清除所有颜色身份组", guild=discord.Object(id=1384945301780955246))
async def clear_color(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # 检查冷却时间（3小时 = 10800秒）
    cd = check_cooldown(user_id, "清除颜色", 10800)
    if cd > 0:
        hours = int(cd // 3600)
        minutes = int((cd % 3600) // 60)
        await interaction.response.send_message(
            f"嘻嘻(=^▽^=)清除颜色身份组冷却中，请等待 {hours}小时{minutes}分钟后再试！",
            ephemeral=True
        )
        return

    guild = interaction.guild
    member = interaction.user
    removed_roles = []
    
    try:
        for role_name in COLOR_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles:
                await member.remove_roles(role, reason="清除颜色身份组")
                removed_roles.append(role_name)
        
        if removed_roles:
            await interaction.response.send_message(
                f"主人~已清除颜色身份组：`{'`、`'.join(removed_roles)}` 喵~",
                ephemeral=True
            )
            print(f"✅ {member.display_name} 清除了颜色身份组：{removed_roles}")
        else:
            await interaction.response.send_message(
                "ℹ️ 你没有任何颜色身份组需要清除。",
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(f"❌ 清除失败：{e}", ephemeral=True)
        print(f"❌ 清除颜色身份组失败：{e}")

# --- 🌐订阅身份组系统 ---
class SubscriptionView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @ui.select(
        placeholder="选择你要订阅的身份组...",
        options=[
            discord.SelectOption(label=role, value=role, emoji="🌐") 
            for role in SUBSCRIPTION_ROLES
        ],
        max_values=len(SUBSCRIPTION_ROLES)  # 允许多选
    )
    async def select_subscriptions(self, interaction: discord.Interaction, select: ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 你不能操作别人的选择。", ephemeral=True)
            return
            
        guild = interaction.guild
        member = interaction.user
        selected_roles = select.values
        added_roles = []
        failed_roles = []
        
        try:
            for role_name in selected_roles:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    if role not in member.roles:
                        await member.add_roles(role, reason="订阅身份组")
                        added_roles.append(role_name)
                else:
                    failed_roles.append(role_name)
            
            message_parts = []
            if added_roles:
                message_parts.append(f"耶(=^▽^=)成功订阅：`{'`、`'.join(added_roles)}`")
            if failed_roles:
                message_parts.append(f"诶喵(T＿T)未找到身份组：`{'`、`'.join(failed_roles)}`")
            
            if not message_parts:
                message_parts.append("喵!o(´^｀)o你已经拥有这些订阅身份组了。")
                
            await interaction.response.send_message(
                "\n".join(message_parts) + " 喵~",
                ephemeral=True
            )
            
            if added_roles:
                print(f"✅ {member.display_name} 订阅了身份组：{added_roles}")
                
        except Exception as e:
            await interaction.response.send_message(f"订阅成功哩：{e}", ephemeral=True)
            print(f"❌ 订阅身份组操作失败：{e}")

@bot.tree.command(name="订阅", description="订阅感兴趣的身份组", guild=discord.Object(id=1384945301780955246))
async def subscribe_roles(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # 检查是否为缓冲喵
    member = interaction.user
    buffer_role = discord.utils.get(interaction.guild.roles, name="缓冲喵")
    if buffer_role and buffer_role in member.roles:
        await interaction.response.send_message(
            "诶喵(o｀ε´o)缓冲喵不能订阅身份组，请先完成验证！",
            ephemeral=True
        )
        return
    
    # 检查冷却时间（3小时 = 10800秒）
    cd = check_cooldown(user_id, "订阅", 10800)
    if cd > 0:
        hours = int(cd // 3600)
        minutes = int((cd % 3600) // 60)
        await interaction.response.send_message(
            f"(つД`)订阅功能冷却中，请等待 {hours}小时{minutes}分钟后再试！",
            ephemeral=True
        )
        return

    view = SubscriptionView(user_id)
    await interaction.response.send_message(
        "喵~(*σ´∀`)σ **订阅身份组**\n请选择你想订阅的身份组（可多选，只会添加你还没有的身份组）:",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="清除订阅", description="清除所有订阅身份组", guild=discord.Object(id=1384945301780955246))
async def clear_subscriptions(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # 检查冷却时间（3小时 = 10800秒）
    cd = check_cooldown(user_id, "清除订阅", 10800)
    if cd > 0:
        hours = int(cd // 3600)
        minutes = int((cd % 3600) // 60)
        await interaction.response.send_message(
            f"诶喵 (*^▽^*) 清除订阅功能冷却中，请等待 {hours}小时{minutes}分钟后再试！",
            ephemeral=True
        )
        return

    guild = interaction.guild
    member = interaction.user
    removed_roles = []
    
    try:
        for role_name in SUBSCRIPTION_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles:
                await member.remove_roles(role, reason="清除订阅身份组")
                removed_roles.append(role_name)
        
        if removed_roles:
            await interaction.response.send_message(
                f"耶喵(*^ω^*)已清除订阅身份组：`{'`、`'.join(removed_roles)}` 喵~",
                ephemeral=True
            )
            print(f"✅ {member.display_name} 清除了订阅身份组：{removed_roles}")
        else:
            await interaction.response.send_message(
                "诶 (-^〇^-) 你没有任何订阅身份组需要清除。",
                ephemeral=True
            )
    except Exception as e:
        await interaction.response.send_message(f"❌ 清除失败：{e}", ephemeral=True)
        print(f"❌ 清除订阅身份组失败：{e}")

# 启动 bot（⚠️ 请尽快替换 token）
bot.run('MTM5NjEwMjI0OTMxNDM4NjAwMA.GwAG7-.kq8x7xZojpRk19pYBUHOzEOh6DkISMddWOuXoc')

