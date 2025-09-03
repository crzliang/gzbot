"""
数据库操作模块
"""
import asyncpg
from .config import POSTGRES_DSN, TARGET_GAME_ID


async def get_game_title(game_id: int) -> str:
    """根据游戏ID获取游戏标题"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        game_record = await conn.fetchrow('SELECT "Title" FROM "Games" WHERE "Id" = $1', game_id)
        if not game_record:
            raise ValueError(f"未找到ID为 {game_id} 的比赛")
        return game_record['Title']
    finally:
        await conn.close()


async def get_game_challenges(game_id: int):
    """获取比赛题目列表"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        rows = await conn.fetch(
            'SELECT "Title", "Category", "OriginalScore" FROM "GameChallenges" WHERE "GameId" = $1 ORDER BY "Id" DESC',
            game_id
        )
        return rows
    finally:
        await conn.close()


async def get_game_rankings(game_id: int):
    """获取比赛排行榜"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        query = """
        WITH TeamScores AS (
            SELECT 
                t."Name" as TeamName,
                COALESCE(SUM(CASE 
                    WHEN s."Status" = 'Accepted'
                    THEN gc."OriginalScore"::integer
                    ELSE 0 
                END), 0) as TotalScore,
                -- 最后正确提交时间（用于排名）
                MAX(CASE 
                    WHEN s."Status" = 'Accepted'
                    THEN s."SubmitTimeUtc" 
                END) as LastAcceptedSubmission
            FROM "Participations" p
            INNER JOIN "Teams" t ON p."TeamId" = t."Id"
            LEFT JOIN "Submissions" s ON s."ParticipationId" = p."Id"
            LEFT JOIN "GameChallenges" gc ON s."ChallengeId" = gc."Id"
            WHERE p."GameId" = $1 
              AND p."Status" = 1  -- ParticipationStatus.Accepted
            GROUP BY t."Name"
            HAVING SUM(CASE WHEN s."Status" = 'Accepted' THEN gc."OriginalScore"::integer ELSE 0 END) > 0
        ),
        RankedTeams AS (
            SELECT 
                TeamName,
                TotalScore,
                ROW_NUMBER() OVER (
                    ORDER BY TotalScore DESC, 
                             LastAcceptedSubmission ASC NULLS LAST,
                             TeamName ASC
                ) as Rank
            FROM TeamScores
        )
        SELECT 
            Rank,
            TeamName,
            TotalScore
        FROM RankedTeams
        ORDER BY Rank;
        """
        rows = await conn.fetch(query, game_id)
        return rows
    finally:
        await conn.close()


async def get_recent_notices(game_id: int, seconds: int = 10):
    """获取最近的游戏通知"""
    from datetime import datetime, timedelta
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        query = """
        SELECT 
            gn."Id",
            gn."Type",
            gn."Values",
            gn."PublishTimeUtc",
            CASE gn."Type"
                WHEN 0 THEN '📢 公告通知'
                WHEN 1 THEN '🥇 一血通知'
                WHEN 2 THEN '🥈 二血通知'
                WHEN 3 THEN '🥉 三血通知'
                WHEN 4 THEN '💡 提示更新'
                WHEN 5 THEN '🆕 新题目开放'
                ELSE '❓ 未知类型'
            END as notice_type
        FROM "GameNotices" gn
        WHERE gn."GameId" = $1
          AND gn."PublishTimeUtc" > $2
        ORDER BY gn."PublishTimeUtc" DESC;
        """
        
        time_ago = datetime.utcnow() - timedelta(seconds=seconds)
        rows = await conn.fetch(query, game_id, time_ago)
        return rows
    finally:
        await conn.close()
