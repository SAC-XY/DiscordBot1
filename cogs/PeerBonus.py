import random
import os

from discord.ext import commands
import googleapiclient.discovery
from google.oauth2 import service_account

from db.session import session
from db.message import Message

class PeerBonusError(Exception):
    """PeerBonusモデルが投げる例外の基底クラス"""
    pass

class メンバーが見つからない(PeerBonusError):
    pass


class PeerBonus(commands.Cog):
    spreadsheet_id: str

    def __init__(self, bot):
        self.bot = bot
        self.spreadsheet_id = '1HK96UyIEEiX3Q67yMzpA-bc5eLi0jHm3pgJSTXFnqkY'

    @staticmethod
    def get_credentials():
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        credentials = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
        return credentials

    def get_spreadsheet_service(self):
        credentials = self.get_credentials()
        service = googleapiclient.discovery.build('sheets', 'v4',
                                                  credentials=credentials,
                                                  cache_discovery=False)
        return service

    def スプレッドシートを家門名で検索(self, 家門名):
        range_name = 'メンバー情報一覧!A1:P'
        service = self.get_spreadsheet_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id,
                                    range=range_name).execute()
        match_row = [row for row in result['values'] if row[1] == 家門名]

        if len(match_row) <= 0:
            raise メンバーが見つからない

        return match_row[0]

    @commands.command(name='感謝')
    async def 感謝(self, ctx, 記名, to_家門名, メッセージ):
        """感謝 [匿名, 記名] 送り先家門名 メッセージ本文"""
        if 記名 == '匿名':
            匿名希望 = True
        elif 記名 == '記名':
            匿名希望 = False
        else:
            return await ctx.send(f"記名の有無は [ 記名, 匿名 ] のいずれかを選択してください")

        try:
            match_row = self.スプレッドシートを家門名で検索(to_家門名)
            to_discord_id = match_row[12]

            if str(ctx.author.id) == to_discord_id:
                return await ctx.send(f'自分自身へはおくれません！')

            to_user = self.bot.get_user(int(to_discord_id))
            if 匿名希望:
                from_user_name = '匿名希望'
            else:
                from_user_name = ctx.author.name

            # DBに記録を残しておく(変な使われ方を防止するため)
            Message.記録(session, str(ctx.author.id), to_discord_id, 匿名希望, メッセージ)

            msg = "```\n"
            msg += f"{from_user_name} さんより、感謝が届きました！\n"
            msg += f"{メッセージ}"
            msg += "```"
            await to_user.send(msg)

            return await ctx.send(f'送信完了！')

        except メンバーが見つからない as e:
            return await ctx.send(f'該当する宛先のメンバーがいませんでした！')

    async def cog_command_error(self, ctx, error):
        if error.param.name == 'メッセージ':
            if isinstance(error, commands.errors.MissingRequiredArgument):
                return await ctx.send(f'感謝 [匿名, 記名] 送り先家門名 メッセージ本文 という形で使用してください！')
        pass


def setup(bot):
    bot.add_cog(PeerBonus(bot))
