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
        # 最简化的查询，只获取排名、团队名、总分和学号
        query = """
        WITH TeamScores AS (
            SELECT 
                t."Name" as TeamName,
                t."Id" as TeamId,
                COALESCE(SUM(CASE 
                    WHEN s."Status" = 'Accepted'
                    THEN gc."OriginalScore"::integer
                    ELSE 0 
                END), 0) as TotalScore
            FROM "Participations" p
            INNER JOIN "Teams" t ON p."TeamId" = t."Id"
            LEFT JOIN "Submissions" s ON s."ParticipationId" = p."Id"
            LEFT JOIN "GameChallenges" gc ON s."ChallengeId" = gc."Id"
            WHERE p."GameId" = $1 AND p."Status" = 1
            GROUP BY t."Name", t."Id"
            HAVING SUM(CASE WHEN s."Status" = 'Accepted' THEN gc."OriginalScore"::integer ELSE 0 END) > 0
        ),
        RankedTeams AS (
            SELECT 
                TeamName,
                TeamId,
                TotalScore,
                ROW_NUMBER() OVER (ORDER BY TotalScore DESC, TeamName ASC) as Rank
            FROM TeamScores
        )
        SELECT 
            rt.Rank,
            rt.TeamName,
            rt.TotalScore,
            STRING_AGG(u."StdNumber", ', ') as StudentNumbers
        FROM RankedTeams rt
        INNER JOIN "Participations" p ON p."TeamId" = rt.TeamId AND p."GameId" = $1
        INNER JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
        INNER JOIN "AspNetUsers" u ON u."Id" = up."UserId"
        GROUP BY rt.Rank, rt.TeamName, rt.TotalScore
        ORDER BY rt.Rank;
        """
        rows = await conn.fetch(query, game_id)
        return rows
    finally:
        await conn.close()


async def get_game_rankings_by_stdnum_prefix(game_id: int, stdnum_prefix: str):
    """获取按学号前缀过滤的比赛排行榜"""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        # 查询指定学号前缀的队伍排行榜
        query = """
        WITH TeamScores AS (
            SELECT 
                t."Name" as TeamName,
                t."Id" as TeamId,
                COALESCE(SUM(CASE 
                    WHEN s."Status" = 'Accepted'
                    THEN gc."OriginalScore"::integer
                    ELSE 0 
                END), 0) as TotalScore
            FROM "Participations" p
            INNER JOIN "Teams" t ON p."TeamId" = t."Id"
            LEFT JOIN "Submissions" s ON s."ParticipationId" = p."Id"
            LEFT JOIN "GameChallenges" gc ON s."ChallengeId" = gc."Id"
            WHERE p."GameId" = $1 AND p."Status" = 1
            GROUP BY t."Name", t."Id"
            HAVING SUM(CASE WHEN s."Status" = 'Accepted' THEN gc."OriginalScore"::integer ELSE 0 END) > 0
        ),
        FilteredTeams AS (
            SELECT DISTINCT ts.TeamId, ts.TeamName, ts.TotalScore
            FROM TeamScores ts
            INNER JOIN "Participations" p ON p."TeamId" = ts.TeamId AND p."GameId" = $1
            INNER JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
            INNER JOIN "AspNetUsers" u ON u."Id" = up."UserId"
            WHERE u."StdNumber" LIKE $2 || '%'
        ),
        RankedTeams AS (
            SELECT 
                TeamName,
                TeamId,
                TotalScore,
                ROW_NUMBER() OVER (ORDER BY TotalScore DESC, TeamName ASC) as Rank
            FROM FilteredTeams
        )
        SELECT 
            rt.Rank,
            rt.TeamName,
            rt.TotalScore,
            STRING_AGG(u."StdNumber", ', ') as StudentNumbers
        FROM RankedTeams rt
        INNER JOIN "Participations" p ON p."TeamId" = rt.TeamId AND p."GameId" = $1
        INNER JOIN "UserParticipations" up ON up."ParticipationId" = p."Id"
        INNER JOIN "AspNetUsers" u ON u."Id" = up."UserId"
        GROUP BY rt.Rank, rt.TeamName, rt.TotalScore
        ORDER BY rt.Rank;
        """
        rows = await conn.fetch(query, game_id, stdnum_prefix)
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


async def get_challenge_info_by_name(game_id: int, challenge_name: str):
    """根据题目名称获取题目信息"""
    import json
    
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        # 首先尝试直接匹配
        query = """
        SELECT 
            gc."Title",
            gc."Category",
            CASE gc."Category"
                WHEN 0 THEN 'Misc'
                WHEN 1 THEN 'Crypto'
                WHEN 2 THEN 'Pwn'
                WHEN 3 THEN 'Web'
                WHEN 4 THEN 'Reverse'
                WHEN 5 THEN 'Blockchain'
                WHEN 6 THEN 'Forensics'
                WHEN 7 THEN 'Hardware'
                WHEN 8 THEN 'Mobile'
                WHEN 9 THEN 'PPC'
                WHEN 10 THEN 'AI'
                WHEN 11 THEN 'Pentest'
                WHEN 12 THEN 'OSINT'
                ELSE 'Unknown'
            END as CategoryName
        FROM "GameChallenges" gc
        WHERE gc."GameId" = $1 AND gc."Title" = $2
        LIMIT 1;
        """
        
        # 处理 Values 字段中的题目名称
        # Values 可能是 JSON 格式如 ["题目名"] 或直接是题目名
        actual_challenge_name = challenge_name
        
        # 如果是 JSON 数组格式，提取第一个元素
        if challenge_name.startswith('[') and challenge_name.endswith(']'):
            try:
                parsed_values = json.loads(challenge_name)
                if isinstance(parsed_values, list) and len(parsed_values) > 0:
                    actual_challenge_name = str(parsed_values[0])
            except json.JSONDecodeError:
                pass  # 如果解析失败，使用原始名称
        
        print(f"DEBUG: Looking for challenge: original='{challenge_name}', processed='{actual_challenge_name}'")
        
        result = await conn.fetchrow(query, game_id, actual_challenge_name)
        return result
    finally:
        await conn.close()
