import json
import logging
import os
import uuid
from datetime import datetime, date, timedelta

import discord
import googleapiclient.discovery
import pytz
from discord.ext import commands
from google.oauth2 import service_account

import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'IPAGothic'

from db.session import session
from db.member import Member, メンバーが見つからない, 職が見つからない
from db.basewar_resources import BaseWarResources, メンバーが見つからない as Bwメンバーが見つからない

logger = logging.getLogger(__name__)


class MemberStatusError(Exception):
    """MemberStatusモデルが投げる例外の基底クラス"""
    pass


class スプレッドシート上にメンバーが見つからない(MemberStatusError):
    pass

class スプレッドシート上に職が見つからない(MemberStatusError):
    pass

class MemberStatus(commands.Cog):

    spreadsheet_id: str

    def __init__(self, bot):
        self.bot = bot
        self.spreadsheet_id = '1HK96UyIEEiX3Q67yMzpA-bc5eLi0jHm3pgJSTXFnqkY'

    @commands.command(name='ステータス')
    @commands.has_role('攻殻機動隊')
    async def show_my_status(self, ctx, *, member: discord.Member = None):
        try:
            msg = "```\n"
            msg += '\n'.join(self.get_my_status(ctx.author.id))
            msg += "```"
            return await ctx.channel.send(msg)
        except スプレッドシート上にメンバーが見つからない as e:
            return await ctx.channel.send(f'スプレッドシート上のメンバー一覧をあなたのDiscordIDで検索したけど見つからなかったよ！')

    def get_job_list(self):
        range_name: str = '職名リスト(新規職が追加されたら編集)!A:A'
        service = self.get_spreadsheet_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id,
                                    majorDimension='COLUMNS',
                                    range=range_name).execute()
        values = result.get('values', [])
        return values[0]

    @commands.command(name='家門名変更')
    @commands.has_role('攻殻機動隊')
    async def update_kamon_name(self, ctx, new_name):
        try:
            row_index, match_row = self.スプレッドシートをDiscordIDで検索(ctx.author.id)

            update_values = [
                [
                    new_name
                ]
            ]
            body = {
                'values': update_values
            }
            update_range_name = f"メンバー情報一覧!B{row_index + 1}"
            service = self.get_spreadsheet_service()
            result = service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                            range=update_range_name,
                                                            valueInputOption='USER_ENTERED',
                                                            body=body).execute()

            self.データベース側の家門名変更(ctx.author.id, new_name)
            await ctx.send(f'更新完了！')
        except スプレッドシート上にメンバーが見つからない as e:
            return await ctx.send(f'スプレッドシート上のメンバー一覧をあなたのDiscordIDで検索したけど見つからなかったよ！')
        return

    @commands.command(name='職変更')
    @commands.has_role('攻殻機動隊')
    async def update_job(self, ctx, job_name):
        """職変更 アークメイジ"""
        try:
            self.データベース側の職業変更(ctx.author.id, job_name)

            job_list = self.get_job_list()
            if job_name not in job_list:
                raise スプレッドシート上に職が見つからない

            row_index, match_row = self.スプレッドシートをDiscordIDで検索(ctx.author.id)
            update_values = [
                [
                    job_name
                ]
            ]
            body = {
                'values': update_values
            }
            update_range_name = f"メンバー情報一覧!H{row_index + 1}"
            service = self.get_spreadsheet_service()
            result = service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                            range=update_range_name,
                                                            valueInputOption='USER_ENTERED',
                                                            body=body).execute()
            logging.info(result)

            msg = f"{ctx.author.name} さんの職業を {job_name} に更新しました〜！"
            return await ctx.channel.send(msg)
        except スプレッドシート上にメンバーが見つからない as e:
            return await ctx.send(f'スプレッドシート上のメンバー一覧をあなたのDiscordIDで検索したけど見つからなかったよ！')
        except スプレッドシート上に職が見つからない as e:
            return await ctx.channel.send(f'スプレッドシートの職マスタに {job_name} という職が見つかりませんでした！')
        except メンバーが見つからない as e:
            return await ctx.channel.send(f'タチコマDBのメンバー一覧をあなたのDiscordIDで検索したけど見つからなかったよ！')
        except 職が見つからない as e:
            return await ctx.channel.send(f'タチコマDBの職マスタに {job_name} という職が見つかりませんでした！( 職マスタ追加 を行ってください)')

    @commands.command(name='戦闘力更新')
    @commands.has_role('攻殻機動隊')
    async def my_combat_point(self, ctx, cp, *, member: discord.Member = None):
        """戦闘力更新 {戦闘力}"""
        row_index, match_row = self.スプレッドシートをDiscordIDで検索(ctx.author.id)
        update_values = [
            [
                cp
            ]
        ]
        body = {
            'values': update_values
        }
        update_range_name = f"メンバー情報一覧!I{row_index + 1}"
        service = self.get_spreadsheet_service()
        result = service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id,
                                                        range=update_range_name,
                                                        valueInputOption='USER_ENTERED',
                                                        body=body).execute()

        self.データベース側の戦闘力更新(ctx.author.id, cp)

        msg = f"{ctx.author.name} さんの戦闘力を {cp} に更新しました〜！"
        await ctx.channel.send(msg)

    @commands.command(name='強制入隊')
    @commands.has_role('隊長')
    async def signup_member_from_leader(self, ctx, user_id, 家門名, 戦闘力, 職名):
        try:
            Member.登録(session, user_id, 家門名, 戦闘力, 職名)
            member = Member.UserIDでメンバーを取得(session, ctx.author.id)
        except 職が見つからない as e:
            await ctx.channel.send("該当する職が見つかりませんでした！")
            return
        except メンバーが見つからない as e:
            await ctx.channel.send("メンバーが見つかりませんでした！")
            return

        await ctx.channel.send(f"家門名: {member.メンバー履歴.家門名}, 戦闘力: {member.メンバー履歴.戦闘力}, メイン職: {member.メンバー履歴.職マスタ_職名} で入隊しました！")
        return

    @commands.command(name='入隊')
    @commands.has_role('攻殻機動隊')
    async def signup_member(self, ctx, 家門名, 戦闘力, 職名):
        try:
            Member.登録(session, ctx.author.id, 家門名, 戦闘力, 職名)
            member = Member.UserIDでメンバーを取得(session, ctx.author.id)
        except 職が見つからない as e:
            await ctx.channel.send("該当する職が見つかりませんでした！")
            return
        except メンバーが見つからない as e:
            await ctx.channel.send("メンバーが見つかりませんでした！")
            return

        await ctx.channel.send(f"家門名: {member.メンバー履歴.家門名}, 戦闘力: {member.メンバー履歴.戦闘力}, メイン職: {member.メンバー履歴.職マスタ_職名} で入隊しました！")
        return

    @commands.command(name='除隊')
    @commands.has_role('隊長')
    async def 除隊(self, ctx, user_id):
        try:
            member = Member.UserIDでメンバーを取得(session, user_id)
            self.データベース側の除隊処理(user_id)
            await ctx.channel.send(f"{member.メンバー履歴.家門名} さんを除隊済に設定しました！")
        except メンバーが見つからない as e:
            await ctx.channel.send("ユーザーが見つかりませんでした！")
            return
        return

    def get_spreadsheet_service(self):
        credentials = self.get_credentials()
        service = googleapiclient.discovery.build('sheets', 'v4',
                                                  credentials=credentials,
                                                  cache_discovery=False)
        return service

    def get_member_list(self):
        range_name = 'メンバー情報一覧!A1:P'

        service = self.get_spreadsheet_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id,
                                    range=range_name).execute()
        values = result.get('values', [])
        return values

    def データベース側の戦闘力更新(self, user_id, 戦闘力):
        Member.戦闘力更新(session, user_id, 戦闘力)
        return

    def データベース側の家門名変更(self, user_id, 家門名):
        Member.家門名変更(session, user_id, 家門名)
        return

    def データベース側の職業変更(self, user_id, 職業名):
        Member.職業変更(session, user_id, 職業名)
        return

    def データベース側の除隊処理(self, user_id):
        Member.除隊(session, user_id)
        return

    @commands.command(name='戦闘力推移')
    async def signup_character(self, ctx, date_range=30, *, member: discord.Member = None):
        """戦闘力推移 {現在から過去何日分(default=30)}"""
        delta = timedelta(days=date_range)
        tokyo = pytz.timezone('Asia/Tokyo')

        end = datetime.now(tz=pytz.utc).astimezone(tokyo)
        start = end - delta

        # testuser = 552078039761027073
        # data = Member.指定期間における履歴取得(session, testuser, start, end)
        data = Member.指定期間における履歴取得(session, ctx.author.id, start, end)
        xy_data = [(x.created_at.astimezone(tokyo), x.戦闘力) for x in data]
        x_data, y_data = map(list, zip(*xy_data))
        latest_data = data[-1]

        start_datetime_str = datetime.strftime(start, '%Y-%m-%d %H:%M:%S')
        end_datetime_str = datetime.strftime(end, '%Y-%m-%d %H:%M:%S')

        plt.figure()
        plt.plot(x_data, y_data, color="#0d5295", marker='.', markersize='10')

        graph_tmp_filename = uuid.uuid4()
        plt.ylabel("戦闘力")
        plt.xlabel("更新日時")
        plt.grid(b=True, which='major', color='#666666', linestyle='-', alpha=0.5)
        plt.minorticks_on()
        plt.grid(b=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(f"{graph_tmp_filename}.png")
        file = discord.File(f"{graph_tmp_filename}.png", filename=f"{graph_tmp_filename}.png")

        embed = discord.Embed(title=f"{latest_data.家門名} さんの戦闘力推移", description=f"{start_datetime_str} 〜 {end_datetime_str}", color=discord.Colour.from_rgb(13, 82, 149))
        embed.add_field(name="プロット日数範囲", value=f"過去 {date_range} 日分")
        embed.set_image(url=f"attachment://{graph_tmp_filename}.png")
        await ctx.channel.send(file=file, embed=embed)

        os.remove(f"{graph_tmp_filename}.png")
        return ""

    @commands.command(name='資材')
    async def reinforcement_resources(self, ctx, 生命の粉=0, 頑丈な原木=0, 黒い水晶の原石=0):
        """資材 {生命の粉の数} {頑丈な原木の数} {黒い水晶の原石の数}"""
        try:
            BaseWarResources.全資材申告(session, ctx.author.id, 生命の粉, 頑丈な原木, 黒い水晶の原石)
        except Bwメンバーが見つからない as e:
            await ctx.channel.send("ユーザーが見つかりませんでした！")
            return
        await ctx.channel.send(f"{ctx.author.name} さんの資材状況 生命の粉: {生命の粉}, 頑丈な原木: {頑丈な原木}, 黒い水晶の原石: {黒い水晶の原石} で更新完了！")

    def スプレッドシートをDiscordIDで検索(self, discord_id):
        range_name = 'メンバー情報一覧!A1:P'
        service = self.get_spreadsheet_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.spreadsheet_id,
                                    range=range_name).execute()
        match_row = [(idx, row) for idx, row in enumerate(result['values']) if row[12] == str(discord_id)]

        if len(match_row) <= 0:
            raise スプレッドシート上にメンバーが見つからない

        return match_row[0]

    @staticmethod
    def get_credentials():
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        credentials = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
        return credentials

    def get_my_status(self, discord_user_id):
        index, status = self.スプレッドシートをDiscordIDで検索(discord_user_id)
        result = [
            f"家門名: {status[1]}",
            f"加入日: {status[2]}",
            f"在籍日数: {status[4]}",
            f"メイン職: {status[7]}",
            f"戦闘力: {status[8]}"
        ]
        return result


def setup(bot):
    bot.add_cog(MemberStatus(bot))
